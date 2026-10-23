import json
from fastapi import HTTPException
from pydantic import BaseModel, Field
from packages.agent_core.providers import LLMProvider
from packages.career.graph import apply_patches
from services.api.schemas import Patch


class SuggestRewrite(BaseModel):
    approved_fact_ids: list[str] = Field(min_length=1, max_length=100)
    instruction: str = Field(default="在保留全部事实的前提下改善表达结构", max_length=3000)
    base_version_id: str | None = None


def suggest(facts, body, jd, evidence=None, context=None, structure=None):
    selected = [f for f in facts if f["id"] in body.approved_fact_ids]
    if len(selected) != len(set(body.approved_fact_ids)) or any(f.get("locked") for f in selected):
        raise HTTPException(422, "请选择存在且未锁定的段落")
    provider = LLMProvider()
    evidence = evidence or []
    raw = provider.complete("只返回JSON {patches:[{fact_id,text,reason,source_chunk_ids}]}。针对目标GTM岗位与JD改写已授权项目和实际经历，将已有调研、数据分析、内容、协作等经历与岗位能力建立联系。用户JD优先，学习资料提供框架，面经仅作个人案例参考。不能把岗位要求或别人的经历写成用户事实，不新增职责、地区、资历、结果或数字。reason解释调整依据，source_chunk_ids仅从证据包选择。", {"facts": selected, "instruction": body.instruction, "jd": jd, 'career_context':context or {}, 'focus_sections':['projects','experience'], 'section_assignments':(structure or {}).get('assignments',{}), 'evidence':evidence})
    try:
        proposals = json.loads(raw.removeprefix("```json").removesuffix("```").strip())["patches"]
        patches = [Patch.model_validate(p) for p in proposals]
        known = {e['chunk_id'] for e in evidence}
        if any(not set(p.get('source_chunk_ids',[])).issubset(known) for p in proposals):
            raise ValueError('Unknown rewrite reference')
        apply_patches(facts, patches, body.approved_fact_ids)
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, "模型改写结构不合法；未生成任何简历版本")
    return {"patches": [{**p.model_dump(),'reason':str(proposal.get('reason','仅调整表达；请核对事实与岗位关联。'))[:1500],'source_chunk_ids':proposal.get('source_chunk_ids',[])} for p,proposal in zip(patches,proposals)], 'citations':evidence, 'jd_priority':bool(jd), "provider": provider.mode, "model": provider.model, "notice": "改写建议尚未保存为版本。下列资料是检索参考，不是你的个人经历；请核对事实、编辑文本，再确认授权生成。"}
