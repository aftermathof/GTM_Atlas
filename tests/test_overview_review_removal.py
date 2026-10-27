import re
from services.api.config import ROOT
from packages.rag.reference_sources import reference_documents


def test_all_overview_chapter_reviews_and_links_are_removed():
    files=list((ROOT/'knowledge/site/gtm-overview').glob('*.html'))
    assert len(files)==5
    for file in files:
        raw=file.read_text(encoding='utf-8')
        assert '章末自测' not in raw
        assert not re.search(r'<section[^>]*class="review"',raw)
        assert 'href="#review"' not in raw
    for name,raw in reference_documents(ROOT):
        if 'overview' in name:
            assert '章末自测' not in raw
