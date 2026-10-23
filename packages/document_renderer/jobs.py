import json
from services.api.config import data_dir


def enqueue(version_id, facts):
    directory = data_dir() / "render-queue"
    directory.mkdir(exist_ok=True)
    temporary = directory / (version_id + ".tmp")
    temporary.write_text(json.dumps({"version_id": version_id, "facts": facts}, ensure_ascii=False), encoding="utf-8")
    temporary.replace(directory / (version_id + ".request.json"))


def refresh(db, job):
    result = data_dir() / "render-queue" / (job.data["version_id"] + ".result.json")
    if result.exists():
        value = json.loads(result.read_text(encoding="utf-8"))
        if value.get("status") == "ready":
            from services.api import storage
            if storage.enabled() and not job.data.get('storage_synced'):
                pdf = data_dir() / 'artifacts' / job.data['version_id'] / 'resume.pdf'
                storage.put_private(f'{job.owner}/artifacts/{job.data["version_id"]}/resume.pdf', pdf.read_bytes(), 'application/pdf')
                value['storage_synced'] = True
            value["message"] = "PDF 已通过编译与内容 QA，可预览或下载。"
        job.data = {**job.data, **value}
        db.commit()
    return job
