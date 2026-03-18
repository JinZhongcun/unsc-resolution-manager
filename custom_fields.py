"""Helpers for runtime custom fields backed by schema_overrides.json."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from schema_overrides import default_value_for_field, get_category_fields, REPEATED_CATEGORIES


CUSTOM_KEY = '_custom'


def ensure_custom_defaults(record: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    for category in schema.get('categories', {}):
        fields = get_category_fields(schema, category)
        if not fields:
            continue
        if category in REPEATED_CATEGORIES:
            blocks = record.get(category, [])
            if not isinstance(blocks, list):
                continue
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                block.setdefault(CUSTOM_KEY, {})
                for field in fields:
                    block[CUSTOM_KEY].setdefault(field['key'], default_value_for_field(field))
        else:
            section = record.get(category)
            if not isinstance(section, dict):
                continue
            section.setdefault(CUSTOM_KEY, {})
            for field in fields:
                section[CUSTOM_KEY].setdefault(field['key'], default_value_for_field(field))
    return record


def empty_custom_payload(category: str, schema: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in get_category_fields(schema, category):
        payload[field['key']] = default_value_for_field(field)
    return payload


def _string(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _string(value).lower() in {'1', 'true', 'yes', 'y', 'on'}


def _optional_int(value: Any, *, field: str, errors: list[str]) -> int | None:
    raw = _string(value)
    if raw == '':
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        errors.append(f'{field} は整数で入力してください。')
        return None


def _date_to_iso(value: Any, *, field: str, errors: list[str], required: bool = False) -> str:
    raw = _string(value)
    if raw == '':
        if required:
            errors.append(f'{field} は必須です。')
        return ''
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    errors.append(f'{field} の日付形式が正しくありません。YYYY-MM-DD または DD/MM/YYYY を使用してください。')
    return ''


def normalize_custom_fields(category: str, raw_custom: Any, schema: dict[str, Any], errors: list[str], *, field_prefix: str) -> dict[str, Any]:
    fields = get_category_fields(schema, category)
    if not fields:
        return {}
    source = raw_custom if isinstance(raw_custom, dict) else {}
    normalized: dict[str, Any] = {}
    for field in fields:
        key = field['key']
        label = f'{field_prefix} / {field["label"]}'
        value = source.get(key)
        field_type = field['type']
        if field_type in {'text', 'textarea'}:
            norm = _string(value)
        elif field_type == 'int':
            norm = _optional_int(value, field=label, errors=errors)
        elif field_type == 'bool':
            norm = _bool(value)
        elif field_type == 'date':
            norm = _date_to_iso(value, field=label, errors=errors, required=field['required']) or ''
        elif field_type == 'select':
            if value in (None, ''):
                norm = None
            elif value not in field['options']:
                errors.append(f'{label} の値が選択肢にありません。')
                norm = None
            else:
                norm = value
        elif field_type == 'multiselect':
            raw_values = value if isinstance(value, list) else ([value] if value not in (None, '') else [])
            norm = []
            seen: set[str] = set()
            for item in raw_values:
                if item in ('', None):
                    continue
                if item not in field['options']:
                    errors.append(f'{label} の値 {item} は選択肢にありません。')
                    continue
                if item not in seen:
                    seen.add(item)
                    norm.append(item)
        else:
            norm = _string(value)
        if field['required']:
            if norm in (None, '', []):
                errors.append(f'{label} は必須です。')
        normalized[key] = norm
    return normalized


def collect_searchable_custom_tags(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()

    def add_value(value: Any) -> None:
        if value in (None, '', False):
            return
        if isinstance(value, list):
            for item in value:
                add_value(item)
            return
        text = str(value)
        if text not in seen:
            seen.add(text)
            tags.append(text)

    for category, fields in schema.get('categories', {}).items():
        searchable_keys = [field['key'] for field in fields if field.get('searchable')]
        if not searchable_keys:
            continue
        if category in REPEATED_CATEGORIES:
            for block in record.get(category, []):
                custom = block.get(CUSTOM_KEY, {}) if isinstance(block, dict) else {}
                for key in searchable_keys:
                    add_value(custom.get(key))
        else:
            section = record.get(category, {})
            custom = section.get(CUSTOM_KEY, {}) if isinstance(section, dict) else {}
            for key in searchable_keys:
                add_value(custom.get(key))
    return tags
