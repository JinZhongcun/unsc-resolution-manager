"""Load and validate external schema overrides for extensibility.

This layer is intentionally small:
- keep the existing fixed UI as the stable core
- allow option-list updates for existing fields
- allow additional fields per category / repeated block

It does *not* turn the whole application into a full CMS.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from form_spec import CATEGORY_ORDER
from masters import DURATION_UNIT_OPTIONS

EXTRA_FIELD_TYPES = {'text', 'textarea', 'integer', 'boolean', 'select', 'multiselect', 'date'}
REPEATED_CATEGORIES = {'sanctions', 'un_peace_operations', 'non_un_operations_enforcement_actions'}

DEFAULT_SCHEMA_OVERRIDES = {
    'option_overrides': {},
    'extra_fields': {category: [] for category in CATEGORY_ORDER},
}


def _deep_default() -> dict[str, Any]:
    return deepcopy(DEFAULT_SCHEMA_OVERRIDES)


def _normalize_field_def(raw: dict[str, Any], location: str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    field = {
        'key': str(raw.get('key') or '').strip(),
        'label': str(raw.get('label') or '').strip(),
        'type': str(raw.get('type') or '').strip(),
        'required': bool(raw.get('required', False)),
        'searchable': bool(raw.get('searchable', False)),
        'active': bool(raw.get('active', True)),
        'options': list(raw.get('options') or []),
        'help': str(raw.get('help') or '').strip(),
    }
    if not field['key']:
        errors.append(f'{location}: key is required.')
    if not field['label']:
        errors.append(f'{location}: label is required.')
    if field['type'] not in EXTRA_FIELD_TYPES:
        errors.append(f"{location}: type must be one of {sorted(EXTRA_FIELD_TYPES)}.")
    if field['type'] in {'select', 'multiselect'}:
        options = []
        seen = set()
        for value in field['options']:
            text = str(value).strip()
            if not text:
                continue
            if text not in seen:
                seen.add(text)
                options.append(text)
        field['options'] = options
        if not field['options']:
            errors.append(f'{location}: select / multiselect fields require options.')
    else:
        field['options'] = []
    return (field if not errors else None), errors


def validate_schema_overrides(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    extra_fields = schema.get('extra_fields', {})
    for category, defs in extra_fields.items():
        if category not in CATEGORY_ORDER:
            errors.append(f'extra_fields.{category}: unknown category.')
            continue
        if not isinstance(defs, list):
            errors.append(f'extra_fields.{category}: must be a list.')
            continue
        seen_keys: set[str] = set()
        for idx, raw in enumerate(defs):
            if not isinstance(raw, dict):
                errors.append(f'extra_fields.{category}[{idx}]: must be an object.')
                continue
            normalized, field_errors = _normalize_field_def(raw, f'extra_fields.{category}[{idx}]')
            errors.extend(field_errors)
            if normalized:
                if normalized['key'] in seen_keys:
                    errors.append(f'extra_fields.{category}[{idx}]: duplicate key {normalized["key"]}.')
                seen_keys.add(normalized['key'])
    option_overrides = schema.get('option_overrides', {})
    if not isinstance(option_overrides, dict):
        errors.append('option_overrides: must be an object.')
    else:
        for field_id, raw in option_overrides.items():
            if not isinstance(raw, dict):
                errors.append(f'option_overrides.{field_id}: must be an object.')
                continue
            for list_key in ('append_options', 'remove_options', 'replace_options'):
                if list_key in raw and raw[list_key] is not None and not isinstance(raw[list_key], list):
                    errors.append(f'option_overrides.{field_id}.{list_key}: must be a list.')
    return errors


def load_schema_overrides(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return _deep_default()
    text = path.read_text(encoding='utf-8').strip()
    if not text:
        return _deep_default()
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError('schema_overrides.json must be a JSON object.')
    schema = _deep_default()
    if isinstance(raw.get('option_overrides'), dict):
        schema['option_overrides'] = deepcopy(raw['option_overrides'])
    if isinstance(raw.get('extra_fields'), dict):
        for category in CATEGORY_ORDER:
            defs = raw['extra_fields'].get(category, [])
            if isinstance(defs, list):
                normalized_defs = []
                for idx, item in enumerate(defs):
                    if not isinstance(item, dict):
                        continue
                    normalized, field_errors = _normalize_field_def(item, f'extra_fields.{category}[{idx}]')
                    if field_errors:
                        raise ValueError('; '.join(field_errors))
                    if normalized is not None:
                        normalized_defs.append(normalized)
                schema['extra_fields'][category] = normalized_defs
    validation_errors = validate_schema_overrides(schema)
    if validation_errors:
        raise ValueError('\n'.join(validation_errors))
    return schema


def get_option_list(schema: dict[str, Any], field_id: str, default_options: list[str]) -> list[str]:
    override = (schema.get('option_overrides') or {}).get(field_id, {})
    if not isinstance(override, dict):
        return list(default_options)
    if isinstance(override.get('replace_options'), list):
        base = [str(v).strip() for v in override['replace_options'] if str(v).strip()]
    else:
        base = list(default_options)
    append_values = [str(v).strip() for v in override.get('append_options', []) if str(v).strip()]
    remove_values = {str(v).strip() for v in override.get('remove_options', []) if str(v).strip()}
    seen: set[str] = set()
    result: list[str] = []
    for value in base + append_values:
        if value and value not in seen and value not in remove_values:
            seen.add(value)
            result.append(value)
    return result


def get_extra_fields(schema: dict[str, Any], category: str) -> list[dict[str, Any]]:
    defs = (schema.get('extra_fields') or {}).get(category, [])
    if not isinstance(defs, list):
        return []
    return [deepcopy(item) for item in defs if isinstance(item, dict) and item.get('active', True)]


def empty_extra_payload(schema: dict[str, Any], category: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in get_extra_fields(schema, category):
        if field['type'] == 'multiselect':
            payload[field['key']] = []
        elif field['type'] == 'boolean':
            payload[field['key']] = False
        else:
            payload[field['key']] = None
    return payload


def public_schema_from_overrides(schema: dict[str, Any]) -> dict[str, Any]:
    extra_fields = {}
    for category in CATEGORY_ORDER:
        defs = []
        for field in get_extra_fields(schema, category):
            defs.append({
                'key': field['key'],
                'label': field['label'],
                'type': field['type'],
                'required': field['required'],
                'searchable': field['searchable'],
                'options': field['options'],
                'help': field['help'],
            })
        extra_fields[category] = defs
    option_overrides = {}
    for field_id, override in (schema.get('option_overrides') or {}).items():
        if not isinstance(override, dict):
            continue
        option_overrides[field_id] = {
            'append_options': [str(v).strip() for v in override.get('append_options', []) if str(v).strip()],
            'remove_options': [str(v).strip() for v in override.get('remove_options', []) if str(v).strip()],
            'replace_options': [str(v).strip() for v in override.get('replace_options', []) if str(v).strip()],
        }
    return {
        'extra_fields': extra_fields,
        'option_overrides': option_overrides,
        'notes': [
            'This file describes extension fields and option overrides.',
            'The core fixed form remains defined in the backend code and workbook-derived masters.',
        ],
    }


def default_override_template() -> dict[str, Any]:
    template = _deep_default()
    template['option_overrides'] = {
        'general.geographical_locations': {'append_options': [], 'remove_options': []},
        'membership.new_member_name': {'append_options': [], 'remove_options': []},
    }
    template['extra_fields']['general'] = [
        {
            'key': 'adoption_place',
            'label': 'Adoption place',
            'type': 'select',
            'options': ['New York'],
            'required': False,
            'searchable': True,
            'active': False,
            'help': 'Example extension field. Set active=true to enable.',
        }
    ]
    return template
