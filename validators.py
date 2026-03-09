"""Validation and normalization for internal records."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from form_spec import (
    TIME_PERIOD_MODE_MAP,
    TRANSFER_DIRECTION_MAP,
    default_record,
    default_sanction_block,
    default_un_peace_operation_block,
    default_non_un_operation_block,
)
from masters import (
    APPOINTMENT_ORGANIZATION_OPTIONS,
    AUTHORIZED_STRENGTH_CHANGE_OPTIONS,
    CHARTER_INVOKED_OPTIONS,
    COUNTRY_REGION_OPTIONS,
    DURATION_UNIT_OPTIONS,
    EXCEPTIONS_OPTIONS,
    INTER_MISSION_TRANSFER_DIRECTION_OPTIONS,
    ITEMS_REGULATED_DOMESTIC_OPTIONS,
    ITEMS_REGULATED_INBOUND_OPTIONS,
    ITEMS_REGULATED_OUTBOUND_OPTIONS,
    NON_UN_AUTH_ACTION_OPTIONS,
    NON_UN_AUTH_STATUS_OPTIONS,
    NON_UN_COLLABORATION_OPTIONS,
    NON_UN_MANDATE_OPTIONS,
    NON_UN_MISSION_NAME_OPTIONS,
    PKO_COLLABORATION_OPTIONS,
    PKO_MANDATE_OPTIONS,
    PKO_MISSION_ACTIVITY_OPTIONS,
    PKO_MISSION_NAME_OPTIONS,
    PKO_MISSION_STATUS_OPTIONS,
    PKO_OPERATION_TYPE_OPTIONS,
    SANCTIONS_CHANGE_OPTIONS,
    SANCTIONS_REASON_OPTIONS,
    SANCTIONS_STATUS_OPTIONS,
    SUBSIDIARY_ORGAN_TYPE_OPTIONS,
    THREAT_LEVEL_OPTIONS,
    TIME_PERIOD_MODE_OPTIONS,
    TRIBUNAL_NAME_OPTIONS,
)


class ValidationError(ValueError):
    pass


def _string(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()



def _optional_int(value: Any, *, field: str, errors: list[str], minimum: int = 0, maximum: int | None = None) -> int | None:
    raw = _string(value)
    if raw == '':
        return None
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        errors.append(f'{field}: must be an integer.')
        return None
    if parsed < minimum:
        errors.append(f'{field}: must be {minimum} or greater.')
        return None
    if maximum is not None and parsed > maximum:
        errors.append(f'{field}: must be {maximum} or less.')
        return None
    return parsed



def _date_to_iso(value: Any, *, field: str, errors: list[str], required: bool = False) -> str:
    raw = _string(value)
    if raw == '':
        if required:
            errors.append(f'{field}: required.')
        return ''
    for fmt in ('%Y-%m-%d', '%Y%m%d', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    errors.append(f'{field}: invalid date format. Use YYYYMMDD or YYYY-MM-DD e.g. 20170905')
    return ''



def _single_select(value: Any, options: list[str], *, field: str, errors: list[str]) -> str | None:
    if value in (None, ''):
        return None
    if value not in options:
        errors.append(f'{field}: value is not a valid option.')
        return None
    return value



def _multi_select(value: Any, options: list[str], *, field: str, errors: list[str]) -> list[str]:
    values = value or []
    if not isinstance(values, list):
        values = [values]
    cleaned = []
    seen = set()
    for item in values:
        if item in ('', None):
            continue
        if item not in options:
            errors.append(f'{field}: "{item}" is not a valid option.')
            continue
        if item not in seen:
            seen.add(item)
            cleaned.append(item)
    return cleaned



def _text_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        values = [values] if values not in (None, '') else []
    cleaned = []
    for value in values:
        raw = _string(value)
        if raw:
            cleaned.append(raw)
    return cleaned



def _int_list(values: Any, *, field: str, errors: list[str], maximum: int | None = None) -> list[int]:
    if not isinstance(values, list):
        values = [values] if values not in (None, '') else []
    cleaned: list[int] = []
    for i, value in enumerate(values, start=1):
        parsed = _optional_int(value, field=f'{field} #{i}', errors=errors, minimum=0, maximum=maximum)
        if parsed is not None:
            cleaned.append(parsed)
    return cleaned



def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raw = _string(value).lower()
    return raw in {'true', '1', 'yes', 'y', 'on'}



def _valid_url(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)



def _is_meaningful(value: Any) -> bool:
    if value in (None, '', [], {}):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, list):
        return any(_is_meaningful(v) for v in value)
    if isinstance(value, dict):
        return any(_is_meaningful(v) for v in value.values())
    return True



def _normalize_time_period(value: dict[str, Any], *, field: str, errors: list[str]) -> dict[str, Any]:
    mode_display = value.get('mode')
    mode = TIME_PERIOD_MODE_MAP.get(mode_display) if mode_display else None
    if mode_display not in (None, '') and mode_display not in TIME_PERIOD_MODE_OPTIONS:
        errors.append(f'{field}: mode is not a valid option.')
    duration_value = _optional_int(value.get('duration_value'), field=f'{field} duration_value', errors=errors, minimum=0)
    duration_unit = _single_select(value.get('duration_unit'), DURATION_UNIT_OPTIONS, field=f'{field} duration_unit', errors=errors)
    until_date = _date_to_iso(value.get('until_date'), field=f'{field} until_date', errors=errors, required=False)
    normalized = {
        'mode': mode,
        'duration_value': duration_value,
        'duration_unit': duration_unit,
        'until_date': until_date or None,
    }
    if mode is None:
        return normalized
    if mode.endswith('_for'):
        if duration_value is None:
            errors.append(f'{field}: duration value is required for "for" mode.')
        if duration_unit is None:
            errors.append(f'{field}: duration unit is required for "for" mode.')
        normalized['until_date'] = None
    elif mode.endswith('_until'):
        if not until_date:
            errors.append(f'{field}: date is required for "until" mode.')
        normalized['duration_value'] = None
        normalized['duration_unit'] = None
    return normalized



def _normalize_modified_resolution(value: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    enabled = _bool(value.get('enabled'))
    resolution_number = _optional_int(
        value.get('resolution_number'),
        field='Modified resolution number',
        errors=errors,
        minimum=0,
        maximum=9999,
    )
    if enabled and resolution_number is None:
        errors.append('Modified resolution: resolution number is required when enabled.')
    if not enabled:
        resolution_number = None
    return {'enabled': enabled, 'resolution_number': resolution_number}



def _normalize_transfer(value: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    direction_display = value.get('direction')
    if direction_display in (None, ''):
        direction = None
    elif direction_display in INTER_MISSION_TRANSFER_DIRECTION_OPTIONS:
        direction = TRANSFER_DIRECTION_MAP[direction_display]
    else:
        direction = None
        errors.append('Inter-mission loan/transfer: direction is not a valid option.')
    target = _string(value.get('target'))
    if direction and not target:
        errors.append('Inter-mission loan/transfer: target is required when direction is set.')
    if not direction:
        target = ''
    return {'direction': direction, 'target': target}



def _normalize_sanction_block(block: dict[str, Any], index: int, errors: list[str]) -> dict[str, Any]:
    normalized = default_sanction_block()
    normalized['modified_resolution'] = _normalize_modified_resolution(block.get('modified_resolution', {}), errors)
    normalized['items_regulated_inbound'] = _multi_select(block.get('items_regulated_inbound'), ITEMS_REGULATED_INBOUND_OPTIONS, field=f'Sanctions #{index} inbound', errors=errors)
    normalized['items_regulated_outbound'] = _multi_select(block.get('items_regulated_outbound'), ITEMS_REGULATED_OUTBOUND_OPTIONS, field=f'Sanctions #{index} outbound', errors=errors)
    normalized['items_regulated_domestic'] = _multi_select(block.get('items_regulated_domestic'), ITEMS_REGULATED_DOMESTIC_OPTIONS, field=f'Sanctions #{index} domestic', errors=errors)
    normalized['exceptions'] = _multi_select(block.get('exceptions'), EXCEPTIONS_OPTIONS, field=f'Sanctions #{index} exceptions', errors=errors)
    normalized['target_comprehensive'] = _bool(block.get('target_comprehensive'))
    normalized['target_region'] = _string(block.get('target_region'))
    normalized['target_state'] = _multi_select(block.get('target_state'), COUNTRY_REGION_OPTIONS, field=f'Sanctions #{index} target state', errors=errors)
    normalized['target_non_state'] = _string(block.get('target_non_state'))
    normalized['target_entities_business'] = _string(block.get('target_entities_business'))
    normalized['target_individual'] = _string(block.get('target_individual'))
    normalized['reason'] = _multi_select(block.get('reason'), SANCTIONS_REASON_OPTIONS, field=f'Sanctions #{index} reason', errors=errors)
    normalized['sanctions_status'] = _single_select(block.get('sanctions_status'), SANCTIONS_STATUS_OPTIONS, field=f'Sanctions #{index} status', errors=errors)
    normalized['sanctions_change'] = _single_select(block.get('sanctions_change'), SANCTIONS_CHANGE_OPTIONS, field=f'Sanctions #{index} change', errors=errors)
    normalized['sanctions_time_period'] = _normalize_time_period(block.get('sanctions_time_period', {}), field=f'Sanctions #{index} time period', errors=errors)
    return normalized



def _normalize_personnel_levels(value: dict[str, Any], field_prefix: str, errors: list[str]) -> dict[str, int | None]:
    return {
        'military': _optional_int(value.get('military'), field=f'{field_prefix} military', errors=errors, minimum=0),
        'police': _optional_int(value.get('police'), field=f'{field_prefix} police', errors=errors, minimum=0),
        'civilian': _optional_int(value.get('civilian'), field=f'{field_prefix} civilian', errors=errors, minimum=0),
        'other': _optional_int(value.get('other'), field=f'{field_prefix} other', errors=errors, minimum=0),
    }



def _normalize_un_peace_block(block: dict[str, Any], index: int, errors: list[str]) -> dict[str, Any]:
    normalized = default_un_peace_operation_block()
    normalized['operation_type'] = _single_select(block.get('operation_type'), PKO_OPERATION_TYPE_OPTIONS, field=f'UN peace #{index} operation_type', errors=errors)
    normalized['mission_name'] = _single_select(block.get('mission_name'), PKO_MISSION_NAME_OPTIONS, field=f'UN peace #{index} mission_name', errors=errors)
    normalized['mission_activity'] = _single_select(block.get('mission_activity'), PKO_MISSION_ACTIVITY_OPTIONS, field=f'UN peace #{index} mission_activity', errors=errors)
    normalized['authorization_time_period'] = _normalize_time_period(block.get('authorization_time_period', {}), field=f'UN peace #{index} authorization time period', errors=errors)
    normalized['mission_activation_termination'] = _single_select(block.get('mission_activation_termination'), PKO_MISSION_STATUS_OPTIONS, field=f'UN peace #{index} mission status', errors=errors)
    normalized['deployed_personnel_levels'] = _normalize_personnel_levels(block.get('deployed_personnel_levels', {}), f'UN peace #{index}', errors)
    normalized['description'] = _string(block.get('description'))
    normalized['change_in_authorized_strength'] = _single_select(block.get('change_in_authorized_strength'), AUTHORIZED_STRENGTH_CHANGE_OPTIONS, field=f'UN peace #{index} change', errors=errors)
    normalized['collaboration'] = _multi_select(block.get('collaboration'), PKO_COLLABORATION_OPTIONS, field=f'UN peace #{index} collaboration', errors=errors)
    normalized['inter_mission_loan_transfer'] = _normalize_transfer(block.get('inter_mission_loan_transfer', {}), errors)
    normalized['authorization_level_all_necessary_measures'] = _bool(block.get('authorization_level_all_necessary_measures'))
    normalized['mandate'] = _multi_select(block.get('mandate'), PKO_MANDATE_OPTIONS, field=f'UN peace #{index} mandate', errors=errors)
    return normalized



def _normalize_non_un_block(block: dict[str, Any], index: int, errors: list[str]) -> dict[str, Any]:
    normalized = default_non_un_operation_block()
    normalized['mission_name'] = _single_select(block.get('mission_name'), NON_UN_MISSION_NAME_OPTIONS, field=f'Non-UN #{index} mission_name', errors=errors)
    normalized['authorization_action'] = _single_select(block.get('authorization_action'), NON_UN_AUTH_ACTION_OPTIONS, field=f'Non-UN #{index} authorization action', errors=errors)
    normalized['authorization_time_period'] = _normalize_time_period(block.get('authorization_time_period', {}), field=f'Non-UN #{index} authorization time period', errors=errors)
    normalized['authorization_activation_termination'] = _single_select(block.get('authorization_activation_termination'), NON_UN_AUTH_STATUS_OPTIONS, field=f'Non-UN #{index} authorization status', errors=errors)
    normalized['deployed_personnel_levels'] = _normalize_personnel_levels(block.get('deployed_personnel_levels', {}), f'Non-UN #{index}', errors)
    normalized['description'] = _string(block.get('description'))
    normalized['change_in_authorized_strength'] = _single_select(block.get('change_in_authorized_strength'), AUTHORIZED_STRENGTH_CHANGE_OPTIONS, field=f'Non-UN #{index} change', errors=errors)
    normalized['collaboration'] = _multi_select(block.get('collaboration'), NON_UN_COLLABORATION_OPTIONS, field=f'Non-UN #{index} collaboration', errors=errors)
    normalized['authorization_level_all_necessary_measures'] = _bool(block.get('authorization_level_all_necessary_measures'))
    normalized['mandate'] = _multi_select(block.get('mandate'), NON_UN_MANDATE_OPTIONS, field=f'Non-UN #{index} mandate', errors=errors)
    return normalized



def normalize_record(record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    source = deepcopy(record)
    normalized = default_record()
    normalized['record_id'] = _string(source.get('record_id')) or normalized['record_id']

    general = source.get('general', {})
    normalized['general']['un_document_url'] = _string(general.get('un_document_url'))
    if not normalized['general']['un_document_url']:
        errors.append('UN document URL: required.')
    elif not _valid_url(normalized['general']['un_document_url']):
        errors.append('UN document URL: must be an http(s) URL.')
    normalized['general']['resolution_number'] = _optional_int(general.get('resolution_number'), field='Resolution number', errors=errors, minimum=0, maximum=9999)
    if normalized['general']['resolution_number'] is None:
        errors.append('Resolution number: required.')
    normalized['general']['date'] = _date_to_iso(general.get('date'), field='Date', errors=errors, required=True)
    normalized['general']['meeting_number'] = _optional_int(general.get('meeting_number'), field='Meeting number', errors=errors, minimum=0)
    normalized['general']['geographical_locations'] = _multi_select(general.get('geographical_locations'), COUNTRY_REGION_OPTIONS, field='Geographical location', errors=errors)
    normalized['general']['resolution_title'] = _string(general.get('resolution_title'))
    if not normalized['general']['resolution_title']:
        errors.append('Resolution title: required.')
    normalized['general']['references_resolutions'] = _int_list(general.get('references_resolutions'), field='References (resolutions)', errors=errors, maximum=9999)
    normalized['general']['references_prst'] = _text_list(general.get('references_prst'))
    normalized['general']['references_other'] = _text_list(general.get('references_other'))
    normalized['general']['threat_level'] = _single_select(general.get('threat_level'), THREAT_LEVEL_OPTIONS, field='Threat level', errors=errors)
    normalized['general']['charter_invoked'] = _multi_select(general.get('charter_invoked'), CHARTER_INVOKED_OPTIONS, field='Charter invoked', errors=errors)
    normalized['general']['referrals'] = _string(general.get('referrals'))

    sanctions = []
    for i, block in enumerate(source.get('sanctions', []), start=1):
        item = _normalize_sanction_block(block, i, errors)
        if _is_meaningful(item):
            sanctions.append(item)
    normalized['sanctions'] = sanctions

    un_peace = []
    for i, block in enumerate(source.get('un_peace_operations', []), start=1):
        item = _normalize_un_peace_block(block, i, errors)
        if _is_meaningful(item):
            un_peace.append(item)
    normalized['un_peace_operations'] = un_peace

    non_un = []
    for i, block in enumerate(source.get('non_un_operations_enforcement_actions', []), start=1):
        item = _normalize_non_un_block(block, i, errors)
        if _is_meaningful(item):
            non_un.append(item)
    normalized['non_un_operations_enforcement_actions'] = non_un

    criminal = source.get('criminal_tribunals', {})
    normalized['criminal_tribunals']['tribunal_name'] = _multi_select(criminal.get('tribunal_name'), TRIBUNAL_NAME_OPTIONS, field='Tribunal name', errors=errors)
    subsidiary = source.get('other_subsidiary_organs', {})
    normalized['other_subsidiary_organs']['subsidiary_organ_type'] = _multi_select(subsidiary.get('subsidiary_organ_type'), SUBSIDIARY_ORGAN_TYPE_OPTIONS, field='Subsidiary organ type', errors=errors)
    thematic = source.get('thematic_resolutions', {})
    normalized['thematic_resolutions']['theme'] = _string(thematic.get('theme'))
    membership = source.get('membership', {})
    normalized['membership']['new_member_name'] = _multi_select(membership.get('new_member_name'), COUNTRY_REGION_OPTIONS, field='New member name', errors=errors)
    normalized['membership']['other_membership_issue'] = _string(membership.get('other_membership_issue'))
    appointment = source.get('appointment_related', {})
    normalized['appointment_related']['organization'] = _multi_select(appointment.get('organization'), APPOINTMENT_ORGANIZATION_OPTIONS, field='Organization', errors=errors)
    other = source.get('other', {})
    normalized['other']['note'] = _string(other.get('note'))
    normalized['other']['annex_attached'] = _bool(other.get('annex_attached'))

    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    normalized['created_at'] = source.get('created_at') or now
    normalized['updated_at'] = now

    return normalized, errors
