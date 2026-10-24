import json
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from services.api.schemas import MockSetup
from packages.mock.graph import plan_interview
from packages.agent_core.providers import LLMProvider


@pytest.mark.parametrize('count', [1, 2, 7, 20])
def test_custom_count_produces_distinct_questions(monkeypatch, count):
    monkeypatch.setattr('packages.mock.graph.search', lambda *a, **k: [])
    result = plan_interview(None, MockSetup(count=count))
    assert len(result['questions']) == count
    assert len({q['text'] for q in result['questions']}) == count
    assert len({q['dimension'] for q in result['questions']}) >= min(3, count)


@pytest.mark.parametrize('count', [0, 21, 1.5])
def test_custom_count_has_a_bounded_integer_range(count):
    with pytest.raises(ValidationError):
        MockSetup(count=count)


def test_seed_is_generated_per_request():
    assert MockSetup().seed != MockSetup().seed


def test_planner_avoids_prior_questions_and_rejects_model_repeats(monkeypatch):
    monkeypatch.setattr('packages.mock.graph.search', lambda *a, **k: [])
    first = plan_interview(None, MockSetup(count=3, seed=42))
    previous = [q['text'] for q in first['questions']]
    second = plan_interview(None, MockSetup(count=3, seed=42), excluded_questions=previous)
    assert not set(previous) & {q['text'] for q in second['questions']}
    monkeypatch.setattr(LLMProvider, 'complete', lambda *a: json.dumps({'questions': first['questions']}))
    with pytest.raises(HTTPException) as error:
        plan_interview(None, MockSetup(count=3), excluded_questions=previous)
    assert error.value.status_code == 503


def test_single_question_can_reference_resume(monkeypatch):
    monkeypatch.setattr('packages.mock.graph.search', lambda *a, **k: [])
    result = plan_interview(None, MockSetup(count=1), [{'id':'f1','text':'参与用户调研并整理访谈材料，协作完善工作流程。','locked':False}])
    assert result['questions'][0]['source_type'] == 'authorized_resume'
