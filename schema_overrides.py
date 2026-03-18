"""Load and validate editable schema overrides for additional fields.

This file allows the project to keep the Excel-driven fixed form while adding
new fields later without changing the Python source for every new field.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

VALID_CATEGORIES = {
    'general',
    'sanctions',
    'un_peace_operations',
    'non_un_operations_enforcement_actions',
    'criminal_tribunals',
    'other_subsidiary_organs',
    'thematic_resolutions',
    'membership',
    'appointment_related',
    'other',
}
REPEATED_CATEGORIES = {'sanctions', 'un_peace_operations', 'non_un_operations_enforcement_actions'}
VALID_TYPES = {'text', 'textarea', 'int', 'bool', 'date', 'select', 'multiselect'}
KEY_RE = re.compile(r'^[a-z][a-z0-9_]*$')
EMPTY_SCHEMA: dict[str, Any] = {'categories': {}}


def empty_schema() -> dict[str, Any]:
    return {'categories': {}}


def _normalize_options(value: Any, *, category: str, key: str, errors: list[str]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f'{category}.{key}.options は配列である必要があります。')
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        if text not in seen:
            seen.add(text)
            cleaned.append(text)
    return cleaned


def validate_schema(schema: Any) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if schema in (None, ''):
        return empty_schema(), []
    if not isinstance(schema, dict):
        return empty_schema(), ['schema_overrides.json のルートはオブジェクトである必要があります。']

    raw_categories = schema.get('categories', {})
    if raw_categories in (None, ''):
        raw_categories = {}
    if not isinstance(raw_categories, dict):
        return empty_schema(), ['schema_overrides.json の categories はオブジェクトである必要があります。']

    normalized: dict[str, Any] = {'categories': {}}
    for category, raw_fields in raw_categories.items():
        if category not in VALID_CATEGORIES:
            errors.append(f'未対応カテゴリ {category} が schema_overrides.json にあります。')
            continue
        if isinstance(raw_fields, dict):
            raw_fields = raw_fields.get('fields', [])
        if raw_fields in (None, ''):
            raw_fields = []
        if not isinstance(raw_fields, list):
            errors.append(f'{category} の定義は配列である必要があります。')
            continue
        normalized_fields: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for i, field in enumerate(raw_fields, start=1):
            if not isinstance(field, dict):
                errors.append(f'{category} の field #{i} はオブジェクトである必要があります。')
                continue
            key = str(field.get('key', '')).strip()
            label = str(field.get('label', '')).strip()
            field_type = str(field.get('type', '')).strip()
            required = bool(field.get('required', False))
            searchable = bool(field.get('searchable', False))
            help_text = str(field.get('help', '')).strip()
            if not key or not KEY_RE.match(key):
                errors.append(f'{category} の field #{i} は key を snake_case で定義してください。')
                continue
            if key in seen_keys:
                errors.append(f'{category}.{key} が重複しています。')
                continue
            if not label:
                errors.append(f'{category}.{key} は label が必要です。')
                continue
            if field_type not in VALID_TYPES:
                errors.append(f'{category}.{key} の type {field_type} は未対応です。')
                continue
            options = _normalize_options(field.get('options'), category=category, key=key, errors=errors)
            if field_type in {'select', 'multiselect'} and not options:
                errors.append(f'{category}.{key} は options が必要です。')
                continue
            if field_type not in {'select', 'multiselect'}:
                options = []
            normalized_fields.append({
                'key': key,
                'label': label,
                'type': field_type,
                'required': required,
                'searchable': searchable,
                'options': options,
                'help': help_text,
            })
            seen_keys.add(key)
        if normalized_fields:
            normalized['categories'][category] = normalized_fields
    return normalized, errors


def load_schema_overrides(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    path = Path(path)
    if not path.exists():
        return empty_schema(), []
    text = path.read_text(encoding='utf-8').strip()
    if not text:
        return empty_schema(), []
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        return empty_schema(), [f'schema_overrides.json の JSON が壊れています: {exc}']
    return validate_schema(raw)


def get_category_fields(schema: dict[str, Any], category: str) -> list[dict[str, Any]]:
    categories = schema.get('categories', {}) if isinstance(schema, dict) else {}
    fields = categories.get(category, [])
    return fields if isinstance(fields, list) else []


def default_value_for_field(field: dict[str, Any]) -> Any:
    field_type = field['type']
    if field_type == 'multiselect':
        return []
    if field_type == 'bool':
        return False
    if field_type == 'select':
        return None
    return ''
