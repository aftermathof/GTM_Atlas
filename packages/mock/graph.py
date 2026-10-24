import json
import random
import re
import unicodedata
from typing import TypedDict
from fastapi import HTTPException
from langgraph.graph import StateGraph, END
from packages.agent_core.providers import LLMProvider
from packages.agent_core.registry import catalog
from packages.rag.knowledge import search

ZH = [
    ("岗位认知", "你如何理解目标岗位的职责？请说明它与海外渠道销售、KOL 营销或海外运营的边界。"),
    ("市场分析", "一款消费电子产品进入新市场前，你会如何验证目标用户、竞争格局与渠道假设？"),
    ("业务场景", "目标市场销量未达预期，你会如何拆解用户、渠道和转化环节，并安排验证优先级？"),
    ("商业指标", "如何评价一次 KOL 营销或渠道合作的投入产出？请说明归因窗口、利润和数据局限。"),
    ("行为经历", "请用 STAR 结构讲述一次真实的跨团队协作。你负责什么，采取了什么行动，结果如何验证？"),
    ("跨文化沟通", "海外合作方对合作条款提出异议时，你会如何澄清诉求、协商并记录下一步？"),
    ("用户洞察", "用户访谈与销量数据出现冲突，你会如何解释并设计下一步调研？"),
    ("策略取舍", "预算受限时，你如何在内容营销、分销渠道与效果广告之间分配资源？"),
    ("风险判断", "渠道库存积压且经销商要求提高返利，你会如何排查并评估方案？"),
    ("复盘迭代", "如果项目未达到目标，你如何区分策略错误与执行偏差，并设计下一轮实验？"),
]
EN = [
    "How do you define this role and its boundaries with channel sales and KOL marketing?",
    "How would you validate the target users, competition and channels for a new market?",
    "Sales are below expectations. How would you prioritize and test your hypotheses?",
    "How do you measure ROI for a creator or channel partnership, including attribution limits?",
    "Describe a real cross-functional project using STAR. What did you personally do?",
    "How would you handle a disagreement with an overseas partner about contract terms?",
    "User interviews and sales data conflict. How would you investigate?",
    "How would you allocate a limited budget across creators, distributors and paid media?",
    "A distributor has excess inventory and asks for rebates. What would you examine?",
    "How do you distinguish execution issues from strategic errors after a missed target?",
]


def question_key(text):
    return re.sub(r'[\W_]+', '', unicodedata.normalize('NFKC', text).casefold())


def plan_interview(db, setup, resume=None, excluded_questions=None):
    excluded_questions = excluded_questions or []
    excluded = {question_key(text) for text in excluded_questions}
    rng = random.Random(setup.seed)
    profiles = catalog()
    indexes = []
    while len(indexes) < setup.count:
        indexes.extend(rng.sample(range(len(ZH)), len(ZH)))
    questions = []
    references = {}
    scenarios = [('新品上市', 'a product launch'), ('渠道伙伴评估', 'channel partner evaluation'), ('内容本地化', 'content localization'), ('客户线索转化', 'lead conversion'), ('用户留存', 'user retention'), ('销售与市场协作', 'sales and marketing collaboration'), ('定价测试', 'pricing tests'), ('市场进入试点', 'a market entry pilot')]
    for i in indexes[:setup.count]:
        dimension, question = ZH[i]
        if setup.language == "en":
            question = EN[i]
        used = excluded | {question_key(q['text']) for q in questions}
        if question_key(question) in used:
            for zh, en in rng.sample(scenarios, len(scenarios)):
                candidate = question + (f' Focus on {en}.' if setup.language == 'en' else f' 请结合{zh}场景作答。')
                if question_key(candidate) not in used:
                    question = candidate
                    break
        if i not in references:
            references[i] = search(db, ZH[i][1], "interview", setup.role, setup.industry, top_k=1)
        evidence = references[i]
        questions.append({"text": question, "dimension": dimension, "source_type": "interview_reference" if evidence else "role_profile_generated", "citations": evidence, "rubric_version": profiles["version"]})
    if resume:
        factual = next((f for f in resume if not f.get("locked") and len(f["text"]) > 15), resume[-1])
        index = min(2, len(questions)-1)
        question = (f'In your resume you wrote: "{factual["text"][:500]}". What was your own contribution and how did you verify the outcome?' if setup.language == 'en' else f'你在简历中提到「{factual["text"][:500]}」。你具体负责什么？如何验证结果？')
        if question_key(question) in excluded:
            question += (' What would you change next time, and why?' if setup.language == 'en' else '如果重新开展这项工作，你会改变哪一步，为什么？')
        questions[index] = {**questions[index], "text": question, "source_type": "authorized_resume", "fact_id": factual["id"]}
    provider = LLMProvider()
    previous = []
    budget = 12000
    for text in reversed(excluded_questions):
        if len(text) <= budget:
            previous.append(text)
            budget -= len(text)
    task = f"题目规划：返回JSON {{questions:[{{text,dimension}}]}}。按给定题数、语言、难度、岗位与JD规划；覆盖至少{min(3, setup.count)}个能力维度；不编造个人经历。本轮题目和previous_questions中的题目均不得重复；引用简历时只依据authorized_facts，围绕不同个人行动、判断、协作或验证方式提问。"
    payload = {"setup": setup.model_dump(), "role_profiles": profiles["roles"], "blueprint": questions, "authorized_facts": resume, "previous_questions": previous}
    for attempt in range(2):
        raw = provider.complete(task, payload)
        try:
            planned = json.loads(raw.removeprefix("```json").removesuffix("```").strip())["questions"]
            keys = [question_key(q['text']) for q in planned]
            if not excluded.intersection(keys) and len(set(keys)) == len(keys):
                break
            task += ' 上次输出包含重复题，请从不同任务场景与追问角度重新规划全部题目。'
        except (ValueError, KeyError, TypeError, AttributeError):
            raise HTTPException(502, "面试规划结构校验失败，请重试；未创建不完整会话")
    else:
        raise HTTPException(503, "生成的题目与历史重复，请重新开始；未保存重复题目")
    try:
        if len(planned) != setup.count or len({q["dimension"] for q in planned}) < min(3, setup.count):
            raise ValueError()
        for i, question in enumerate(planned):
            if not isinstance(question["text"], str) or not 10 <= len(question["text"]) <= 1500:
                raise ValueError()
            questions[i] = {**questions[i], "text": question["text"], "dimension": question["dimension"], "source_type": "authorized_resume" if questions[i].get("source_type") == "authorized_resume" else "ai_generated_with_blueprint"}
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, "面试规划结构校验失败，请重试；未创建不完整会话")
    return {"context": setup.model_dump(), "questions": questions, "current_question_index": 0, "answers": [], "followup_counts": {}, "pending_followup": None, "status": "in_progress", "blueprint_version": "blueprint-1", "rubric_version": profiles["version"], "provider": LLMProvider().mode}


class MockState(TypedDict):
    session: dict
    answer: dict
    evaluation: dict


def evaluate_answer(session, submission, checkpointer=None, thread_id=None):
    provider = LLMProvider()

    def evaluate(state):
        answer = state["answer"]["answer"]
        dimensions = {'相关性', '结构性', '专业准确性', '可验证经历', '商业逻辑', '沟通表达'}
        question = session["questions"][session["current_question_index"]]
        raw = provider.complete("返回JSON：dimensions各维0-4或null（不适用）；feedback；evidence须原答摘录；followup可为null。不要虚构事实。", {"question": question, "confirmed_answer": answer, "rubric": catalog()["rubric"]})
        try:
            value = json.loads(raw.removeprefix("```json").removesuffix("```").strip())
            scores = value["dimensions"]
            if set(scores) != dimensions or any(v is not None and (type(v) not in (int, float) or not 0 <= v <= 4) for v in scores.values()):
                raise ValueError()
            if not isinstance(value.get("feedback"), str) or (value.get("followup") is not None and not isinstance(value["followup"], str)):
                raise ValueError()
            if value.get("evidence", "") not in answer:
                value["evidence"] = answer[:240]
            valid = [v for v in scores.values() if v is not None]
            value["score"] = round(sum(valid) / len(valid) * 25) if valid else None
        except (ValueError, KeyError, TypeError):
            raise HTTPException(502, "模型评分结构不合法，答案未推进，请重试")
        value.update({"provider": provider.mode, "model": provider.model, "rubric_version": "role-rubric-1", "notice": "训练参考评分；不适用的维度标记为 N/A，不预测录用结果。"})
        return {"evaluation": value}

    graph = StateGraph(MockState)
    graph.add_node("answer_evaluator", evaluate)
    graph.set_entry_point("answer_evaluator")
    graph.add_edge("answer_evaluator", END)
    compiled = graph.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}} if checkpointer else None
    if checkpointer:
        checkpoint = compiled.get_state(config)
        if checkpoint.values.get("evaluation") and not checkpoint.next:
            return checkpoint.values["evaluation"]
        if checkpoint.next:
            return compiled.invoke(None, config)["evaluation"]
    return compiled.invoke({"session": session, "answer": submission, "evaluation": {}}, config)["evaluation"]
