from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from packages.document_renderer import render


def test_pdf_qa_ignores_decorative_heading_prefix_but_checks_real_content(monkeypatch, tmp_path):
    monkeypatch.setenv("RENDER_ENABLED", "true")
    monkeypatch.setattr(render.Path, "exists", lambda self: True)
    monkeypatch.setattr(render, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(render.subprocess, "run", Mock())
    page = SimpleNamespace(rect=SimpleNamespace(width=600, height=800),
                           get_text=lambda kind=None: [] if kind == "words" else "项目经历")
    pdf = Mock()
    pdf.__enter__ = Mock(return_value=[page])
    pdf.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(render.pymupdf, "open", lambda path: pdf)
    result = render.compile_pdf("test", [{"id": "f1", "text": "ˌ 项目经历"}])
    assert result["status"] == "ready"
    result = render.compile_pdf("test", [{"id": "f1", "text": "项目经历缺失正文"}])
    assert result["status"] == "qa_failed"
    assert result["qa"]["missing_fact_ids"] == ["f1"]


@pytest.mark.parametrize("template", ["classic-cn", "classic-en", "modern-onepage", "gtm-original"])
def test_all_templates_fill_clean_text_without_imported_icons(monkeypatch, tmp_path, template):
    monkeypatch.setattr(render, "data_dir", lambda: tmp_path)
    facts = [
        {"id": "f1", "text": "ŵ 实习经历", "locked": False},
        {"id": "f2", "text": "Ǽ 项目经历", "locked": False},
        {"id": "f3", "text": "• 调研 20 家企业\n• 分析 DTC & Kickstarter", "locked": False},
        {"id": "f4", "text": "姓名：Zoë Williams", "locked": False},
    ]
    source = render.render_tex("clean-" + template, facts, template)
    assert not any(char in source for char in ("ŵ", "Ǽ", "•"))
    assert "调研 20 家企业" in source
    assert r"DTC \& Kickstarter" in source
    assert "Zoë Williams" in source
    assert (tmp_path / "artifacts" / ("clean-" + template) / "resume.tex").read_text(encoding="utf-8") == source
