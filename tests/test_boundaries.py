import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from services.api.db import Base, Document, Chunk, Record, make_database
from packages.rag.knowledge import ingest, search
from packages.career.graph import apply_patches
from packages.document_renderer.render import escape_tex
from services.api.schemas import Patch
from tests.test_workflows import login, client


def test_forbidden_and_deleted_documents_never_searchable(tmp_path):
    engine, factory = make_database("sqlite://")
    Base.metadata.create_all(engine)
    source = "---\nid: source\ntitle: KOL营销\nkind: learning\nrole_tags: [kol_marketing]\nindustry_tags: []\nsource_type: original\npermission: public_display\nquality_status: reviewed\n---\n## KOL营销\n合法的学习证据"
    path = tmp_path / "sample.md"
    path.write_text(source, encoding="utf-8")
    with factory() as db:
        ingest(db, tmp_path)
        assert search(db, "KOL营销")
        path.write_text(source.replace("public_display", "no_llm"), encoding="utf-8")
        ingest(db, tmp_path)
        assert not search(db, "KOL营销")
        assert not db.scalars(select(Chunk)).all()
        path.write_text(source, encoding="utf-8")
        ingest(db, tmp_path)
        path.unlink()
        assert ingest(db, tmp_path)["deleted"] == 1
        assert not search(db, "KOL营销")


@pytest.mark.parametrize("text", [r"\input{secret}"])
def test_patch_rejects_tex_commands(text):
    with pytest.raises(HTTPException):
        apply_patches([{"id": "f0", "text": "负责渠道分析", "locked": False}], [Patch(fact_id="f0", text=text)], ["f0"])


def test_locked_education_cannot_be_rewritten():
    with pytest.raises(HTTPException):
        apply_patches([{"id": "f0", "text": "教育：示例大学", "locked": True}], [Patch(fact_id="f0", text="其他大学")], ["f0"])


def test_tex_escapes_all_user_macros():
    assert escape_tex(r"\input{/etc/passwd} 50% & x_y") == r"\textbackslash{}input\{/etc/passwd\} 50\% \& x\_y"


def test_mock_allows_repeated_followups_and_completes_when_answers_are_sufficient(client):
    headers = login(client)
    sid = client.post("/api/v1/mock/sessions", json={"count": 3}, headers=headers).json()["id"]
    for question_index in range(3):
        # Exercise more rounds than the old total-step and per-question limits.
        followups = 8 if question_index == 0 else 2
        for turn in range(followups):
            response = client.post(f"/api/v1/mock/sessions/{sid}/answers", json={"answer": "我先验证需求，再分析渠道数据，最后复盘。", "question_index": question_index, "idempotency_key": f"question-{question_index}-followup-{turn}"}, headers=headers)
            assert response.status_code == 200, response.text
            state = response.json()
            assert state["status"] == "in_progress"
            assert state["current_question_index"] == question_index
            assert state["followup_counts"][str(question_index)] == turn + 1
            assert state["pending_followup"]
        # The offline provider returns no followup for this detailed answer.
        detailed_answer = "我负责新品渠道试点，先访谈目标客户并核对需求，再按获客成本与转化率选择渠道，以小预算分组实验验证假设，统一指标口径后复盘结果，并据此调整投放与库存计划。" * 3
        response = client.post(f"/api/v1/mock/sessions/{sid}/answers", json={"answer": detailed_answer, "question_index": question_index, "idempotency_key": f"question-{question_index}-complete"}, headers=headers)
        assert response.status_code == 200, response.text
        state = response.json()
        assert state["current_question_index"] == question_index + 1
        assert state["pending_followup"] is None
    assert response.json()["status"] == "completed"
    report = client.get(f"/api/v1/mock/sessions/{sid}/report", headers=headers)
    assert report.status_code == 200 and report.json()["average_score"] is not None


def test_unauthorized_resume_context_and_artifacts(client):
    a, b = login(client), login(client, "other")
    resume = client.post('/api/v1/career/resumes', files={"file": ("resume.txt", "姓名：示例\n教育：示例大学\n经历：负责AI运营知识整理与项目协作".encode(), "text/plain")}, headers=a).json()
    state = client.post('/api/v1/career/sessions', json={"resume_id": resume["id"]}, headers=a).json()
    sid = state["id"]
    assert client.post('/api/v1/mock/sessions', json={"resume_session_id": sid}, headers=a).status_code == 422
    assert client.post('/api/v1/mock/sessions', json={"resume_session_id": sid, "resume_consent": True}, headers=a).status_code == 409
    assert client.post('/api/v1/ai/chat', json={"message": "怎么修改", "scope": "career", "session_id": sid}, headers=b).status_code == 404
    assert client.get(f'/api/v1/career/resumes/{resume["id"]}/original', headers=b).status_code == 404
    client.post(f'/api/v1/career/sessions/{sid}/confirm-facts', json={"facts": state["facts"]}, headers=a)
    mock = client.post('/api/v1/mock/sessions', json={"resume_session_id": sid, "resume_consent": True}, headers=a).json()
    assert mock["questions"][2]["source_type"] == "authorized_resume"
    assert "AI运营" in mock["questions"][2]["text"]


def test_scan_requires_ocr_or_manual_confirmation(client):
    import pymupdf
    pdf = pymupdf.open(); pdf.new_page(); content = pdf.tobytes(); pdf.close()
    headers = login(client)
    result = client.post('/api/v1/career/resumes', files={"file": ("scan.pdf", content, "application/pdf")}, headers=headers)
    assert result.status_code == 200
    assert result.json()["needs_ocr"] is True
    assert result.json()["facts"] == []


def test_forged_citation_is_blocked(client, monkeypatch):
    from packages.agent_core.providers import LLMProvider
    monkeypatch.setattr(LLMProvider, "complete", lambda *args: "Fake answer [not-real:99]")
    result = client.post('/api/v1/ai/chat', json={"message": "KOL营销", "scope": "learning"}).json()
    assert result["citations"] == []
    assert "引用校验失败" in result["answer"]
