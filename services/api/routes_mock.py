import copy
import uuid
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select, delete
from services.api.auth import current_user
from services.api.db import Record
from services.api.schemas import MockSetup, Answer
from services.api.store import owned, save, expose, trace
from packages.mock.graph import plan_interview, evaluate_answer
from packages.agent_core.checkpoints import SQLCheckpointer

from services.api.streaming import AIStreamingRoute

router = APIRouter(prefix="/api/v1/mock", route_class=AIStreamingRoute)


@router.post("/sessions")
def create(body: MockSetup, request: Request, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        facts = None
        if body.resume_session_id or body.resume_version_id:
            if not body.resume_consent:
                raise HTTPException(422, "引用简历需要显式授权")
            row = owned(db, body.resume_version_id or body.resume_session_id, user.id, "resume_version" if body.resume_version_id else "career")
            if body.resume_version_id and body.resume_session_id and row.parent_id != body.resume_session_id:
                raise HTTPException(422, "简历版本不属于所选会话")
            if not body.resume_version_id and not row.data["confirmed"]:
                raise HTTPException(409, "请先确认简历事实")
            facts = row.data["facts"]
        previous = [q['text'] for questions in db.scalars(select(Record.data['questions']).where(Record.owner == user.id, Record.kind == 'mock').order_by(Record.created_at)) for q in questions or [] if isinstance(q, dict) and isinstance(q.get('text'), str)]
        row = save(db, user.id, "mock", plan_interview(db, body, facts, excluded_questions=previous))
        trace(db, user.id, "mock_interview_graph", row.id, [{"node": "planner", "seed": body.seed, "blueprint": "blueprint-1"}])
        db.commit()
        return expose(row)


@router.get("/sessions/{sid}")
def get(sid: str, request: Request, user=Depends(current_user)):
    with request.app.state.db() as db:
        return expose(owned(db, sid, user.id, "mock"))


@router.post("/sessions/{sid}/answers")
def answer(sid: str, body: Answer, request: Request, user=Depends(current_user)):
    # SQLite needs a process lock; PostgreSQL additionally uses row locks.
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = owned(db, sid, user.id, "mock", lock=True)
        key = sid + ":" + body.idempotency_key
        prior = db.scalar(select(Record).where(Record.owner == user.id, Record.kind == "mock_answer", Record.idempotency_key == key))
        if prior:
            if prior.data["submission"] != body.model_dump():
                raise HTTPException(409, "幂等键已用于不同回答")
            return prior.data["response"]
        state = copy.deepcopy(row.data)
        if state["status"] == "completed" or state["current_question_index"] != body.question_index:
            raise HTTPException(409, "题目状态已变更，请刷新后重试")
        thread_id = str(uuid.uuid5(uuid.NAMESPACE_URL, user.id + key))
        evaluation = evaluate_answer(state, body.model_dump(), SQLCheckpointer(request.app.state.db, user.id), thread_id)
        state["answers"].append({**body.model_dump(), "evaluation": evaluation, "question": state["pending_followup"] or state["questions"][body.question_index]["text"]})
        followups = state["followup_counts"].get(str(body.question_index), 0)
        if evaluation.get("followup"):
            state["pending_followup"] = evaluation["followup"]
            state["followup_counts"][str(body.question_index)] = followups + 1
        else:
            state["pending_followup"] = None
            state["current_question_index"] += 1
        if state["current_question_index"] >= len(state["questions"]):
            state["status"] = "completed"
        row.data = state
        result = expose(row)
        save(db, user.id, "mock_answer", {"submission": body.model_dump(), "response": result}, sid, key)
        trace(db, user.id, "mock_interview_graph", sid, [{"node": "answer_evaluator", "question_index": body.question_index, "model": evaluation["model"]}, {"node": "await_answer" if state["status"] != "completed" else "report", "followup_count": state["followup_counts"].get(str(body.question_index), 0)}])
        db.commit()
        return result


@router.post("/sessions/{sid}/next")
def next_question(sid: str, request: Request, user=Depends(current_user)):
    # Reading next must never skip an unanswered question.
    return get(sid, request, user)


@router.get("/sessions/{sid}/history")
def history(sid: str, request: Request, user=Depends(current_user)):
    return get(sid, request, user)["answers"]


@router.get("/sessions/{sid}/report")
def report(sid: str, request: Request, user=Depends(current_user)):
    state = get(sid, request, user)
    return report_snapshot(state)


def report_snapshot(state):
    scores = [a["evaluation"]["score"] for a in state["answers"] if a["evaluation"]["score"] is not None]
    return {**state, "average_score": round(sum(scores) / len(scores)) if scores else None, "recommendations": ["用 STAR 结构重答薄弱题，区分个人行动与团队结果。", "补充指标口径、归因限制与下一步验证计划。"], "notice": "训练参考；语音识别误差可能影响评价，请以校对后的文字为准。"}


@router.delete('/sessions/{sid}')
def remove(sid: str, request: Request, only_if_unanswered: bool = False, user=Depends(current_user)):
    with request.app.state.mutation_lock, request.app.state.db() as db:
        row = owned(db, sid, user.id, 'mock', lock=True)
        if only_if_unanswered and row.data.get('answers'):
            return {'deleted': False}
        answers = db.scalars(select(Record).where(Record.owner == user.id, Record.parent_id == sid, Record.kind == 'mock_answer')).all()
        threads = [str(uuid.uuid5(uuid.NAMESPACE_URL, user.id + a.idempotency_key)) for a in answers]
        db.execute(delete(Record).where(Record.owner == user.id, Record.parent_id == sid))
        db.delete(row)
        db.commit()
    for thread in threads:
        SQLCheckpointer(request.app.state.db, user.id).delete_thread(thread)
    return {'deleted': True}
