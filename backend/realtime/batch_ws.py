from __future__ import annotations
import re, json
from flask import current_app
from flask_socketio import Namespace, join_room, emit

_ROOM_RE = re.compile(r"^[a-f0-9\-]{16,64}$")

def _meta_key(job_id: str) -> str:
    return f"draks:batch:{job_id}:meta"

class BatchNamespace(Namespace):
    def on_connect(self):
        # İsteğe göre auth eklenebilir; şu an oda katılımında job_id doğruluyoruz
        emit("hello", {"ok": True})

    def on_join(self, data):
        job_id = (data or {}).get("job_id", "")
        if not isinstance(job_id, str) or not _ROOM_RE.match(job_id):
            emit("error", {"error": "invalid_job"})
            return
        # (Opsiyonel) sahiplik kontrolü için Redis meta'ya bakılabilir
        # r = current_app.extensions["redis_client"]; meta = r.get(_meta_key(job_id))
        join_room(f"job:{job_id}")
        emit("joined", {"job_id": job_id})

def init_batch_namespace(socketio, app):
    socketio.on_namespace(BatchNamespace("/batch"))
