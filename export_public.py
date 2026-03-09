"""Export records.json into a front-end friendly JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from form_spec import CATEGORY_LABELS


def _collect_values(value: Any) -> list[str]:
    results: list[str] = []
    if value in (None, '', False):
        return results
    if isinstance(value, list):
        for item in value:
            results.extend(_collect_values(item))
        return results
    if isinstance(value, dict):
        for item in value.values():
            results.extend(_collect_values(item))
        return results
    results.append(str(value))
    return results



def _category_has_data(value: Any) -> bool:
    if value in (None, '', [], {}, False):
        return False
    if isinstance(value, list):
        return any(_category_has_data(v) for v in value)
    if isinstance(value, dict):
        return any(_category_has_data(v) for v in value.values())
    return True



def _tag_filters(record: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        for item in _collect_values(value):
            if item not in seen:
                seen.add(item)
                tags.append(item)

    general = record.get('general', {})
    add(general.get('geographical_locations'))
    add(general.get('threat_level'))
    add(general.get('charter_invoked'))

    for block in record.get('sanctions', []):
        add(block.get('items_regulated_inbound'))
        add(block.get('items_regulated_outbound'))
        add(block.get('items_regulated_domestic'))
        add(block.get('exceptions'))
        add(block.get('target_state'))
        add(block.get('reason'))
        add(block.get('sanctions_status'))
        add(block.get('sanctions_change'))

    for block in record.get('un_peace_operations', []):
        add(block.get('operation_type'))
        add(block.get('mission_name'))
        add(block.get('mission_activity'))
        add(block.get('mission_activation_termination'))
        add(block.get('change_in_authorized_strength'))
        add(block.get('collaboration'))
        add(block.get('mandate'))

    for block in record.get('non_un_operations_enforcement_actions', []):
        add(block.get('mission_name'))
        add(block.get('authorization_action'))
        add(block.get('authorization_activation_termination'))
        add(block.get('change_in_authorized_strength'))
        add(block.get('collaboration'))
        add(block.get('mandate'))

    add(record.get('criminal_tribunals', {}).get('tribunal_name'))
    add(record.get('other_subsidiary_organs', {}).get('subsidiary_organ_type'))
    add(record.get('membership', {}).get('new_member_name'))
    add(record.get('appointment_related', {}).get('organization'))
    return tags



def _categories_present(record: dict[str, Any]) -> list[str]:
    categories = [CATEGORY_LABELS['general']]
    for key in [
        'sanctions',
        'un_peace_operations',
        'non_un_operations_enforcement_actions',
        'criminal_tribunals',
        'other_subsidiary_organs',
        'thematic_resolutions',
        'membership',
        'appointment_related',
        'other',
    ]:
        if _category_has_data(record.get(key)):
            categories.append(CATEGORY_LABELS[key])
    return categories



def build_public_record(record: dict[str, Any]) -> dict[str, Any]:
    general = record.get('general', {})
    date_value = general.get('date') or ''
    try:
        year = int(str(date_value)[:4]) if date_value else None
    except ValueError:
        year = None
    return {
        'record_id': record.get('record_id'),
        'resolution_number': general.get('resolution_number'),
        'date': general.get('date'),
        'year': year,
        'resolution_title': general.get('resolution_title'),
        'un_document_url': general.get('un_document_url'),
        'geographical_locations': general.get('geographical_locations', []),
        'categories_present': _categories_present(record),
        'tag_filters': _tag_filters(record),
        'detail': record,
    }



def generate_public_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_public_record(record) for record in records]



def save_public_records(records: list[dict[str, Any]], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    public_records = generate_public_records(records)
    tmp.write_text(json.dumps(public_records, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)
