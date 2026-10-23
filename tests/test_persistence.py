from fastapi.testclient import TestClient
from services.api.main import create_app
from tests.test_workflows import login


def test_restart_restores_session_and_duplicate_response(tmp_path):
    url = "sqlite:///" + (tmp_path / "persist.db").as_posix()
    with TestClient(create_app(url)) as c:
        headers = login(c)
        sid = c.post('/api/v1/mock/sessions', json={"count": 3}, headers=headers).json()["id"]
        submission = {"question_index": 0, "answer": "我先验证渠道数据，再复盘真实的结果。", "idempotency_key": "durable-key"}
        response = c.post(f'/api/v1/mock/sessions/{sid}/answers', json=submission, headers=headers)
        assert response.status_code == 200, response.text
        saved = response.json()
    with TestClient(create_app(url)) as c:
        assert c.get(f'/api/v1/mock/sessions/{sid}', headers=headers).json()["answers"] == saved["answers"]
        assert c.post(f'/api/v1/mock/sessions/{sid}/answers', json=submission, headers=headers).json() == saved


def test_ai_suggestion_does_not_create_version():
    with TestClient(create_app("sqlite://")) as c:
        headers = login(c)
        resume = c.post('/api/v1/career/resumes', files={"file": ("r.txt", "姓名：测试同学\n教育：示例大学\n经历：负责AI运营知识整理，协作完成培训材料".encode(), "text/plain")}, headers=headers).json()
        state = c.post('/api/v1/career/sessions', json={"resume_id": resume["id"]}, headers=headers).json()
        sid = state["id"]
        c.post(f'/api/v1/career/sessions/{sid}/confirm-facts', json={"facts": state["facts"]}, headers=headers)
        suggestion = c.post(f'/api/v1/career/sessions/{sid}/suggest-rewrite', json={"approved_fact_ids": ["f2"]}, headers=headers)
        assert suggestion.status_code == 200, suggestion.text
        assert suggestion.json()["patches"][0]["fact_id"] == "f2"
        assert c.get(f'/api/v1/career/sessions/{sid}/versions', headers=headers).json() == []
