"""Model-assisted field extraction with complete, source-bound fact assignments."""
import json
import re
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from packages.agent_core.providers import LLMProvider

Section = Literal['personal', 'education', 'projects', 'experience', 'skills', 'summary', 'other']
SECTION_NAMES = {'personal':'个人信息', 'education':'教育背景', 'projects':'项目经历', 'experience':'实习与工作经历', 'skills':'技能特长', 'summary':'自我评价', 'other':'其他经历'}


class SourcedValue(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value: str = Field(default='', max_length=1000)
    source_fact_ids: list[str] = Field(default_factory=list, max_length=20)


class Profile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: SourcedValue = Field(default_factory=SourcedValue)
    email: SourcedValue = Field(default_factory=SourcedValue)
    phone: SourcedValue = Field(default_factory=SourcedValue)
    target_role: SourcedValue = Field(default_factory=SourcedValue)


class ResumeStructure(BaseModel):
    model_config = ConfigDict(extra='forbid')
    profile: Profile
    assignments: dict[str, Section]


def local_structure(facts):
    profile = {key: {'value':'', 'source_fact_ids':[]} for key in ['name','email','phone','target_role']}
    assignments, current = {}, 'other'
    for index, fact in enumerate(facts):
        value, fid = fact['text'], fact['id']
        patterns = {'name':r'^(?:姓名|Name)\s*[:：]\s*(.+)', 'email':r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', 'phone':r'(?:电话|手机|Phone)\s*[:：]\s*([+\d ()-]{7,})', 'target_role':r'(?:求职意向|目标岗位)\s*[:：]\s*(.+)'}
        personal = False
        for key, pattern in patterns.items():
            match = re.search(pattern, value, re.I)
            if match and not profile[key]['value']:
                profile[key] = {'value': (match.group(1) if match.lastindex else match.group()).strip(), 'source_fact_ids':[fid]}
                personal = True
        if index == 0 and not profile['name']['value'] and re.fullmatch(r'[\u4e00-\u9fffA-Za-z ·]{2,20}', value):
            profile['name'] = {'value':value, 'source_fact_ids':[fid]}; personal = True
        if personal:
            section = 'personal'
        else:
            section = None
            for kind, pattern in [('projects',r'^(?:项目|研究项目|Project)'), ('experience',r'^(?:实习|工作经历|实践经历|Experience)'), ('education',r'教育|大学|本科|硕士|博士|Education|University'), ('skills',r'^(?:技能|语言|工具|Skills)'), ('summary',r'^(?:自我评价|个人总结|Summary)')]:
                if re.search(pattern, value, re.I): section = kind; break
            if section: current = section
            else: section = current
        assignments[fid] = fact.get('section') or section
    return {'profile':profile,'assignments':assignments}


def validate_structure(value, facts):
    try:
        result = ResumeStructure.model_validate(value).model_dump()
        originals = {f['id']:f['text'] for f in facts}
        if set(result['assignments']) != set(originals):
            raise ValueError('Missing or unknown facts')
        for field in result['profile'].values():
            if any(fid not in originals for fid in field['source_fact_ids']):
                raise ValueError('Unknown source fact')
            source = '\n'.join(originals[fid] for fid in field['source_fact_ids'])
            if field['value'] and (not field['source_fact_ids'] or field['value'] not in source):
                raise ValueError('Extracted value is not in source facts')
        # User-corrected section mappings take priority over model classifications.
        for fact in facts:
            if fact.get('section'): result['assignments'][fact['id']] = fact['section']
        return result
    except (ValidationError, ValueError, KeyError, TypeError):
        raise HTTPException(502, '简历字段映射未通过来源与完整性校验，请重试或校正事实；未生成简历版本')


def extract_structure(facts):
    provider = LLMProvider()
    raw = provider.complete('提取简历关键信息。只返回JSON：profile中name/email/phone/target_role各含value和source_fact_ids；assignments将每个事实ID唯一映射到personal/education/projects/experience/skills/summary/other。value必须逐字来自引用事实，不补全；每个事实必须有归属，不能删除或新增事实。', {'facts':facts})
    try:
        value = json.loads(raw.removeprefix('```json').removesuffix('```').strip())
    except (ValueError, TypeError):
        raise HTTPException(502, '模型未返回有效的简历字段映射')
    return {**validate_structure(value, facts), 'provider':provider.mode, 'model':provider.model}


def refresh_structure(facts, previous=None):
    value = local_structure(facts)
    if previous:
        value['assignments'].update({f['id']:previous['assignments'][f['id']] for f in facts if f['id'] in previous.get('assignments', {})})
    return validate_structure(value, facts)
