"""One renderer worker. Reads file-backed queue, never needs database/network access."""
import json
import time
from pathlib import Path
from packages.document_renderer.render import compile_pdf
from services.api.config import data_dir

directory = data_dir() / "render-queue"
directory.mkdir(exist_ok=True)
while True:
    for file in directory.glob("*.request.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            result = compile_pdf(data["version_id"], data["facts"])
            temporary = file.with_suffix(".result.tmp")
            temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            temporary.replace(directory / (data["version_id"] + ".result.json"))
            file.unlink()
        except (OSError, ValueError, KeyError):
            file.rename(file.with_suffix(".failed"))
    time.sleep(2)
