# path: services/storage_service.py

from __future__ import annotations

import mimetypes
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

MEDIA_ROOT = os.getenv("MEDIA_ROOT", "media")

_ATTACHMENT_TOKEN_RE = re.compile(
    r"(?P<name>[\w\-\(\)]+?\.(?:jpg|jpeg|png|gif|webp|mp4|mov|mkv|mp3|wav|m4a|opus|ogg|pdf|doc|docx|xls|xlsx|ppt|pptx|txt|zip|rar))",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StoredFile:
    filename: str
    path: str
    mime_type: str | None
    size: int
    tipo: str


def _safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _guess_tipo_from_mime(mime_type: str | None) -> str:
    if not mime_type:
        return "file"
    major = mime_type.split("/", 1)[0].lower()
    if major in {"image", "audio", "video"}:
        return major
    return "file"


def store_media_file(*, src_path: str, team_id: int, chat_id: int) -> StoredFile:
    src = Path(src_path)
    filename = src.name

    mime_type, _ = mimetypes.guess_type(filename)
    tipo = _guess_tipo_from_mime(mime_type)

    dest_dir = Path(MEDIA_ROOT) / f"team_{team_id}" / f"chat_{chat_id}" / tipo
    _safe_mkdir(dest_dir)

    dest = dest_dir / filename
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        i = 2
        while True:
            candidate = dest_dir / f"{stem}__{i}{suffix}"
            if not candidate.exists():
                dest = candidate
                break
            i += 1

    shutil.copy2(str(src), str(dest))
    size = dest.stat().st_size

    return StoredFile(
        filename=dest.name,
        path=str(dest),
        mime_type=mime_type,
        size=size,
        tipo=tipo,
    )


def index_extracted_files(extract_dir: str, *, chat_txt_path: str) -> dict[str, str]:
    indexed: dict[str, str] = {}
    chat_txt_abs = str(Path(chat_txt_path).resolve())

    for root, _, files in os.walk(extract_dir):
        for name in files:
            full = str(Path(root, name).resolve())
            if full == chat_txt_abs:
                continue
            indexed[name] = full
    return indexed


def resolve_message_attachments(*, message_text: str, extracted_index: dict[str, str]) -> list[str]:
    if not message_text:
        return []
    tokens = [m.group("name") for m in _ATTACHMENT_TOKEN_RE.finditer(message_text)]
    return [extracted_index[t] for t in tokens if t in extracted_index]
