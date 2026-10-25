import pymupdf
from packages.career.photo import extract_photo
from packages.document_renderer.render import render_tex


def original_pdf(with_photo=True):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((40, 40), "Resume with education and work experience")
        if with_photo:
            portrait = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 150), False)
            portrait.clear_with(180)
            page.insert_image(pymupdf.Rect(450, 60, 540, 195), stream=portrait.tobytes("png"))
        return pdf.tobytes()


def test_extracts_only_portrait_and_does_not_use_full_page_or_guess_missing_photo():
    photo = extract_photo(original_pdf(), "resume.pdf")
    assert photo.startswith(b"\x89PNG")
    image = pymupdf.Pixmap(photo)
    assert image.width < image.height
    assert extract_photo(original_pdf(False), "resume.pdf") is None
    assert extract_photo(b"plain text", "resume.txt") is None


def test_photo_written_only_into_this_versions_work_directory(monkeypatch, tmp_path):
    monkeypatch.setattr("packages.document_renderer.render.data_dir", lambda: tmp_path)
    photo = extract_photo(original_pdf(), "resume.pdf")
    source = render_tex("with-photo", [{"id":"f0", "text":"姓名：示例同学"}], "gtm-original", photo=photo)
    assert "photo.png" in source
    assert (tmp_path/"artifacts/with-photo/photo.png").read_bytes() == photo
    assert not (tmp_path/"artifacts/other/photo.png").exists()
