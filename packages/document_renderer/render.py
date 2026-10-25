import os
from pathlib import Path
import subprocess
import pymupdf
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from services.api.config import ROOT, data_dir
from packages.career.structure import refresh_structure
from packages.document_renderer.layout import build_layout, qa_fragments


def escape_tex(value):
    mapping = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&", "#": r"\#", "%": r"\%", "_": r"\_", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(mapping.get(c, c) for c in value)


def render_tex(version_id, facts, template, structure=None, target_role='', photo=None):
    if template not in {"classic-cn", "classic-en", "modern-onepage", "gtm-original"}:
        raise ValueError("Unknown template")
    env = Environment(loader=FileSystemLoader(ROOT / "templates/latex"), undefined=StrictUndefined, autoescape=False)
    mapping = refresh_structure(facts, structure)
    layout = build_layout(facts, mapping)
    def escaped_value(value):
        if isinstance(value, str): return escape_tex(value)
        if isinstance(value, list): return [escaped_value(item) for item in value]
        return {key: escaped_value(item) for key, item in value.items()}
    preamble = (ROOT / 'templates/latex/gtm-original/preamble.tex').read_text(encoding='utf-8') if template == 'gtm-original' else ''
    source = env.get_template(template + "/resume.tex.j2").render(layout=escaped_value(layout), target_role=escape_tex(target_role), preamble=preamble, has_photo=bool(photo), has_target_role=any('求职意向' in item or '目标岗位' in item for item in layout['personal']))
    directory = data_dir() / "artifacts" / version_id
    directory.mkdir(parents=True, exist_ok=True)
    if photo:
        (directory / 'photo.png').write_bytes(photo)
    (directory / "resume.tex").write_text(source, encoding="utf-8")
    return source


def compile_pdf(version_id, facts):
    if os.getenv("RENDER_ENABLED") != "true" or not Path("/renderer-sandbox").exists():
        return {"status": "requires_renderer", "message": "TeX 已生成。PDF 需启动隔离 renderer Worker；宿主机不会执行 LaTeX。"}
    directory = data_dir() / "artifacts" / version_id
    try:
        subprocess.run(["xelatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"], cwd=directory, timeout=35, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "openin_any": "p", "openout_any": "p"})
        with pymupdf.open(directory / "resume.pdf") as pdf:
            extracted = "".join(p.get_text() for p in pdf)
            squash = lambda s: "".join(s.split())
            mapping = refresh_structure(facts)['assignments']
            missing = [f["id"] for f in facts if any(squash(part) not in squash(extracted) for part in qa_fragments(f, mapping[f['id']]))]
            overflow = any(word[0] < 20 or word[1] < 20 or word[2] > page.rect.width - 20 or word[3] > page.rect.height - 20 for page in pdf for word in page.get_text("words"))
            qa = {"pages": len(pdf), "missing_fact_ids": missing, "overflow": overflow}
        if missing or overflow or qa["pages"] > 2:
            (directory / "resume.pdf").unlink(missing_ok=True)
            return {"status": "qa_failed", "qa": qa}
        return {"status": "ready", "qa": qa}
    except (subprocess.SubprocessError, RuntimeError, OSError):
        (directory / "resume.pdf").unlink(missing_ok=True)
        return {"status": "failed", "message": "隔离编译失败或超时；已有版本未变。"}
