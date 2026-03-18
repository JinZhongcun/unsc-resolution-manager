from __future__ import annotations

from copy import deepcopy
from typing import Any
import sys

import streamlit as st

from export_public import generate_public_records, save_public_records
from custom_fields import CUSTOM_KEY, empty_custom_payload, ensure_custom_defaults
from form_spec import (
    CATEGORY_ORDER,
    TIME_PERIOD_MODE_MAP_REVERSE,
    TRANSFER_DIRECTION_MAP_REVERSE,
    clone_record,
    default_non_un_operation_block,
    default_record,
    default_sanction_block,
    default_un_peace_operation_block,
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
from storage import PUBLIC_RECORDS_PATH, RECORDS_PATH, SCHEMA_OVERRIDES_PATH, ensure_data_files, load_records, save_records, upsert_record
from validators import normalize_record
from schema_overrides import default_value_for_field, get_category_fields, load_schema_overrides


st.set_page_config(page_title='UNSC Metadata Backend', layout='wide')

if sys.version_info < (3, 11):
    st.error('Python 3.11 以上で実行してください。')
    st.stop()

EDITOR_PREFIX = 'editor_'


def clear_editor_widget_state() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith(EDITOR_PREFIX):
            del st.session_state[key]



def get_runtime_schema() -> dict[str, Any]:
    return st.session_state.get('_runtime_custom_schema', {'categories': {}})


def load_record_into_editor(record: dict[str, Any]) -> None:
    st.session_state.current_record = ensure_custom_defaults(clone_record(record), get_runtime_schema())
    clear_editor_widget_state()



def init_if_missing(key: str, default: Any) -> None:
    if key not in st.session_state:
        st.session_state[key] = default



def display_text(value: Any) -> str:
    if value is None:
        return ''
    return str(value)



def display_mode(value: Any) -> Any:
    if value in (None, ''):
        return None
    return TIME_PERIOD_MODE_MAP_REVERSE.get(value, value)



def display_direction(value: Any) -> Any:
    if value in (None, ''):
        return None
    return TRANSFER_DIRECTION_MAP_REVERSE.get(value, value)



def render_text(label: str, key: str, default: Any = '', help_text: str | None = None) -> None:
    init_if_missing(key, display_text(default))
    st.text_input(label, key=key, help=help_text)



def render_text_area(label: str, key: str, default: Any = '', help_text: str | None = None) -> None:
    init_if_missing(key, display_text(default))
    st.text_area(label, key=key, help=help_text, height=100)



def render_select(label: str, key: str, options: list[str], default: Any = None, help_text: str | None = None) -> None:
    values = [None] + list(options)
    init_if_missing(key, default if default in values else None)
    st.selectbox(label, values, key=key, format_func=lambda x: '—' if x in (None, '') else x, help=help_text)



def render_multiselect(label: str, key: str, options: list[str], default: list[str] | None = None, help_text: str | None = None) -> None:
    init_if_missing(key, list(default or []))
    st.multiselect(label, options, key=key, help=help_text)



def render_checkbox(label: str, key: str, default: bool = False, help_text: str | None = None) -> None:
    init_if_missing(key, bool(default))
    st.checkbox(label, key=key, help=help_text)


def custom_state_key(prefix: str, field_key: str) -> str:
    return f'{prefix}_custom_{field_key}'


def render_custom_fields(category: str, target: dict[str, Any], key_prefix: str) -> None:
    fields = get_category_fields(get_runtime_schema(), category)
    if not fields:
        return
    custom = target.get(CUSTOM_KEY, {}) if isinstance(target, dict) else {}
    st.markdown('**追加項目**')
    for field in fields:
        field_key = field['key']
        state_key = custom_state_key(key_prefix, field_key)
        default = custom.get(field_key, default_value_for_field(field))
        help_text = field.get('help') or None
        if field['type'] == 'textarea':
            render_text_area(field['label'], state_key, default, help_text)
        elif field['type'] in {'text', 'int', 'date'}:
            render_text(field['label'], state_key, default, help_text)
        elif field['type'] == 'bool':
            render_checkbox(field['label'], state_key, bool(default), help_text)
        elif field['type'] == 'select':
            render_select(field['label'], state_key, field.get('options', []), default, help_text)
        elif field['type'] == 'multiselect':
            render_multiselect(field['label'], state_key, field.get('options', []), default or [], help_text)


def materialize_custom_fields(category: str, key_prefix: str, seed_custom: dict[str, Any] | None = None) -> dict[str, Any]:
    seed_custom = seed_custom or {}
    fields = get_category_fields(get_runtime_schema(), category)
    result: dict[str, Any] = {}
    for field in fields:
        field_key = field['key']
        state_key = custom_state_key(key_prefix, field_key)
        if field['type'] == 'multiselect':
            result[field_key] = st.session_state.get(state_key, list(seed_custom.get(field_key, [])))
        elif field['type'] == 'bool':
            result[field_key] = st.session_state.get(state_key, bool(seed_custom.get(field_key, False)))
        elif field['type'] == 'select':
            result[field_key] = st.session_state.get(state_key, seed_custom.get(field_key))
        else:
            result[field_key] = st.session_state.get(state_key, display_text(seed_custom.get(field_key, '')))
    return result



def record_label(public_record: dict[str, Any]) -> str:
    resolution = public_record.get('resolution_number') or '未設定'
    date_value = public_record.get('date') or '日付未設定'
    title = public_record.get('resolution_title') or 'タイトル未設定'
    suffix = str(public_record.get('record_id', ''))[:8]
    return f'{resolution} | {date_value} | {title} | {suffix}'



def render_dynamic_string_list(title: str, list_key: str, values: list[Any]) -> None:
    st.markdown(f'**{title}**')
    if not values:
        st.caption('項目なし')
    for idx, value in enumerate(values):
        cols = st.columns([5, 1])
        with cols[0]:
            render_text(f'{title} #{idx + 1}', f'{list_key}_{idx}', value)
        with cols[1]:
            if st.button('削除', key=f'remove_{list_key}_{idx}'):
                current = materialize_current_record()
                target = current['general'][list_key]
                if idx < len(target):
                    target.pop(idx)
                st.session_state.current_record = current
                clear_editor_widget_state()
                st.rerun()
    if st.button(f'{title} を追加', key=f'add_{list_key}'):
        current = materialize_current_record()
        current['general'][list_key].append('')
        st.session_state.current_record = current
        clear_editor_widget_state()
        st.rerun()



def render_general_section(record: dict[str, Any]) -> None:
    general = record['general']
    st.subheader('General')
    render_text('UN document URL', 'editor_general_un_document_url', general.get('un_document_url'), '検索結果から遷移する国連ページのURL')
    cols = st.columns(3)
    with cols[0]:
        render_text('Resolution number', 'editor_general_resolution_number', general.get('resolution_number'))
    with cols[1]:
        render_text('Date', 'editor_general_date', general.get('date'), 'YYYY-MM-DD または DD/MM/YYYY')
    with cols[2]:
        render_text('Meeting number', 'editor_general_meeting_number', general.get('meeting_number'))
    render_multiselect('Geographical location', 'editor_general_geographical_locations', COUNTRY_REGION_OPTIONS, general.get('geographical_locations', []))
    render_text('Resolution title', 'editor_general_resolution_title', general.get('resolution_title'))
    render_dynamic_string_list('References (resolutions)', 'references_resolutions', general.get('references_resolutions', []))
    render_dynamic_string_list('References (PRST)', 'references_prst', general.get('references_prst', []))
    render_dynamic_string_list('References (other)', 'references_other', general.get('references_other', []))
    cols = st.columns(2)
    with cols[0]:
        render_select('Threat level', 'editor_general_threat_level', THREAT_LEVEL_OPTIONS, general.get('threat_level'))
    with cols[1]:
        render_multiselect('Charter invoked', 'editor_general_charter_invoked', CHARTER_INVOKED_OPTIONS, general.get('charter_invoked', []))
    render_text('Referrals', 'editor_general_referrals', general.get('referrals'))
    render_custom_fields('general', general, 'editor_general')



def render_time_period(prefix: str, title: str, current: dict[str, Any]) -> None:
    st.markdown(f'**{title}**')
    render_select('Mode', f'{prefix}_mode', TIME_PERIOD_MODE_OPTIONS, display_mode(current.get('mode')))
    mode = st.session_state.get(f'{prefix}_mode')
    if mode in {'Established for', 'Extended for'}:
        cols = st.columns(2)
        with cols[0]:
            render_text('Duration value', f'{prefix}_duration_value', current.get('duration_value'))
        with cols[1]:
            render_select('Duration unit', f'{prefix}_duration_unit', DURATION_UNIT_OPTIONS, current.get('duration_unit'))
    elif mode in {'Established until', 'Extended until'}:
        render_text('Until date', f'{prefix}_until_date', current.get('until_date'), 'YYYY-MM-DD または DD/MM/YYYY')



def render_sanctions(record: dict[str, Any]) -> None:
    st.subheader('Sanctions')
    if not record['sanctions']:
        st.caption('ブロックなし')
    for idx, block in enumerate(record['sanctions']):
        with st.expander(f'Sanctions #{idx + 1}', expanded=True):
            render_checkbox('Modified resolution', f'editor_sanctions_{idx}_modified_enabled', block.get('modified_resolution', {}).get('enabled', False))
            if st.session_state.get(f'editor_sanctions_{idx}_modified_enabled'):
                render_text('Modified resolution number', f'editor_sanctions_{idx}_modified_resolution_number', block.get('modified_resolution', {}).get('resolution_number'))
            render_multiselect('Items regulated (inbound)', f'editor_sanctions_{idx}_items_regulated_inbound', ITEMS_REGULATED_INBOUND_OPTIONS, block.get('items_regulated_inbound', []))
            render_multiselect('Items regulated (outbound)', f'editor_sanctions_{idx}_items_regulated_outbound', ITEMS_REGULATED_OUTBOUND_OPTIONS, block.get('items_regulated_outbound', []))
            render_multiselect('Items regulated (domestic)', f'editor_sanctions_{idx}_items_regulated_domestic', ITEMS_REGULATED_DOMESTIC_OPTIONS, block.get('items_regulated_domestic', []))
            render_multiselect('Exceptions', f'editor_sanctions_{idx}_exceptions', EXCEPTIONS_OPTIONS, block.get('exceptions', []))
            render_checkbox('Target: Comprehensive', f'editor_sanctions_{idx}_target_comprehensive', block.get('target_comprehensive', False))
            render_text('Target: Region', f'editor_sanctions_{idx}_target_region', block.get('target_region'))
            render_multiselect('Target: State', f'editor_sanctions_{idx}_target_state', COUNTRY_REGION_OPTIONS, block.get('target_state', []))
            render_text('Target: Non-state', f'editor_sanctions_{idx}_target_non_state', block.get('target_non_state'))
            render_text('Target: Entities (business)', f'editor_sanctions_{idx}_target_entities_business', block.get('target_entities_business'))
            render_text('Target: Individual', f'editor_sanctions_{idx}_target_individual', block.get('target_individual'))
            render_multiselect('Reason', f'editor_sanctions_{idx}_reason', SANCTIONS_REASON_OPTIONS, block.get('reason', []))
            cols = st.columns(2)
            with cols[0]:
                render_select('Sanctions activation/termination/suspension', f'editor_sanctions_{idx}_sanctions_status', SANCTIONS_STATUS_OPTIONS, block.get('sanctions_status'))
            with cols[1]:
                render_select('Sanctions change', f'editor_sanctions_{idx}_sanctions_change', SANCTIONS_CHANGE_OPTIONS, block.get('sanctions_change'))
            render_time_period(f'editor_sanctions_{idx}_time_period', 'Sanctions (time period)', block.get('sanctions_time_period', {}))
            render_custom_fields('sanctions', block, f'editor_sanctions_{idx}')
            if st.button('この Sanctions ブロックを削除', key=f'remove_sanctions_block_{idx}'):
                current = materialize_current_record()
                current['sanctions'].pop(idx)
                st.session_state.current_record = current
                clear_editor_widget_state()
                st.rerun()
    if st.button('Sanctions ブロックを追加', key='add_sanctions_block'):
        current = materialize_current_record()
        current['sanctions'].append(default_sanction_block())
        st.session_state.current_record = ensure_custom_defaults(current, get_runtime_schema())
        clear_editor_widget_state()
        st.rerun()



def render_un_peace_operations(record: dict[str, Any]) -> None:
    st.subheader('UN peace operations')
    if not record['un_peace_operations']:
        st.caption('ブロックなし')
    for idx, block in enumerate(record['un_peace_operations']):
        with st.expander(f'UN peace operation #{idx + 1}', expanded=True):
            render_select('Operation type', f'editor_un_peace_{idx}_operation_type', PKO_OPERATION_TYPE_OPTIONS, block.get('operation_type'))
            render_select('Mission name', f'editor_un_peace_{idx}_mission_name', PKO_MISSION_NAME_OPTIONS, block.get('mission_name'))
            render_select('Mission activity', f'editor_un_peace_{idx}_mission_activity', PKO_MISSION_ACTIVITY_OPTIONS, block.get('mission_activity'))
            render_time_period(f'editor_un_peace_{idx}_authorization_time_period', 'Authorization (time period)', block.get('authorization_time_period', {}))
            render_select('Mission activation/termination', f'editor_un_peace_{idx}_mission_activation_termination', PKO_MISSION_STATUS_OPTIONS, block.get('mission_activation_termination'))
            st.markdown('**Deployed personnel levels**')
            cols = st.columns(4)
            with cols[0]:
                render_text('Military', f'editor_un_peace_{idx}_military', block.get('deployed_personnel_levels', {}).get('military'))
            with cols[1]:
                render_text('Police', f'editor_un_peace_{idx}_police', block.get('deployed_personnel_levels', {}).get('police'))
            with cols[2]:
                render_text('Civilian', f'editor_un_peace_{idx}_civilian', block.get('deployed_personnel_levels', {}).get('civilian'))
            with cols[3]:
                render_text('Other', f'editor_un_peace_{idx}_other', block.get('deployed_personnel_levels', {}).get('other'))
            render_text('Description', f'editor_un_peace_{idx}_description', block.get('description'))
            render_select('Change in authorized strength', f'editor_un_peace_{idx}_change_in_authorized_strength', AUTHORIZED_STRENGTH_CHANGE_OPTIONS, block.get('change_in_authorized_strength'))
            render_multiselect('Collaboration', f'editor_un_peace_{idx}_collaboration', PKO_COLLABORATION_OPTIONS, block.get('collaboration', []))
            render_select('Inter-mission loan/transfer', f'editor_un_peace_{idx}_transfer_direction', INTER_MISSION_TRANSFER_DIRECTION_OPTIONS, display_direction(block.get('inter_mission_loan_transfer', {}).get('direction')))
            if st.session_state.get(f'editor_un_peace_{idx}_transfer_direction'):
                render_text('Transfer target', f'editor_un_peace_{idx}_transfer_target', block.get('inter_mission_loan_transfer', {}).get('target'))
            render_checkbox('Authorization level (all necessary measures)', f'editor_un_peace_{idx}_authorization_level', block.get('authorization_level_all_necessary_measures', False))
            render_multiselect('Mandate', f'editor_un_peace_{idx}_mandate', PKO_MANDATE_OPTIONS, block.get('mandate', []))
            render_custom_fields('un_peace_operations', block, f'editor_un_peace_{idx}')
            if st.button('この UN peace operations ブロックを削除', key=f'remove_un_peace_block_{idx}'):
                current = materialize_current_record()
                current['un_peace_operations'].pop(idx)
                st.session_state.current_record = current
                clear_editor_widget_state()
                st.rerun()
    if st.button('UN peace operations ブロックを追加', key='add_un_peace_block'):
        current = materialize_current_record()
        current['un_peace_operations'].append(default_un_peace_operation_block())
        st.session_state.current_record = ensure_custom_defaults(current, get_runtime_schema())
        clear_editor_widget_state()
        st.rerun()



def render_non_un_operations(record: dict[str, Any]) -> None:
    st.subheader('Non-UN operations/enforcement actions')
    if not record['non_un_operations_enforcement_actions']:
        st.caption('ブロックなし')
    for idx, block in enumerate(record['non_un_operations_enforcement_actions']):
        with st.expander(f'Non-UN operation #{idx + 1}', expanded=True):
            render_select('Mission name', f'editor_non_un_{idx}_mission_name', NON_UN_MISSION_NAME_OPTIONS, block.get('mission_name'))
            render_select('Authorization action', f'editor_non_un_{idx}_authorization_action', NON_UN_AUTH_ACTION_OPTIONS, block.get('authorization_action'))
            render_time_period(f'editor_non_un_{idx}_authorization_time_period', 'Authorization (time period)', block.get('authorization_time_period', {}))
            render_select('Authorization activation/termination', f'editor_non_un_{idx}_authorization_activation_termination', NON_UN_AUTH_STATUS_OPTIONS, block.get('authorization_activation_termination'))
            st.markdown('**Deployed personnel levels**')
            cols = st.columns(4)
            with cols[0]:
                render_text('Military', f'editor_non_un_{idx}_military', block.get('deployed_personnel_levels', {}).get('military'))
            with cols[1]:
                render_text('Police', f'editor_non_un_{idx}_police', block.get('deployed_personnel_levels', {}).get('police'))
            with cols[2]:
                render_text('Civilian', f'editor_non_un_{idx}_civilian', block.get('deployed_personnel_levels', {}).get('civilian'))
            with cols[3]:
                render_text('Other', f'editor_non_un_{idx}_other', block.get('deployed_personnel_levels', {}).get('other'))
            render_text('Description', f'editor_non_un_{idx}_description', block.get('description'))
            render_select('Change in authorized strength', f'editor_non_un_{idx}_change_in_authorized_strength', AUTHORIZED_STRENGTH_CHANGE_OPTIONS, block.get('change_in_authorized_strength'))
            render_multiselect('Collaboration', f'editor_non_un_{idx}_collaboration', NON_UN_COLLABORATION_OPTIONS, block.get('collaboration', []))
            render_checkbox('Authorization level (all necessary measures)', f'editor_non_un_{idx}_authorization_level', block.get('authorization_level_all_necessary_measures', False))
            render_multiselect('Mandate', f'editor_non_un_{idx}_mandate', NON_UN_MANDATE_OPTIONS, block.get('mandate', []))
            render_custom_fields('non_un_operations_enforcement_actions', block, f'editor_non_un_{idx}')
            if st.button('この Non-UN operations ブロックを削除', key=f'remove_non_un_block_{idx}'):
                current = materialize_current_record()
                current['non_un_operations_enforcement_actions'].pop(idx)
                st.session_state.current_record = current
                clear_editor_widget_state()
                st.rerun()
    if st.button('Non-UN operations ブロックを追加', key='add_non_un_block'):
        current = materialize_current_record()
        current['non_un_operations_enforcement_actions'].append(default_non_un_operation_block())
        st.session_state.current_record = ensure_custom_defaults(current, get_runtime_schema())
        clear_editor_widget_state()
        st.rerun()



def render_single_sections(record: dict[str, Any]) -> None:
    st.subheader('Criminal Tribunals')
    render_multiselect('Tribunal name', 'editor_criminal_tribunals_tribunal_name', TRIBUNAL_NAME_OPTIONS, record.get('criminal_tribunals', {}).get('tribunal_name', []))
    render_custom_fields('criminal_tribunals', record.get('criminal_tribunals', {}), 'editor_criminal_tribunals')

    st.subheader('Other subsidiary organs')
    render_multiselect('Subsidiary organ type', 'editor_other_subsidiary_organs_subsidiary_organ_type', SUBSIDIARY_ORGAN_TYPE_OPTIONS, record.get('other_subsidiary_organs', {}).get('subsidiary_organ_type', []))
    render_custom_fields('other_subsidiary_organs', record.get('other_subsidiary_organs', {}), 'editor_other_subsidiary_organs')

    st.subheader('Thematic resolutions')
    render_text('Theme', 'editor_thematic_resolutions_theme', record.get('thematic_resolutions', {}).get('theme', ''))
    render_custom_fields('thematic_resolutions', record.get('thematic_resolutions', {}), 'editor_thematic_resolutions')

    st.subheader('Membership')
    render_multiselect('New member name', 'editor_membership_new_member_name', COUNTRY_REGION_OPTIONS, record.get('membership', {}).get('new_member_name', []))
    render_text('Other membership issue', 'editor_membership_other_membership_issue', record.get('membership', {}).get('other_membership_issue', ''))
    render_custom_fields('membership', record.get('membership', {}), 'editor_membership')

    st.subheader('Appointment related')
    render_multiselect('Organization', 'editor_appointment_related_organization', APPOINTMENT_ORGANIZATION_OPTIONS, record.get('appointment_related', {}).get('organization', []))
    render_custom_fields('appointment_related', record.get('appointment_related', {}), 'editor_appointment_related')

    st.subheader('Other')
    render_text_area('Note', 'editor_other_note', record.get('other', {}).get('note', ''))
    render_checkbox('Annex attached', 'editor_other_annex_attached', record.get('other', {}).get('annex_attached', False))
    render_custom_fields('other', record.get('other', {}), 'editor_other')



def materialize_current_record() -> dict[str, Any]:
    seed = st.session_state.current_record
    record = default_record()
    record['record_id'] = seed.get('record_id') or record['record_id']

    record['general']['un_document_url'] = st.session_state.get('editor_general_un_document_url', '')
    record['general']['resolution_number'] = st.session_state.get('editor_general_resolution_number', '')
    record['general']['date'] = st.session_state.get('editor_general_date', '')
    record['general']['meeting_number'] = st.session_state.get('editor_general_meeting_number', '')
    record['general']['geographical_locations'] = st.session_state.get('editor_general_geographical_locations', [])
    record['general']['resolution_title'] = st.session_state.get('editor_general_resolution_title', '')
    record['general']['references_resolutions'] = [st.session_state.get(f'references_resolutions_{i}', '') for i in range(len(seed['general']['references_resolutions']))]
    record['general']['references_prst'] = [st.session_state.get(f'references_prst_{i}', '') for i in range(len(seed['general']['references_prst']))]
    record['general']['references_other'] = [st.session_state.get(f'references_other_{i}', '') for i in range(len(seed['general']['references_other']))]
    record['general']['threat_level'] = st.session_state.get('editor_general_threat_level')
    record['general']['charter_invoked'] = st.session_state.get('editor_general_charter_invoked', [])
    record['general']['referrals'] = st.session_state.get('editor_general_referrals', '')
    record['general'][CUSTOM_KEY] = materialize_custom_fields('general', 'editor_general', seed['general'].get(CUSTOM_KEY, {}))

    record['sanctions'] = []
    for idx in range(len(seed['sanctions'])):
        block = default_sanction_block()
        block['modified_resolution']['enabled'] = st.session_state.get(f'editor_sanctions_{idx}_modified_enabled', False)
        block['modified_resolution']['resolution_number'] = st.session_state.get(f'editor_sanctions_{idx}_modified_resolution_number', '')
        block['items_regulated_inbound'] = st.session_state.get(f'editor_sanctions_{idx}_items_regulated_inbound', [])
        block['items_regulated_outbound'] = st.session_state.get(f'editor_sanctions_{idx}_items_regulated_outbound', [])
        block['items_regulated_domestic'] = st.session_state.get(f'editor_sanctions_{idx}_items_regulated_domestic', [])
        block['exceptions'] = st.session_state.get(f'editor_sanctions_{idx}_exceptions', [])
        block['target_comprehensive'] = st.session_state.get(f'editor_sanctions_{idx}_target_comprehensive', False)
        block['target_region'] = st.session_state.get(f'editor_sanctions_{idx}_target_region', '')
        block['target_state'] = st.session_state.get(f'editor_sanctions_{idx}_target_state', [])
        block['target_non_state'] = st.session_state.get(f'editor_sanctions_{idx}_target_non_state', '')
        block['target_entities_business'] = st.session_state.get(f'editor_sanctions_{idx}_target_entities_business', '')
        block['target_individual'] = st.session_state.get(f'editor_sanctions_{idx}_target_individual', '')
        block['reason'] = st.session_state.get(f'editor_sanctions_{idx}_reason', [])
        block['sanctions_status'] = st.session_state.get(f'editor_sanctions_{idx}_sanctions_status')
        block['sanctions_change'] = st.session_state.get(f'editor_sanctions_{idx}_sanctions_change')
        block['sanctions_time_period'] = {
            'mode': st.session_state.get(f'editor_sanctions_{idx}_time_period_mode'),
            'duration_value': st.session_state.get(f'editor_sanctions_{idx}_time_period_duration_value', ''),
            'duration_unit': st.session_state.get(f'editor_sanctions_{idx}_time_period_duration_unit'),
            'until_date': st.session_state.get(f'editor_sanctions_{idx}_time_period_until_date', ''),
        }
        block[CUSTOM_KEY] = materialize_custom_fields('sanctions', f'editor_sanctions_{idx}', seed['sanctions'][idx].get(CUSTOM_KEY, {}))
        record['sanctions'].append(block)

    record['un_peace_operations'] = []
    for idx in range(len(seed['un_peace_operations'])):
        block = default_un_peace_operation_block()
        block['operation_type'] = st.session_state.get(f'editor_un_peace_{idx}_operation_type')
        block['mission_name'] = st.session_state.get(f'editor_un_peace_{idx}_mission_name')
        block['mission_activity'] = st.session_state.get(f'editor_un_peace_{idx}_mission_activity')
        block['authorization_time_period'] = {
            'mode': st.session_state.get(f'editor_un_peace_{idx}_authorization_time_period_mode'),
            'duration_value': st.session_state.get(f'editor_un_peace_{idx}_authorization_time_period_duration_value', ''),
            'duration_unit': st.session_state.get(f'editor_un_peace_{idx}_authorization_time_period_duration_unit'),
            'until_date': st.session_state.get(f'editor_un_peace_{idx}_authorization_time_period_until_date', ''),
        }
        block['mission_activation_termination'] = st.session_state.get(f'editor_un_peace_{idx}_mission_activation_termination')
        block['deployed_personnel_levels'] = {
            'military': st.session_state.get(f'editor_un_peace_{idx}_military', ''),
            'police': st.session_state.get(f'editor_un_peace_{idx}_police', ''),
            'civilian': st.session_state.get(f'editor_un_peace_{idx}_civilian', ''),
            'other': st.session_state.get(f'editor_un_peace_{idx}_other', ''),
        }
        block['description'] = st.session_state.get(f'editor_un_peace_{idx}_description', '')
        block['change_in_authorized_strength'] = st.session_state.get(f'editor_un_peace_{idx}_change_in_authorized_strength')
        block['collaboration'] = st.session_state.get(f'editor_un_peace_{idx}_collaboration', [])
        block['inter_mission_loan_transfer'] = {
            'direction': st.session_state.get(f'editor_un_peace_{idx}_transfer_direction'),
            'target': st.session_state.get(f'editor_un_peace_{idx}_transfer_target', ''),
        }
        block['authorization_level_all_necessary_measures'] = st.session_state.get(f'editor_un_peace_{idx}_authorization_level', False)
        block['mandate'] = st.session_state.get(f'editor_un_peace_{idx}_mandate', [])
        block[CUSTOM_KEY] = materialize_custom_fields('un_peace_operations', f'editor_un_peace_{idx}', seed['un_peace_operations'][idx].get(CUSTOM_KEY, {}))
        record['un_peace_operations'].append(block)

    record['non_un_operations_enforcement_actions'] = []
    for idx in range(len(seed['non_un_operations_enforcement_actions'])):
        block = default_non_un_operation_block()
        block['mission_name'] = st.session_state.get(f'editor_non_un_{idx}_mission_name')
        block['authorization_action'] = st.session_state.get(f'editor_non_un_{idx}_authorization_action')
        block['authorization_time_period'] = {
            'mode': st.session_state.get(f'editor_non_un_{idx}_authorization_time_period_mode'),
            'duration_value': st.session_state.get(f'editor_non_un_{idx}_authorization_time_period_duration_value', ''),
            'duration_unit': st.session_state.get(f'editor_non_un_{idx}_authorization_time_period_duration_unit'),
            'until_date': st.session_state.get(f'editor_non_un_{idx}_authorization_time_period_until_date', ''),
        }
        block['authorization_activation_termination'] = st.session_state.get(f'editor_non_un_{idx}_authorization_activation_termination')
        block['deployed_personnel_levels'] = {
            'military': st.session_state.get(f'editor_non_un_{idx}_military', ''),
            'police': st.session_state.get(f'editor_non_un_{idx}_police', ''),
            'civilian': st.session_state.get(f'editor_non_un_{idx}_civilian', ''),
            'other': st.session_state.get(f'editor_non_un_{idx}_other', ''),
        }
        block['description'] = st.session_state.get(f'editor_non_un_{idx}_description', '')
        block['change_in_authorized_strength'] = st.session_state.get(f'editor_non_un_{idx}_change_in_authorized_strength')
        block['collaboration'] = st.session_state.get(f'editor_non_un_{idx}_collaboration', [])
        block['authorization_level_all_necessary_measures'] = st.session_state.get(f'editor_non_un_{idx}_authorization_level', False)
        block['mandate'] = st.session_state.get(f'editor_non_un_{idx}_mandate', [])
        block[CUSTOM_KEY] = materialize_custom_fields('non_un_operations_enforcement_actions', f'editor_non_un_{idx}', seed['non_un_operations_enforcement_actions'][idx].get(CUSTOM_KEY, {}))
        record['non_un_operations_enforcement_actions'].append(block)

    record['criminal_tribunals']['tribunal_name'] = st.session_state.get('editor_criminal_tribunals_tribunal_name', [])
    record['criminal_tribunals'][CUSTOM_KEY] = materialize_custom_fields('criminal_tribunals', 'editor_criminal_tribunals', seed['criminal_tribunals'].get(CUSTOM_KEY, {}))
    record['other_subsidiary_organs']['subsidiary_organ_type'] = st.session_state.get('editor_other_subsidiary_organs_subsidiary_organ_type', [])
    record['other_subsidiary_organs'][CUSTOM_KEY] = materialize_custom_fields('other_subsidiary_organs', 'editor_other_subsidiary_organs', seed['other_subsidiary_organs'].get(CUSTOM_KEY, {}))
    record['thematic_resolutions']['theme'] = st.session_state.get('editor_thematic_resolutions_theme', '')
    record['thematic_resolutions'][CUSTOM_KEY] = materialize_custom_fields('thematic_resolutions', 'editor_thematic_resolutions', seed['thematic_resolutions'].get(CUSTOM_KEY, {}))
    record['membership']['new_member_name'] = st.session_state.get('editor_membership_new_member_name', [])
    record['membership']['other_membership_issue'] = st.session_state.get('editor_membership_other_membership_issue', '')
    record['membership'][CUSTOM_KEY] = materialize_custom_fields('membership', 'editor_membership', seed['membership'].get(CUSTOM_KEY, {}))
    record['appointment_related']['organization'] = st.session_state.get('editor_appointment_related_organization', [])
    record['appointment_related'][CUSTOM_KEY] = materialize_custom_fields('appointment_related', 'editor_appointment_related', seed['appointment_related'].get(CUSTOM_KEY, {}))
    record['other']['note'] = st.session_state.get('editor_other_note', '')
    record['other']['annex_attached'] = st.session_state.get('editor_other_annex_attached', False)
    record['other'][CUSTOM_KEY] = materialize_custom_fields('other', 'editor_other', seed['other'].get(CUSTOM_KEY, {}))
    return record



def run_filters(public_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    resolution_filter = st.sidebar.text_input('Resolution number filter', key='filter_resolution')
    years = sorted({rec['year'] for rec in public_records if rec.get('year') is not None})
    year_filter = st.sidebar.multiselect('Year', years, key='filter_year')
    geo_options = sorted({geo for rec in public_records for geo in rec.get('geographical_locations', [])})
    geo_filter = st.sidebar.multiselect('Geographical location', geo_options, key='filter_geo')
    category_options = sorted({cat for rec in public_records for cat in rec.get('categories_present', [])})
    category_filter = st.sidebar.multiselect('Category', category_options, key='filter_category')
    tag_options = sorted({tag for rec in public_records for tag in rec.get('tag_filters', [])})
    tag_filter = st.sidebar.multiselect('Tag', tag_options, key='filter_tag')

    results = []
    for rec in public_records:
        if resolution_filter:
            if str(rec.get('resolution_number', '')) != resolution_filter.strip():
                continue
        if year_filter and rec.get('year') not in year_filter:
            continue
        if geo_filter and not set(geo_filter).issubset(set(rec.get('geographical_locations', []))):
            continue
        if category_filter and not set(category_filter).issubset(set(rec.get('categories_present', []))):
            continue
        if tag_filter and not set(tag_filter).issubset(set(rec.get('tag_filters', []))):
            continue
        results.append(rec)
    return results



def main() -> None:
    ensure_data_files()
    st.title('UNSC Metadata Backend')
    st.caption('リンク付きメタデータの登録・修正・検索・公開用JSON生成')
    st.caption(f'追加項目は {SCHEMA_OVERRIDES_PATH.name} で定義できます。')

    with st.expander('Help / 使い方', expanded=False):
        col_ja, col_en = st.columns(2)
        with col_ja:
            st.markdown('''
### 使い方

**登録したい場合**
1. 「新規作成」ボタンをクリック
2. 必須項目（URL・決議番号・日付・タイトル）を入力
3. 「保存」をクリック

**編集したい場合**
1. ドロップダウンから対象レコードを選択
2. 「選択読込」をクリック
3. 内容を変更して「保存」

**検索・絞り込みたい場合**
- 左のサイドバーから地域・カテゴリ等でフィルタ可能

**公開JSONを出力したい場合**
- 「公開JSON再生成」ボタンをクリック
- `data/public_records.json` が更新される

**削除したい場合**
- UIに削除機能はありません（誤操作防止）
- 管理者が `data/records.json` を直接編集してください

---

**追加項目（拡張機能）**

`data/schema_overrides.json` を編集することで、固定フォームを変更せずに独自の入力項目を追加できます。

形式例：
```json
{
  "categories": {
    "general": [
      {
        "key": "my_field",
        "label": "独自項目",
        "type": "text",
        "required": false,
        "searchable": false
      }
    ]
  }
}
```

- `type`: `text` / `textarea` / `boolean` / `integer` / `date` / `select` / `multiselect`
- `searchable: true` にすると `tag_filters` に含まれ公開JSON側で検索可能になる
- `select` / `multiselect` は `options` リストも必須
- 変更後はアプリを再起動してください
''')
        with col_en:
            st.markdown('''
### How to Use

**Register a new record**
1. Click "新規作成" (New)
2. Fill in required fields: URL, Resolution number, Date, Title
3. Click "保存" (Save)

**Edit an existing record**
1. Select the target record from the dropdown
2. Click "選択読込" (Load)
3. Modify fields and click "保存" (Save)

**Search / filter records**
- Use the sidebar on the left to filter by region, category, etc.

**Export public JSON**
- Click "公開JSON再生成" (Regenerate public JSON)
- Updates `data/public_records.json`

**Delete a record**
- No delete button in the UI (intentional — prevents accidental loss)
- Administrator must edit `data/records.json` directly

---

**Custom Fields (Extensible Schema)**

Edit `data/schema_overrides.json` to add custom input fields without touching the core form.

Example:
```json
{
  "categories": {
    "general": [
      {
        "key": "my_field",
        "label": "My Custom Field",
        "type": "text",
        "required": false,
        "searchable": false
      }
    ]
  }
}
```

- `type`: `text` / `textarea` / `boolean` / `integer` / `date` / `select` / `multiselect`
- `searchable: true` includes the value in `tag_filters` in the public JSON
- `select` / `multiselect` also require an `options` list
- Restart the app after editing
''')

    schema, schema_errors = load_schema_overrides(SCHEMA_OVERRIDES_PATH)
    if schema_errors:
        st.error('schema_overrides.json に問題があります。修正後に再実行してください。')
        for err in schema_errors:
            st.write(f'- {err}')
        st.stop()
    st.session_state['_runtime_custom_schema'] = schema

    try:
        records = [ensure_custom_defaults(rec, schema) for rec in load_records()]
        public_records = generate_public_records(records, schema)
    except Exception as exc:
        st.error('保存データの読み込みに失敗しました。records.json / public_records.json を確認してください。')
        st.code(str(exc))
        st.stop()
    record_by_id = {rec['record_id']: rec for rec in records}

    st.sidebar.header('Filters')
    filtered_public = run_filters(public_records)
    st.sidebar.caption(f'{len(filtered_public)} / {len(public_records)} 件')

    controls = st.columns([3, 1, 1, 1])
    selection_options = ['—'] + [record_label(rec) for rec in filtered_public]
    labels_to_id = {record_label(rec): rec['record_id'] for rec in filtered_public}
    with controls[0]:
        selected_label = st.selectbox('編集対象レコード', selection_options, key='selected_record_label')
    with controls[1]:
        if st.button('選択読込') and selected_label != '—':
            load_record_into_editor(record_by_id[labels_to_id[selected_label]])
            st.rerun()
    with controls[2]:
        if st.button('新規作成'):
            load_record_into_editor(default_record())
            st.rerun()
    with controls[3]:
        if st.button('公開JSON再生成'):
            try:
                save_public_records(records, PUBLIC_RECORDS_PATH, schema)
            except Exception as exc:
                st.error('公開用JSONの再生成に失敗しました。')
                st.code(str(exc))
            else:
                st.success(f'公開用JSONを再生成しました: {PUBLIC_RECORDS_PATH.name}')

    with st.expander('保存済みレコード一覧', expanded=False):
        st.dataframe(
            [
                {
                    'Resolution number': rec.get('resolution_number'),
                    'Date': rec.get('date'),
                    'Title': rec.get('resolution_title'),
                    'Geo': ', '.join(rec.get('geographical_locations', [])),
                    'Categories': ', '.join(rec.get('categories_present', [])),
                }
                for rec in filtered_public
            ],
            use_container_width=True,
            hide_index=True,
        )

    if 'current_record' not in st.session_state:
        st.info('左上の「新規作成」または「選択読込」から編集を開始してください。')
        return

    current_record = st.session_state.current_record
    st.divider()
    st.header('Editor')
    render_general_section(current_record)
    st.divider()
    render_sanctions(current_record)
    st.divider()
    render_un_peace_operations(current_record)
    st.divider()
    render_non_un_operations(current_record)
    st.divider()
    render_single_sections(current_record)

    st.divider()
    save_cols = st.columns([1, 1, 3])
    with save_cols[0]:
        if st.button('保存', type='primary'):
            draft = materialize_current_record()
            normalized, errors = normalize_record(draft, schema)
            if errors:
                st.error('保存できません。以下を修正してください。')
                for error in errors:
                    st.write(f'- {error}')
            else:
                updated = upsert_record(records, normalized)
                try:
                    save_records(updated)
                    save_public_records(updated, PUBLIC_RECORDS_PATH, schema)
                except Exception as exc:
                    st.error('保存に失敗しました。ファイル権限や保存先を確認してください。')
                    st.code(str(exc))
                else:
                    st.session_state.current_record = normalized
                    clear_editor_widget_state()
                    st.success(f'保存しました。records: {RECORDS_PATH.name}, public: {PUBLIC_RECORDS_PATH.name}')
                    st.rerun()
    with save_cols[1]:
        if st.button('入力内容を再読込'):
            load_record_into_editor(st.session_state.current_record)
            st.rerun()


if __name__ == '__main__':
    main()
