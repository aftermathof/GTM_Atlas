import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["PROVIDER_MODE"] = "live"
os.environ["DATA_DIR"] = str(Path(".data/tests").resolve())

import pytest
from fastapi.testclient import TestClient
from services.api.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


def login(client, name="alice"):
    r = client.post("/api/v1/auth/register", json={"email": f"{name}@example.com", "password": "secure-password-2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_knowledge_permissions_and_citations(client):
    r = client.post("/api/v1/ai/chat", json={"message": "海外渠道销售与 KOL 营销的区别", "scope": "learning"})
    assert r.status_code == 200, r.text
    assert r.json()["citations"]
    assert r.json()["provider"] == "live"
    assert all(c["permission"] == "public_display" for c in r.json()["citations"])
    r = client.post("/api/v1/ai/chat", json={"message": "量子纠缠卫星推进器", "scope": "learning"})
    assert not r.json()['citations']
    assert '一般' in r.json()['limitations']


def test_mock_seed_idempotency_and_ownership(client):
    a, b = login(client), login(client, "bob")
    body = {"role": "kol_marketing", "industry": "consumer_electronics", "count": 5, "seed": 42}
    first = client.post("/api/v1/mock/sessions", json=body, headers=a).json()
    second = client.post("/api/v1/mock/sessions", json=body, headers=a).json()
    assert [q["text"] for q in first["questions"]] == [q["text"] for q in second["questions"]]
    assert len(set(q["dimension"] for q in first["questions"])) >= 3
    sid = first["id"]
    assert client.get(f"/api/v1/mock/sessions/{sid}", headers=b).status_code == 404
    answer = {"answer": "我负责分析渠道，先定位用户和库存问题，制定验证假设，再通过销量和利润复盘。", "idempotency_key": "answer-1", "question_index": 0}
    one = client.post(f"/api/v1/mock/sessions/{sid}/answers", json=answer, headers=a)
    two = client.post(f"/api/v1/mock/sessions/{sid}/answers", json=answer, headers=a)
    assert one.status_code == 200, one.text
    assert one.json() == two.json()
    assert len(client.get(f"/api/v1/mock/sessions/{sid}", headers=a).json()["answers"]) == 1


def test_resume_confirmation_authorization_and_versions(client):
    a = login(client)
    text = "张同学\n教育背景：示例大学 本科 2023-2027\n项目经历：负责AI运营培训资料整理，协作完成内部知识库。\n技能：Excel、英语。"
    r = client.post("/api/v1/career/resumes", files={"file": ("resume.txt", text.encode(), "text/plain")}, headers=a)
    assert r.status_code == 200, r.text
    session = client.post("/api/v1/career/sessions", json={"resume_id": r.json()["id"], "role": "overseas_channel_sales"}, headers=a).json()
    sid = session["id"]
    assert client.get(f"/api/v1/career/sessions/{sid}/versions", headers=a).json() == []
    patch = {"patches": [{"fact_id": "f2", "text": "负责AI运营培训资料整理；协作完成内部知识库。"}], "approved_fact_ids": ["f2"], "template": "classic-cn"}
    assert client.post(f"/api/v1/career/sessions/{sid}/approve-rewrite", json=patch, headers=a).status_code == 409
    facts = session["facts"]
    assert client.post(f"/api/v1/career/sessions/{sid}/confirm-facts", json={"facts": facts}, headers=a).status_code == 200
    illegal = {**patch, "approved_fact_ids": []}
    assert client.post(f"/api/v1/career/sessions/{sid}/approve-rewrite", json=illegal, headers=a).status_code == 422
    valid = client.post(f"/api/v1/career/sessions/{sid}/approve-rewrite", json=patch, headers=a)
    assert valid.status_code == 200, valid.text
    version = valid.json()
    assert version["facts"][1] == facts[1]
    assert version["facts"][2]["text"] == patch["patches"][0]["text"]
    assert client.get(f"/api/v1/career/sessions/{sid}/versions", headers=a).json()[0]["id"] == version["id"]


def test_private_endpoints_require_login(client):
    assert client.post("/api/v1/mock/sessions", json={"count": 5}).status_code == 401
    assert client.get("/api/v1/history").status_code == 401


def test_stt_is_explicitly_unconfigured_and_does_not_fake_transcript(client):
    a = login(client)
    r = client.post("/api/v1/ai/transcriptions", files={"file": ("voice.webm", b"not-real-audio", "audio/webm")}, headers=a)
    assert r.status_code == 503
    assert "STT" in r.json()["detail"]
