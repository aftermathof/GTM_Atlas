from typing import Literal
from pydantic import BaseModel, Field


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=12, max_length=128)


class Context(BaseModel):
    role: str = Field(default="", max_length=100)
    industry: str = Field(default="", max_length=100)
    region: str = Field(default="", max_length=100)
    language: Literal["zh-CN", "en"] = "zh-CN"
    role_raw: str = Field(default="", max_length=200)
    seniority: Literal["intern", "new_graduate", "experienced"] = "intern"
    business_model: Literal["B2B", "B2C", "hybrid", "unknown"] = "unknown"


class Chat(Context):
    message: str = Field(min_length=1, max_length=6000)
    scope: Literal["learning", "interview", "career", "global", "article"] = "global"
    document_id: str | None = None
    session_id: str | None = None
    conversation_id: str | None = Field(default=None, max_length=36)


class RefreshToken(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class Search(Context):
    query: str = Field(default="", max_length=1000)
    kind: Literal["learning", "interview", "jd"] | None = None


class MockSetup(Context):
    count: Literal[3, 5, 10] = 5
    seed: int = 42
    difficulty: Literal["基础", "进阶", "挑战"] = "基础"
    company: str = Field(default="", max_length=200)
    jd: str = Field(default="", max_length=8000)
    resume_session_id: str | None = None
    resume_version_id: str | None = None
    resume_consent: bool = False


class Answer(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)
    question_index: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=120)
    input_mode: Literal["text", "voice"] = "text"


class CareerSetup(Context):
    resume_id: str
    jd: str = Field(default="", max_length=8000)
    jd_id: str | None = None


class Fact(BaseModel):
    id: str = Field(pattern=r"^f\d+$")
    text: str = Field(min_length=1, max_length=4000)
    locked: bool = False
    confidence: float = Field(default=1.0, ge=0, le=1)
    page: int = Field(default=1, ge=1)
    section: Literal['personal','education','projects','experience','skills','summary','other'] | None = None


class ConfirmFacts(BaseModel):
    facts: list[Fact] = Field(min_length=1, max_length=100)


class Patch(BaseModel):
    fact_id: str
    text: str = Field(min_length=1, max_length=4000)


class Rewrite(BaseModel):
    patches: list[Patch] = Field(min_length=1, max_length=100)
    approved_fact_ids: list[str] = Field(min_length=1, max_length=100)
    template: Literal["classic-cn", "classic-en", "modern-onepage", "gtm-original"] = "gtm-original"
    base_version_id: str | None = None


class Feedback(BaseModel):
    message: str = Field(min_length=1, max_length=6000)


class Rollback(BaseModel):
    version_id: str
