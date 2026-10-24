import pytest
from pydantic import ValidationError
from services.api.schemas import Answer, Chat


def test_mock_answer_can_be_sent_in_full_to_assistant():
    answer = Answer(answer="我的回答" * 2000, question_index=0, idempotency_key="test")
    prompt = f"题目：如何制定 GTM 策略？\n\n用户回答：{answer.answer}\n\n请结合资料给出更标准的回答："
    assert Chat(message=prompt).message == prompt


def test_assistant_prompt_still_has_an_input_limit():
    with pytest.raises(ValidationError):
        Chat(message="问" * 16001)
