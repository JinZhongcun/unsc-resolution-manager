"""JSON storage helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / 'data'
RECORDS_PATH = DATA_DIR / 'records.json'
PUBLIC_RECORDS_PATH = DATA_DIR / 'public_records.json'



def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not RECORDS_PATH.exists():
        RECORDS_PATH.write_text('[]\n', encoding='utf-8')
    if not PUBLIC_RECORDS_PATH.exists():
        PUBLIC_RECORDS_PATH.write_text('[]\n', encoding='utf-8')



def _load_json(path: Path) -> Any:
    if not path.exists():
        return []
    text = path.read_text(encoding='utf-8').strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f'{path.name} の JSON が壊れています。ファイル内容を修正してください。詳細: {exc}') from exc



def load_records() -> list[dict[str, Any]]:
    ensure_data_files()
    data = _load_json(RECORDS_PATH)
    if not isinstance(data, list):
        raise ValueError('records.json は配列である必要があります。')
    return data



def load_public_records() -> list[dict[str, Any]]:
    ensure_data_files()
    data = _load_json(PUBLIC_RECORDS_PATH)
    if not isinstance(data, list):
        raise ValueError('public_records.json は配列である必要があります。')
    return data



def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)



def save_records(records: list[dict[str, Any]]) -> None:
    atomic_write_json(RECORDS_PATH, records)



def upsert_record(records: list[dict[str, Any]], record: dict[str, Any]) -> list[dict[str, Any]]:
    record_id = record.get('record_id')
    updated = list(records)
    for idx, existing in enumerate(updated):
        if existing.get('record_id') == record_id:
            updated[idx] = record
            break
    else:
        updated.append(record)
    return updated
