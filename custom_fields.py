"""Runtime helpers for extension fields defined in schema_overrides.json."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from form_spec import CATEGORY_ORDER
from schema_overrides import REPEATED_CATEGORIES, empty_extra_payload, get_extra_fields


def ensure_extra_containers(record: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(record)
    for category in CATEGORY_ORDER:
        defs = get_extra_fields(schema, category)
        if not defs:
            continue
        if category in REPEATED_CATEGORIES:
            blocks = updated.get(category, [])
            for block in blocks:
                if '_extra' not in block or not isinstance(block['_extra'], dict):
                    block['_extra'] = empty_extra_payload(schema, category)
                else:
                    for key, default in empty_extra_payload(schema, category).items():
                        block['_extra'].setdefault(key, default)
        else:
            target = updated.get(category, {})
            if not isinstance(target, dict):
                target = {}
                updated[category] = target
            if '_extra' not in target or not isinstance(target['_extra'], dict):
                target['_extra'] = empty_extra_payload(schema, category)
            else:
                for key, default in empty_extra_payload(schema, category).items():
                    target['_extra'].setdefault(key, default)
    return updated


def _to_string(value: Any) -> str:
    if value in (None, ''):
        return ''
    return str(value).strip()


def _to_optional_int(value: Any, field: str, errors: list[str]) -> int | None:
    if value in (None, ''):
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        errors.append(f'{field}: must be an integer.')
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (1, '1', 'true', 'True', 'yes', 'Yes'):
        return True
    return False


def _to_date(value: Any, field: str, errors: list[str]) -> str | None:
    if value in (None, ''):
        return None
    text = str(value).strip()
    for fmt in ('%Y-%m-%d', '%Y%m%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(text, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    errors.append(f'{field}: invalid date. Use YYYY-MM-DD or YYYYMMDD or DD/MM/YYYY.')
    return None


def normalize_extra_payload(payload: dict[str, Any], field_defs: list[dict[str, Any]], field_prefix: str, errors: list[str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    source = payload if isinstance(payload, dict) else {}
    for field in field_defs:
        key = field['key']
        label = f'{field_prefix} / {field["label"]}'
        raw = source.get(key)
        if field['type'] in {'text', 'textarea'}:
            value = _to_string(raw)
        elif field['type'] == 'integer':
            value = _to_optional_int(raw, label, errors)
        elif field['type'] == 'boolean':
            value = _to_bool(raw)
        elif field['type'] == 'date':
            value = _to_date(raw, label, errors)
        elif field['type'] == 'select':
            value = None if raw in (None, '') else str(raw).strip()
            if value is not None and value not in field['options']:
                errors.append(f'{label}: value must be one of the configured options.')
                value = None
        elif field['type'] == 'multiselect':
            values = raw if isinstance(raw, list) else ([] if raw in (None, '') else [raw])
            cleaned: list[str] = []
            seen: set[str] = set()
            for item in values:
                text = str(item).strip()
                if not text:
                    continue
                if text not in field['options']:
                    errors.append(f'{label}: contains a value outside the configured options.')
                    continue
                if text not in seen:
                    seen.add(text)
                    cleaned.append(text)
            value = cleaned
        else:
            value = raw
        if field['required']:
            if field['type'] == 'multiselect' and not value:
                errors.append(f'{label}: required.')
            elif field['type'] == 'boolean':
                pass
            elif value in (None, ''):
                errors.append(f'{label}: required.')
        normalized[key] = value
    return normalized


def payload_has_meaningful_value(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    for value in payload.values():
        if isinstance(value, list) and value:
            return True
        if isinstance(value, bool) and value:
            return True
        if value not in (None, '', False, []):
            return True
    return False


def extract_searchable_tags(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for category in CATEGORY_ORDER:
        defs = [field for field in get_extra_fields(schema, category) if field.get('searchable')]
        if not defs:
            continue
        if category in REPEATED_CATEGORIES:
            for block in record.get(category, []):
                payload = block.get('_extra', {}) if isinstance(block, dict) else {}
                for field in defs:
                    raw = payload.get(field['key'])
                    values = raw if isinstance(raw, list) else [raw]
                    for item in values:
                        if item in (None, '', False):
                            continue
                        text = str(item)
                        if text not in seen:
                            seen.add(text)
                            tags.append(text)
        else:
            payload = record.get(category, {}).get('_extra', {}) if isinstance(record.get(category), dict) else {}
            for field in defs:
                raw = payload.get(field['key'])
                values = raw if isinstance(raw, list) else [raw]
                for item in values:
                    if item in (None, '', False):
                        continue
                    text = str(item)
                    if text not in seen:
                        seen.add(text)
                        tags.append(text)
    return tags
