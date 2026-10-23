import re
from typing import TypedDict
from langgraph.graph import StateGraph, END
from packages.rag.knowledge import search
from packages.agent_core.providers import LLMProvider


class LearningState(TypedDict, total=False):
    question: str
    scope: str
    kind: str | None
    role: str
    industry: str
    document_id: str | None
    evidence: list
    answer: str
    citations: list
    trace: list
    private_context: dict
    history: list


def answer_question(db, request, private_context=None, history=None):
    provider = LLMProvider()

    def retrieve(state):
        kind = {"learning": "learning", "interview": "interview", "career": "jd", "article": None}.get(state["scope"])
        if state['scope']=='career' and state.get('private_context'):
            from packages.career.retrieval import career_evidence
            private=state['private_context']
            evidence=career_evidence(db,private['career_context'],private.get('jd',''),state['question'],owner_id=private['owner_id'])
        elif state['scope']=='article' and (state.get('private_context') or {}).get('selected_document'):
            doc=state['private_context']['selected_document']
            evidence=[{'chunk_id':'private-jd-'+doc['id']+':0','doc_id':doc['id'],'title':doc['title'],'heading_path':'用户上传的JD','text':doc['body'],'kind':'jd','permission':'private','quality_status':'user_provided','url':'/learn/'+doc['id']}]
        else:
            query = state["question"]
            if state.get('history'):
                query = state['history'][-1]['question'][:500] + ' ' + query
            evidence = search(db, query, kind, '' if state['scope']=='global' else state['role'], '' if state['scope']=='global' else state['industry'], state.get("document_id"))
        return {"evidence": evidence, "trace": [{"node": "permission_resolver", "permissions":sorted({e['permission'] for e in evidence})}, {"node": "retriever", "chunks": [e["chunk_id"] for e in evidence]}]}

    def compose(state):
        if not state["evidence"] and not state.get("private_context"):
            return {"answer": "知识库证据不足，无法仅凭当前资料回答。请尝试调整关键词或切换资料范围。"}
        private={k:v for k,v in (state.get('private_context') or {}).items() if k!='owner_id'}
        answer = provider.complete("基于当前证据回答问题并提供适用范围与局限。历史对话仅用于理解追问，不作为事实来源；引用必须来自本次 evidence。", {"question": state["question"], "history": state.get('history', []), "scope": state["scope"], "evidence": state["evidence"], "authorized_context": private})
        return {"answer": answer}

    def validate(state):
        used = set(re.findall(r"\[([\w-]+:\d+)\]", state["answer"]))
        known = {e["chunk_id"] for e in state["evidence"]}
        if not used.issubset(known):
            answer = "引用校验失败，模型返回了不存在的来源。请重试。"
            citations = []
        else:
            answer = state["answer"]
            citations = [e for e in state["evidence"] if e["chunk_id"] in used]
            if state["evidence"] and not citations:
                answer = "模型未提供可校验引用，回答已拦截。请重试。"
        return {"answer": answer, "citations": citations, "trace": state["trace"] + [{"node": "citation_validator", "valid": used.issubset(known)}]}

    graph = StateGraph(LearningState)
    for name, fn in [("retrieve", retrieve), ("compose", compose), ("validate", validate)]:
        graph.add_node(name, fn)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "compose")
    graph.add_edge("compose", "validate")
    graph.add_edge("validate", END)
    state = graph.compile().invoke({"question": request.message, "scope": request.scope, "role": request.role, "industry": request.industry, "document_id": request.document_id, "private_context": private_context, 'history': history or []})
    return {"answer": state["answer"], "citations": state["citations"], "trace": state["trace"], "provider": provider.mode, "model": provider.model, "limitations": "学习与训练参考；不代表招聘结果。"}
