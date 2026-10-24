"""Source-bound resume blocks and non-mutating, retrieval-backed rewrite dialogue."""
import copy
import json
import re
from fastapi import HTTPException
from pydantic import BaseModel, Field
from packages.agent_core.providers import LLMProvider
from packages.career.structure import local_structure


class BlockPatch(BaseModel):
    fact_ids: list[str] = Field(min_length=1, max_length=100)
    text: str = Field(max_length=16000)


class DialogueTurn(BaseModel):
    message: str = Field(max_length=3000)
    text: str = Field(default='', max_length=16000)
    analysis: str = Field(default='', max_length=4000)
    questions: str = Field(default='', max_length=3000)


class BlockDialogue(BaseModel):
    fact_ids: list[str] = Field(min_length=1, max_length=100)
    draft_text: str = Field(default='', max_length=16000)
    message: str = Field(min_length=1, max_length=3000)
    history: list[DialogueTurn] = Field(default_factory=list, max_length=12)
    base_version_id: str | None = None


def selected_block(facts, ids):
    positions = [i for i, f in enumerate(facts) if f['id'] in ids]
    if not positions or len(positions) != len(ids) or positions != list(range(positions[0], positions[-1]+1)):
        raise HTTPException(422, '请选择同一段连续经历，不能遗漏、重复或跨经历合并')
    selected = [facts[i] for i in positions]
    if [f['id'] for f in selected] != ids or any(f.get('locked') for f in selected):
        raise HTTPException(422, '只能编辑按原顺序选择的未锁定内容')
    sections = local_structure(facts)['assignments']
    if len({sections[f['id']] for f in selected}) != 1:
        raise HTTPException(422, '不同 section 不能合并改写')
    return selected, sections[selected[0]['id']]


def check_text(text, selected):
    original = '\n'.join(f['text'] for f in selected)
    numbers = lambda value: set(re.findall(r"\d+(?:\.\d+)?%?", value))
    if not numbers(text).issubset(numbers(original)):
        raise HTTPException(422, '改写新增数字，请先在识别与事实中补充并确认来源')
    if re.search(r"\\(?:input|include|write|openout|read|usepackage|documentclass)", text):
        raise HTTPException(422, '不接受 LaTeX 指令；请输入纯文本')


def apply_block_patches(facts, patches, approved):
    result, used = copy.deepcopy(facts), set()
    for patch in patches:
        selected, section = selected_block(facts, patch.fact_ids)
        if used.intersection(patch.fact_ids) or not set(patch.fact_ids).issubset(approved):
            raise HTTPException(422, '每块经历必须独立且全部明确授权')
        used.update(patch.fact_ids)
        check_text(patch.text, selected)
        first = patch.fact_ids[0]
        for fact in result:
            if fact['id'] == first:
                fact.update(text=patch.text, section=section)
        removed = set(patch.fact_ids[1:] if patch.text.strip() else patch.fact_ids)
        result = [f for f in result if f['id'] not in removed]
    if not result:
        raise HTTPException(422, '请至少保留一个简历块')
    return result


def group_blocks(facts, structure):
    assignments = structure.get('assignments') or local_structure(facts)['assignments']
    raw = LLMProvider().complete(
        '简历经历分块。只返回JSON {blocks:[{title,fact_ids}]}。按原文顺序覆盖每个事实ID恰好一次，不改写正文。'
        '每个独立公司实习、任职、项目各自一块，例如实习经历 1、实习经历 2；其余按 section 聚合。'
        '只组合连续、同 section 且锁定状态相同的事实。不得将不同企业或不同项目合成一块。',
        {'facts':facts, 'section_assignments':assignments})
    try:
        value=json.loads(raw.removeprefix('```json').removesuffix('```').strip())['blocks']
        if not isinstance(value,list) or not value:
            raise ValueError()
        if [fid for block in value for fid in block['fact_ids']] != [f['id'] for f in facts]:
            raise ValueError()
        by_id={f['id']:f for f in facts}
        result=[]
        for block in value:
            ids=block['fact_ids']
            if not ids or len({assignments[fid] for fid in ids})!=1 or len({bool(by_id[fid].get('locked')) for fid in ids})!=1:
                raise ValueError()
            title=block['title']
            if not isinstance(title,str) or not title.strip() or len(title)>120:
                raise ValueError()
            result.append({'id':ids[0],'title':title,'fact_ids':ids,'section':assignments[ids[0]],'locked':bool(by_id[ids[0]].get('locked'))})
        return result
    except (ValueError,KeyError,TypeError):
        raise HTTPException(502, '简历分块未通过完整性校验，请重试；原文未修改')


def discuss_block(facts, body, jd, evidence, context):
    selected, section=selected_block(facts,body.fact_ids)
    provider=LLMProvider()
    payload={'facts':selected,'section':section,'draft_text':body.draft_text,'message':body.message,
             'history':[t.model_dump() for t in body.history], 'jd':jd,
             'career_context':{k:v for k,v in context.items() if k!='jd'},'evidence':evidence}
    while payload['history'] and len(json.dumps(payload,ensure_ascii=False))>55000:
        payload['history'].pop(0)
    raw=provider.complete(
        '简历分块多轮改写。只返回JSON {text,analysis,questions,source_chunk_ids}。'
        'text 是此块完整的优化后纯文本，analysis 解释修改与岗位关联，questions 是需要向用户确认的问题。'
        '使用当前草稿和本轮要求，结合历史逐轮调整。用户 JD 优先，知识库岗位职能与要求用于解释能力关联。'
        '资料不是用户经历，不得把别人经历、企业要求或模拟结果当成用户事实。不得编造数字或成果。'
        '空白块先询问真实经历细节；信息不足可返回空 text 并在 questions 提问。'
        'source_chunk_ids 只能来自本次 evidence。建议不直接保存版本，等待用户确认。',
        payload)
    try:
        value=json.loads(raw.removeprefix('```json').removesuffix('```').strip())
        if not isinstance(value,dict) or not any(value.get(key) for key in ['text','analysis','questions']):
            raise ValueError()
        for key,limit in [('text',16000),('analysis',4000),('questions',3000)]:
            if not isinstance(value.get(key,''),str) or len(value.get(key,''))>limit:
                raise ValueError()
        sources=value.get('source_chunk_ids',[])
        if not isinstance(sources,list) or not set(sources).issubset({e['chunk_id'] for e in evidence}):
            raise ValueError()
        check_text(value.get('text',''),selected)
        return {key:value.get(key,'') for key in ['text','analysis','questions']} | {'citations':evidence,'model':provider.model}
    except (ValueError,KeyError,TypeError):
        raise HTTPException(502, '改写建议或引用格式不正确，请重试；原文未修改')
