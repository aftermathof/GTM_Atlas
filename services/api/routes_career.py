import copy
import hashlib
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, Response
from services.api import storage
from sqlalchemy import select, delete
from services.api.auth import current_user
from services.api.config import data_dir
from services.api.db import Record, uid
from services.api.schemas import CareerSetup, ConfirmFacts, Rewrite, Feedback, Rollback
from services.api.store import owned, save, expose, trace
from packages.career.graph import parse_resume, diagnose, apply_patches
from packages.document_renderer.render import render_tex
from packages.document_renderer.jobs import enqueue, refresh
from services.api.suggestions import SuggestRewrite, suggest
from services.api.resume_blocks import BlockDialogue, apply_block_patches, group_blocks, discuss_block
from packages.career import approvals
from packages.career.structure import extract_structure, refresh_structure
from packages.career.retrieval import career_evidence
from packages.agent_core.registry import catalog

router = APIRouter(prefix="/api/v1/career")


@router.post('/job-descriptions')
async def upload_jd(request: Request, file: UploadFile = File(...), user=Depends(current_user)):
    filename = Path((file.filename or 'jd').replace('\\','/')).name
    content = await file.read(2_000_001)
    await file.close()
    if not content or len(content)>2_000_000:
        raise HTTPException(413,'JD不得为空或超过2MB')
    suffix = filename.rsplit('.',1)[-1].lower()
    if suffix in {'txt','md'}:
        try: text = content.decode('utf-8-sig')
        except UnicodeDecodeError: raise HTTPException(422,'请上传UTF-8编码的JD')
    elif suffix == 'pdf':
        import pymupdf
        try:
            with pymupdf.open(stream=content,filetype='pdf') as pdf:
                if len(pdf)>10 or pdf.needs_pass: raise HTTPException(422,'JD仅支持不超过10页的未加密PDF')
                text = '\n'.join(page.get_text() for page in pdf)
        except (RuntimeError, ValueError): raise HTTPException(422,'JD文件无法解析')
    else: raise HTTPException(422,'JD支持TXT、Markdown或可提取文字的PDF')
    if not 10 <= len(text.strip()) <= 8000:
        raise HTTPException(422,'JD需要10–8000字可读文本；扫描件请粘贴校对后的文字')
    with request.app.state.db() as db:
        row=save(db,user.id,'private_jd',{'title':filename.rsplit('.',1)[0],'body':text.strip(),'sha256':hashlib.sha256(content).hexdigest(),'filename':filename})
        storage.put_private(f'{user.id}/job-descriptions/{row.id}', content)
        if not storage.enabled():
            directory=data_dir()/'job-descriptions'/user.id
            directory.mkdir(parents=True,exist_ok=True)
            (directory/row.id).write_bytes(content)
        db.commit()
        return expose(row)


@router.post("/resumes")
async def upload(request: Request, file: UploadFile = File(...), user=Depends(current_user)):
    filename = Path((file.filename or "resume").replace("\\", "/")).name
    content = await file.read(10_000_001)
    await file.close()
    if not content or len(content) > 10_000_000:
        raise HTTPException(413, "简历不得为空或超过10MB")
    parsed = parse_resume(content, filename)
    with request.app.state.db() as db:
        row = save(db, user.id, "resume", {"filename": filename, "sha256": hashlib.sha256(content).hexdigest(), **parsed})
        storage.put_private(f'{user.id}/uploads/{row.id}', content)
        if not storage.enabled():
            directory = data_dir() / "uploads" / user.id
            directory.mkdir(parents=True, exist_ok=True)
            (directory / row.id).write_bytes(content)
        db.commit()
        return expose(row)


@router.post("/sessions")
def create(body: CareerSetup, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        resume = owned(db, body.resume_id, user.id, "resume")
        facts = resume.data["facts"]
        if body.jd_id:
            job = owned(db,body.jd_id,user.id,'private_jd')
            if not body.jd.strip(): body.jd = job.data['body']
        evidence = career_evidence(db, body.model_dump(), body.jd,owner_id=user.id)
        structure = extract_structure(facts) if facts else None
        thread_id = uid()
        row = save(db, user.id, "career", {"context": body.model_dump(), "facts": facts, "structure":structure, "confirmed": False, "status": "awaiting_confirmation", "approval_thread_id": thread_id, "active_version_id": None, "diagnosis": diagnose(facts, body.jd, body.role, evidence) if facts else None, "parse_warning": resume.data["warning"]})
        trace(db, user.id, "career_resume_graph", row.id, [{"node": "parse", "method": resume.data["method"]}, {"node": "await_fact_confirmation"}])
        db.commit()
        approvals.start(request.app.state.db, user.id, thread_id)
        return expose(row)


@router.get("/sessions/{sid}")
def get(sid: str, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        return expose(owned(db, sid, user.id, "career"))


@router.get("/sessions/{sid}/diagnosis")
def diagnosis(sid: str, request: Request, user=Depends(current_user)):
    return get(sid, request, user)["diagnosis"]


@router.post("/sessions/{sid}/confirm-facts")
def confirm(sid: str, body: ConfirmFacts, request: Request, user=Depends(current_user)):
    if len({f.id for f in body.facts}) != len(body.facts):
        raise HTTPException(422, "事实ID必须唯一")
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = owned(db, sid, user.id, "career", lock=True)
        facts = [f.model_dump(exclude_none=True) for f in body.facts]
        state = copy.deepcopy(row.data)
        state.pop("editing_blocks", None)
        was_confirmed = state["confirmed"]
        if was_confirmed:
            state["approval_thread_id"] = uid()
        evidence = career_evidence(db,state['context'],state['context'].get('jd',''),owner_id=user.id)
        structure = extract_structure(facts)
        state.update({"facts": facts, "structure":structure, "confirmed": True, "status": "diagnosed", "active_version_id": None, "diagnosis": diagnose(facts, state["context"].get("jd", ""), state["context"]["role"], evidence)})
        row.data = state
        trace(db, user.id, "career_resume_graph", sid, [{"node": "confirm_facts", "fact_ids": [f["id"] for f in facts]}, {"node": "await_rewrite_approval"}])
        db.commit()
        if was_confirmed:
            approvals.start(request.app.state.db, user.id, state["approval_thread_id"], True, [f["id"] for f in facts])
        else:
            approvals.confirm(request.app.state.db, user.id, state["approval_thread_id"], [f["id"] for f in facts])
        return expose(row)


@router.post("/sessions/{sid}/approve-rewrite")
def rewrite(sid: str, body: Rewrite, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = owned(db, sid, user.id, "career", lock=True)
        if not row.data["confirmed"]:
            raise HTTPException(409, "请先确认解析事实")
        base = row.data["facts"]
        if body.base_version_id:
            version = owned(db, body.base_version_id, user.id, "resume_version")
            if version.parent_id != sid:
                raise HTTPException(422, "版本不属于当前简历")
            base = version.data["facts"]
        if bool(body.patches) == bool(body.blocks):
            raise HTTPException(422, '请选择一种改写方式并提供修改内容')
        if body.blocks:
            mapping = (version.data if body.base_version_id else row.data).get('structure', {}).get('assignments', {})
            base = [{**f, 'section': f.get('section') or mapping.get(f['id'])} for f in base]
        facts = apply_block_patches(base, body.blocks, body.approved_fact_ids) if body.blocks else apply_patches(base, body.patches, body.approved_fact_ids)
        structure = refresh_structure(facts, version.data.get('structure') if body.base_version_id else row.data.get('structure'))
        # Each generated version has its own durable human approval checkpoint.
        approval_id = uid()
        approvals.approve(request.app.state.db, user.id, approval_id, [f["id"] for f in base], body.approved_fact_ids)
        version = save(db, user.id, "resume_version", {"facts": facts, "patches": [p.model_dump() for p in body.patches], "blocks": [b.model_dump() for b in body.blocks], "approved_fact_ids": body.approved_fact_ids, "approval_thread_id": approval_id, "base_version_id": body.base_version_id, "template": body.template, "status": "pending", "notice": "人工确认改写草稿；新增语义无法仅靠规则完全验证，请逐段复核。"}, sid)
        version.data = {**version.data, 'structure':structure}
        role = row.data['context'].get('role_raw') or next((r['name'] for r in catalog()['roles'] if r['id']==row.data['context']['role']), '')
        tex = render_tex(version.id, facts, body.template, structure, role)
        storage.put_private(f'{user.id}/artifacts/{version.id}/resume.tex', tex.encode('utf-8'), 'application/x-tex')
        job = save(db, user.id, "render_job", {"status": "queued", "version_id": version.id, "message": "等待隔离 PDF Worker；可先下载 .tex。启动 Worker 后刷新状态。"}, sid)
        enqueue(version.id, facts)
        version.data = {**version.data, "job_id": job.id}
        row.data = {**row.data, "active_version_id": version.id, "status": "editing"}
        trace(db, user.id, "career_resume_graph", sid, [{"node": "approval", "approved": body.approved_fact_ids}, {"node": "patch_validator"}, {"node": "latex_render", "version_id": version.id}])
        db.commit()
        return expose(version)


@router.post("/sessions/{sid}/suggest-rewrite")
def suggest_rewrite(sid: str, body: SuggestRewrite, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        row = owned(db, sid, user.id, "career")
        if not row.data["confirmed"]:
            raise HTTPException(409, "请先确认解析事实")
        facts = row.data["facts"]
        if body.base_version_id:
            base = owned(db, body.base_version_id, user.id, "resume_version")
            if base.parent_id != sid:
                raise HTTPException(422, "版本不属于当前简历")
            facts = base.data["facts"]
        context = row.data['context']
        evidence = career_evidence(db,context,context.get('jd',''),body.instruction,owner_id=user.id)
        result = suggest(facts, body, context.get('jd',''),evidence,context,row.data.get('structure'))
        trace(db, user.id, "career_resume_graph", sid, [{"node": "suggest_patch", "fact_ids": body.approved_fact_ids, "model": result["model"]}, {"node": "await_patch_review"}])
        db.commit()
        return result


@router.get('/sessions/{sid}/editing-blocks')
def editing_blocks(sid: str, request: Request, base_version_id: str | None = None, user=Depends(current_user)):
    with request.app.state.db() as db:
        row = owned(db, sid, user.id, 'career', lock=True)
        if not row.data['confirmed']:
            raise HTTPException(409, '请先确认解析事实')
        base = row
        if base_version_id:
            base = owned(db, base_version_id, user.id, 'resume_version', lock=True)
            if base.parent_id != sid:
                raise HTTPException(422, '版本不属于当前简历')
        if 'editing_blocks' not in base.data:
            blocks = group_blocks(base.data['facts'], base.data.get('structure') or {})
            base.data = {**base.data, 'editing_blocks': blocks}
            db.commit()
        return {'blocks': base.data['editing_blocks']}


@router.post('/sessions/{sid}/block-dialogue')
def block_dialogue(sid: str, body: BlockDialogue, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        row = owned(db, sid, user.id, 'career')
        if not row.data['confirmed']:
            raise HTTPException(409, '请先确认解析事实')
        base = row
        if body.base_version_id:
            base = owned(db, body.base_version_id, user.id, 'resume_version')
            if base.parent_id != sid:
                raise HTTPException(422, '版本不属于当前简历')
        context = row.data['context']
        evidence = career_evidence(db, context, context.get('jd',''), body.message, owner_id=user.id)
        mapping = base.data.get('structure', {}).get('assignments', {})
        facts = [{**f, 'section': f.get('section') or mapping.get(f['id'])} for f in base.data['facts']]
        return discuss_block(facts, body, context.get('jd',''), evidence, context)


@router.post("/sessions/{sid}/feedback")
def feedback(sid: str, body: Feedback, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        owned(db, sid, user.id, "career")
        save(db, user.id, "career_feedback", {"message": body.message}, sid)
        db.commit()
        return {"message": "反馈已保存；请在编辑器明确选择段落并确认修改。反馈不会自动生成简历。"}


@router.get("/sessions/{sid}/versions")
def versions(sid: str, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        owned(db, sid, user.id, "career")
        return [expose(v) for v in db.scalars(select(Record).where(Record.owner == user.id, Record.kind == "resume_version", Record.parent_id == sid).order_by(Record.created_at.desc()))]


@router.post("/sessions/{sid}/rollback")
def rollback(sid: str, body: Rollback, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = owned(db, sid, user.id, "career", lock=True)
        version = owned(db, body.version_id, user.id, "resume_version")
        if version.parent_id != sid:
            raise HTTPException(422, "版本不属于当前简历")
        # Pointer changes only; immutable source facts and old versions remain intact.
        row.data = {**row.data, "active_version_id": version.id, "status": "editing"}
        trace(db, user.id, "career_resume_graph", sid, [{"node": "rollback", "version_id": version.id}])
        db.commit()
        return expose(row)


@router.get("/versions/{vid}/artifacts")
def artifacts(vid: str, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        version = owned(db, vid, user.id, "resume_version")
        job = refresh(db, owned(db, version.data["job_id"], user.id, "render_job"))
        return {"version_id": vid, "job": expose(job), "tex": f"/api/v1/career/versions/{vid}/download/tex", "pdf": f"/api/v1/career/versions/{vid}/download/pdf" if job.data["status"] == "ready" else None}


@router.get("/versions/{vid}/download/{kind}")
def download(vid: str, kind: str, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        version = owned(db, vid, user.id, "resume_version")
        if kind not in {"tex", "pdf"}:
            raise HTTPException(404, "文件不存在")
        job = refresh(db, owned(db, version.data["job_id"], user.id, "render_job"))
        if kind == "pdf" and job.data["status"] != "ready":
            raise HTTPException(409, "PDF 尚未通过编译与 QA")
        if storage.enabled():
            return Response(storage.get_private(f'{user.id}/artifacts/{vid}/resume.{kind}'), media_type='application/pdf' if kind == 'pdf' else 'application/x-tex', headers={'Content-Disposition': f'attachment; filename="resume.{kind}"', 'Cache-Control': 'no-store'})
        path = data_dir() / "artifacts" / vid / ("resume." + kind)
        if not path.exists():
            raise HTTPException(404, "文件不存在")
        return FileResponse(path, filename="resume." + kind, media_type="application/pdf" if kind == "pdf" else "application/x-tex", headers={"Cache-Control": "no-store"})


@router.get("/resumes/{rid}/original")
def original(rid: str, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        row = owned(db, rid, user.id, "resume")
        if storage.enabled():
            from urllib.parse import quote
            return Response(storage.get_private(f'{user.id}/uploads/{rid}'), media_type='application/octet-stream', headers={'Content-Disposition': "attachment; filename*=UTF-8''" + quote(row.data['filename']), 'Cache-Control': 'no-store'})
        return FileResponse(data_dir() / "uploads" / user.id / rid, filename=row.data["filename"], headers={"Cache-Control": "no-store"})


@router.delete("/sessions/{sid}")
def remove(sid: str, request: Request, user=Depends(current_user)):
    import shutil
    from packages.agent_core.checkpoints import SQLCheckpointer
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = owned(db, sid, user.id, "career")
        children = db.scalars(select(Record).where(Record.owner == user.id, Record.parent_id == sid)).all()
        thread_ids = [row.data.get("approval_thread_id")]
        for child in children:
            if child.kind == "resume_version":
                thread_ids.append(child.data.get("approval_thread_id"))
                for kind in ('tex', 'pdf'):
                    storage.delete_private(f'{user.id}/artifacts/{child.id}/resume.{kind}')
                for suffix in [".request.json", ".result.json", ".tmp", '.request.failed', '.request.result.tmp']:
                    (data_dir() / "render-queue" / (child.id + suffix)).unlink(missing_ok=True)
                directory = data_dir() / "artifacts" / child.id
                if directory.exists():
                    shutil.rmtree(directory)
            if child.kind == 'chat_thread':
                db.execute(delete(Record).where(Record.owner == user.id, Record.parent_id == child.id, Record.kind.in_(['conversation', 'agent_run'])))
            db.delete(child)
        db.delete(row)
        rid = row.data["context"]["resume_id"]
        other = db.scalars(select(Record).where(Record.owner == user.id, Record.kind == "career", Record.id != sid)).all()
        if not any(r.data["context"]["resume_id"] == rid for r in other):
            upload = db.get(Record, rid)
            if upload and upload.owner == user.id:
                storage.delete_private(f'{user.id}/uploads/{rid}')
                (data_dir() / "uploads" / user.id / rid).unlink(missing_ok=True)
                db.delete(upload)
        db.commit()
        for thread_id in filter(None, thread_ids):
            SQLCheckpointer(request.app.state.db, user.id).delete_thread(thread_id)
        return {"deleted": True}
