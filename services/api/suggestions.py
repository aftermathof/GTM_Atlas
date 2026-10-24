import json
from fastapi import HTTPException
from pydantic import BaseModel, Field
from packages.agent_core.providers import LLMProvider
from packages.career.graph import apply_patches
from services.api.schemas import Patch


class SuggestRewrite(BaseModel):
    approved_fact_ids: list[str] = Field(min_length=1, max_length=100)
    instruction: str = Field(default="结合目标岗位 JD，优化并补充更贴合岗位的简历表达", max_length=3000)
    base_version_id: str | None = None


def suggest(facts, body, jd, evidence=None, context=None, structure=None):
    selected = [f for f in facts if f["id"] in body.approved_fact_ids]
    if len(selected) != len(set(body.approved_fact_ids)) or any(f.get("locked") for f in selected):
        raise HTTPException(422, "请选择存在且未锁定的段落")
    provider = LLMProvider()
    evidence = evidence or []
    raw = provider.complete("只返回JSON {patches:[{fact_id,text,reason,source_chunk_ids}]}。针对目标岗位与JD改写已选择段落，直接落实用户 instruction 中的调整与补充要求，交付可编辑的候选草稿。用户JD优先，知识库提供岗位职责、方法和交付物参考。原文不是内容上限，用户提供的新细节与数字可直接纳入；新增方向先提供候选写法，在 reason 简短标明需要核对的部分，不要因原文缺失而拒绝交付。未提供的精确业绩数字可以省略，不自行编定。source_chunk_ids仅从证据包选择。", {"facts": selected, "instruction": body.instruction, "jd": jd, 'career_context':context or {}, 'focus_sections':['projects','experience'], 'section_assignments':(structure or {}).get('assignments',{}), 'evidence':evidence})
    try:
        proposals = json.loads(raw.removeprefix("```json").removesuffix("```").strip())["patches"]
        patches = [Patch.model_validate(p) for p in proposals]
        if any(not p.text.strip() for p in patches):
            raise ValueError('Suggestions must not remove facts')
        known = {e['chunk_id'] for e in evidence}
        if any(not set(p.get('source_chunk_ids',[])).issubset(known) for p in proposals):
            raise ValueError('Unknown rewrite reference')
        apply_patches(facts, patches, body.approved_fact_ids)
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, "模型改写结构不合法；未生成任何简历版本")
    return {"patches": [{**p.model_dump(),'reason':str(proposal.get('reason','结合目标岗位调整内容；可继续编辑。'))[:1500],'source_chunk_ids':proposal.get('source_chunk_ids',[])} for p,proposal in zip(patches,proposals)], 'citations':evidence, 'jd_priority':bool(jd), "provider": provider.mode, "model": provider.model, "notice": "这是结合目标岗位生成的候选稿，可继续补充或修改；确认后再保存为新版。"}
