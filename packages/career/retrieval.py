import re
from packages.rag.knowledge import search
from services.api.db import Record


def career_evidence(db, context, jd='', instruction='', owner_id=None):
    # Explicit JD supplies the retrieval query; personal resume text is not used as a public search query.
    query = ' '.join(re.findall(r'[\w\u4e00-\u9fff]+', jd + ' ' + instruction))[:900]
    query = query or 'GTM 市场 用户 调研 项目 上市 渠道 协作 业务分析'
    evidence = []
    if context.get('jd_id') and owner_id:
        job = db.get(Record,context['jd_id'])
        if job and job.owner==owner_id and job.kind=='private_jd':
            evidence.append({'chunk_id':'private-jd-'+job.id+':0','doc_id':job.id,'title':job.data['title'],'heading_path':'用户上传的原始JD','text':job.data['body'],'kind':'jd','permission':'private','source_type':'user_uploaded','quality_status':'user_provided','url':'/learn/'+job.id,'demo':False})
    for kind, quota in [('jd',3),('learning',3),('interview',2)]:
        matches = search(db,query,kind,context.get('role',''),context.get('industry',''),top_k=quota,include_demo=False)
        if not matches and context.get('role'):
            matches = search(db,query,kind,industry=context.get('industry',''),top_k=quota,include_demo=False)
            matches = [{**m,'cross_role_reference':True} for m in matches]
        evidence.extend(matches)
    return evidence
