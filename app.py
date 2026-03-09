from __future__ import annotations

import json
from copy import deepcopy
from typing import Any
import sys

import streamlit as st

from export_public import generate_public_records, save_public_records
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
from storage import PUBLIC_RECORDS_PATH, RECORDS_PATH, ensure_data_files, load_records, save_records, upsert_record
from validators import normalize_record


st.set_page_config(page_title='UNSC Metadata Backend', layout='wide')

st.markdown(
    '<style>'
    '.remove-block-wrapper button { '
    'background-color: #ff4b4b !important; color: white !important; '
    'border: none !important; }'
    '.remove-block-wrapper button:hover { '
    'background-color: #e03e3e !important; }'
    '</style>',
    unsafe_allow_html=True,
)

if sys.version_info < (3, 11):
    st.error('Python 3.11 or later is required.')
    st.stop()

EDITOR_PREFIX = 'editor_'


def clear_editor_widget_state() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith(EDITOR_PREFIX):
            del st.session_state[key]



def load_record_into_editor(record: dict[str, Any]) -> None:
    st.session_state.current_record = clone_record(record)
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



def render_remove_button(label: str, key: str) -> bool:
    cols = st.columns([4, 1])
    with cols[1]:
        st.markdown('<div class="remove-block-wrapper">', unsafe_allow_html=True)
        clicked = st.button(label, key=key)
        st.markdown('</div>', unsafe_allow_html=True)
    return clicked


def render_dynamic_string_list(title: str, list_key: str, values: list[Any]) -> None:
    st.markdown(f'**{title}**')
    if not values:
        st.caption('No items')
    for idx, value in enumerate(values):
        cols = st.columns([5, 1])
        with cols[0]:
            render_text(f'{title} #{idx + 1}', f'{list_key}_{idx}', value)
        with cols[1]:
            if st.button('Remove', key=f'remove_{list_key}_{idx}'):
                current = materialize_current_record()
                target = current['general'][list_key]
                if idx < len(target):
                    target.pop(idx)
                st.session_state.current_record = current
                clear_editor_widget_state()
                st.rerun()
    if st.button(f'Add {title}', key=f'add_{list_key}'):
        current = materialize_current_record()
        current['general'][list_key].append('')
        st.session_state.current_record = current
        clear_editor_widget_state()
        st.rerun()



def render_general_section(record: dict[str, Any]) -> None:
    general = record['general']
    st.subheader('General')
    render_text('UN document URL *', 'editor_general_un_document_url', general.get('un_document_url'), 'Required. Full URL starting with https://  e.g. https://undocs.org/S/RES/2374(2017)')
    cols = st.columns(3)
    with cols[0]:
        render_text('Resolution number *', 'editor_general_resolution_number', general.get('resolution_number'), 'Required. Integer, e.g. 2374')
    with cols[1]:
        render_text('Date *', 'editor_general_date', general.get('date'), 'Required. YYYYMMDD or YYYY-MM-DD e.g. 20170905')
    with cols[2]:
        render_text('Meeting number', 'editor_general_meeting_number', general.get('meeting_number'), 'Integer, e.g. 8040')
    render_multiselect('Geographical location', 'editor_general_geographical_locations', COUNTRY_REGION_OPTIONS, general.get('geographical_locations', []))
    render_text('Resolution title *', 'editor_general_resolution_title', general.get('resolution_title'), 'Required. e.g. The situation in Mali')
    render_dynamic_string_list('References (resolutions)', 'references_resolutions', general.get('references_resolutions', []))
    render_dynamic_string_list('References (PRST)', 'references_prst', general.get('references_prst', []))
    render_dynamic_string_list('References (other)', 'references_other', general.get('references_other', []))
    cols = st.columns(2)
    with cols[0]:
        render_select('Threat level', 'editor_general_threat_level', THREAT_LEVEL_OPTIONS, general.get('threat_level'))
    with cols[1]:
        render_multiselect('Charter invoked', 'editor_general_charter_invoked', CHARTER_INVOKED_OPTIONS, general.get('charter_invoked', []))
    render_text('Referrals', 'editor_general_referrals', general.get('referrals'))



def render_time_period(prefix: str, title: str, current: dict[str, Any]) -> None:
    st.markdown(f'**{title}**')
    render_select('Mode', f'{prefix}_mode', TIME_PERIOD_MODE_OPTIONS, display_mode(current.get('mode')), 'Select how the time period is defined')
    mode = st.session_state.get(f'{prefix}_mode')
    if mode in {'Established for', 'Extended for'}:
        cols = st.columns(2)
        with cols[0]:
            render_text('Duration value', f'{prefix}_duration_value', current.get('duration_value'), 'Required for this mode. Integer, e.g. 12')
        with cols[1]:
            render_select('Duration unit', f'{prefix}_duration_unit', DURATION_UNIT_OPTIONS, current.get('duration_unit'), 'Required for this mode')
    elif mode in {'Established until', 'Extended until'}:
        render_text('Until date', f'{prefix}_until_date', current.get('until_date'), 'Required for this mode. YYYYMMDD or YYYY-MM-DD e.g. 20180630')



def render_sanctions(record: dict[str, Any]) -> None:
    st.subheader('Sanctions')
    if not record['sanctions']:
        st.caption('No blocks')
    for idx, block in enumerate(record['sanctions']):
        with st.expander(f'Sanctions #{idx + 1}', expanded=True):
            render_checkbox('Modified resolution', f'editor_sanctions_{idx}_modified_enabled', block.get('modified_resolution', {}).get('enabled', False), 'Check if this modifies an existing resolution')
            if st.session_state.get(f'editor_sanctions_{idx}_modified_enabled'):
                render_text('Modified resolution number', f'editor_sanctions_{idx}_modified_resolution_number', block.get('modified_resolution', {}).get('resolution_number'), 'Required when checked. Integer, e.g. 2374')
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
            if render_remove_button('Remove this Sanctions block', f'remove_sanctions_block_{idx}'):
                current = materialize_current_record()
                current['sanctions'].pop(idx)
                st.session_state.current_record = current
                clear_editor_widget_state()
                st.rerun()
    if st.button('Add Sanctions block', key='add_sanctions_block'):
        current = materialize_current_record()
        current['sanctions'].append(default_sanction_block())
        st.session_state.current_record = current
        clear_editor_widget_state()
        st.rerun()



def render_un_peace_operations(record: dict[str, Any]) -> None:
    st.subheader('UN peace operations')
    if not record['un_peace_operations']:
        st.caption('No blocks')
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
                render_text('Military', f'editor_un_peace_{idx}_military', block.get('deployed_personnel_levels', {}).get('military'), 'Integer, e.g. 13289')
            with cols[1]:
                render_text('Police', f'editor_un_peace_{idx}_police', block.get('deployed_personnel_levels', {}).get('police'), 'Integer, e.g. 1920')
            with cols[2]:
                render_text('Civilian', f'editor_un_peace_{idx}_civilian', block.get('deployed_personnel_levels', {}).get('civilian'), 'Integer')
            with cols[3]:
                render_text('Other', f'editor_un_peace_{idx}_other', block.get('deployed_personnel_levels', {}).get('other'), 'Integer')
            render_text('Description', f'editor_un_peace_{idx}_description', block.get('description'))
            render_select('Change in authorized strength', f'editor_un_peace_{idx}_change_in_authorized_strength', AUTHORIZED_STRENGTH_CHANGE_OPTIONS, block.get('change_in_authorized_strength'))
            render_multiselect('Collaboration', f'editor_un_peace_{idx}_collaboration', PKO_COLLABORATION_OPTIONS, block.get('collaboration', []))
            render_select('Inter-mission loan/transfer', f'editor_un_peace_{idx}_transfer_direction', INTER_MISSION_TRANSFER_DIRECTION_OPTIONS, display_direction(block.get('inter_mission_loan_transfer', {}).get('direction')))
            if st.session_state.get(f'editor_un_peace_{idx}_transfer_direction'):
                render_text('Transfer target', f'editor_un_peace_{idx}_transfer_target', block.get('inter_mission_loan_transfer', {}).get('target'), 'Required when direction is selected')
            render_checkbox('Authorization level (all necessary measures)', f'editor_un_peace_{idx}_authorization_level', block.get('authorization_level_all_necessary_measures', False))
            render_multiselect('Mandate', f'editor_un_peace_{idx}_mandate', PKO_MANDATE_OPTIONS, block.get('mandate', []))
            if render_remove_button('Remove this UN peace operations block', f'remove_un_peace_block_{idx}'):
                current = materialize_current_record()
                current['un_peace_operations'].pop(idx)
                st.session_state.current_record = current
                clear_editor_widget_state()
                st.rerun()
    if st.button('Add UN peace operations block', key='add_un_peace_block'):
        current = materialize_current_record()
        current['un_peace_operations'].append(default_un_peace_operation_block())
        st.session_state.current_record = current
        clear_editor_widget_state()
        st.rerun()



def render_non_un_operations(record: dict[str, Any]) -> None:
    st.subheader('Non-UN operations/enforcement actions')
    if not record['non_un_operations_enforcement_actions']:
        st.caption('No blocks')
    for idx, block in enumerate(record['non_un_operations_enforcement_actions']):
        with st.expander(f'Non-UN operation #{idx + 1}', expanded=True):
            render_select('Mission name', f'editor_non_un_{idx}_mission_name', NON_UN_MISSION_NAME_OPTIONS, block.get('mission_name'))
            render_select('Authorization action', f'editor_non_un_{idx}_authorization_action', NON_UN_AUTH_ACTION_OPTIONS, block.get('authorization_action'))
            render_time_period(f'editor_non_un_{idx}_authorization_time_period', 'Authorization (time period)', block.get('authorization_time_period', {}))
            render_select('Authorization activation/termination', f'editor_non_un_{idx}_authorization_activation_termination', NON_UN_AUTH_STATUS_OPTIONS, block.get('authorization_activation_termination'))
            st.markdown('**Deployed personnel levels**')
            cols = st.columns(4)
            with cols[0]:
                render_text('Military', f'editor_non_un_{idx}_military', block.get('deployed_personnel_levels', {}).get('military'), 'Integer')
            with cols[1]:
                render_text('Police', f'editor_non_un_{idx}_police', block.get('deployed_personnel_levels', {}).get('police'), 'Integer')
            with cols[2]:
                render_text('Civilian', f'editor_non_un_{idx}_civilian', block.get('deployed_personnel_levels', {}).get('civilian'), 'Integer')
            with cols[3]:
                render_text('Other', f'editor_non_un_{idx}_other', block.get('deployed_personnel_levels', {}).get('other'), 'Integer')
            render_text('Description', f'editor_non_un_{idx}_description', block.get('description'))
            render_select('Change in authorized strength', f'editor_non_un_{idx}_change_in_authorized_strength', AUTHORIZED_STRENGTH_CHANGE_OPTIONS, block.get('change_in_authorized_strength'))
            render_multiselect('Collaboration', f'editor_non_un_{idx}_collaboration', NON_UN_COLLABORATION_OPTIONS, block.get('collaboration', []))
            render_checkbox('Authorization level (all necessary measures)', f'editor_non_un_{idx}_authorization_level', block.get('authorization_level_all_necessary_measures', False))
            render_multiselect('Mandate', f'editor_non_un_{idx}_mandate', NON_UN_MANDATE_OPTIONS, block.get('mandate', []))
            if render_remove_button('Remove this Non-UN operations block', f'remove_non_un_block_{idx}'):
                current = materialize_current_record()
                current['non_un_operations_enforcement_actions'].pop(idx)
                st.session_state.current_record = current
                clear_editor_widget_state()
                st.rerun()
    if st.button('Add Non-UN operations block', key='add_non_un_block'):
        current = materialize_current_record()
        current['non_un_operations_enforcement_actions'].append(default_non_un_operation_block())
        st.session_state.current_record = current
        clear_editor_widget_state()
        st.rerun()



def render_single_sections(record: dict[str, Any]) -> None:
    st.subheader('Criminal Tribunals')
    render_multiselect('Tribunal name', 'editor_criminal_tribunals_tribunal_name', TRIBUNAL_NAME_OPTIONS, record.get('criminal_tribunals', {}).get('tribunal_name', []))

    st.subheader('Other subsidiary organs')
    render_multiselect('Subsidiary organ type', 'editor_other_subsidiary_organs_subsidiary_organ_type', SUBSIDIARY_ORGAN_TYPE_OPTIONS, record.get('other_subsidiary_organs', {}).get('subsidiary_organ_type', []))

    st.subheader('Thematic resolutions')
    render_text('Theme', 'editor_thematic_resolutions_theme', record.get('thematic_resolutions', {}).get('theme', ''))

    st.subheader('Membership')
    render_multiselect('New member name', 'editor_membership_new_member_name', COUNTRY_REGION_OPTIONS, record.get('membership', {}).get('new_member_name', []))
    render_text('Other membership issue', 'editor_membership_other_membership_issue', record.get('membership', {}).get('other_membership_issue', ''))

    st.subheader('Appointment related')
    render_multiselect('Organization', 'editor_appointment_related_organization', APPOINTMENT_ORGANIZATION_OPTIONS, record.get('appointment_related', {}).get('organization', []))

    st.subheader('Other')
    render_text_area('Note', 'editor_other_note', record.get('other', {}).get('note', ''))
    render_checkbox('Annex attached', 'editor_other_annex_attached', record.get('other', {}).get('annex_attached', False))



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
        record['non_un_operations_enforcement_actions'].append(block)

    record['criminal_tribunals']['tribunal_name'] = st.session_state.get('editor_criminal_tribunals_tribunal_name', [])
    record['other_subsidiary_organs']['subsidiary_organ_type'] = st.session_state.get('editor_other_subsidiary_organs_subsidiary_organ_type', [])
    record['thematic_resolutions']['theme'] = st.session_state.get('editor_thematic_resolutions_theme', '')
    record['membership']['new_member_name'] = st.session_state.get('editor_membership_new_member_name', [])
    record['membership']['other_membership_issue'] = st.session_state.get('editor_membership_other_membership_issue', '')
    record['appointment_related']['organization'] = st.session_state.get('editor_appointment_related_organization', [])
    record['other']['note'] = st.session_state.get('editor_other_note', '')
    record['other']['annex_attached'] = st.session_state.get('editor_other_annex_attached', False)
    return record



FILTER_KEYS = ['filter_resolution', 'filter_year', 'filter_geo', 'filter_category', 'filter_tag']


def _clear_filters() -> None:
    for key in FILTER_KEYS:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state['filter_applied'] = False


def _apply_filters() -> None:
    st.session_state['filter_applied'] = True


def run_filters(public_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    resolution_filter = st.text_input('Resolution number', key='filter_resolution')
    filter_cols = st.columns(4)
    years = sorted({rec['year'] for rec in public_records if rec.get('year') is not None})
    year_filter = filter_cols[0].multiselect('Year', years, key='filter_year')
    geo_options = sorted({geo for rec in public_records for geo in rec.get('geographical_locations', [])})
    geo_filter = filter_cols[1].multiselect('Geographical location', geo_options, key='filter_geo')
    category_options = sorted({cat for rec in public_records for cat in rec.get('categories_present', [])})
    category_filter = filter_cols[2].multiselect('Category', category_options, key='filter_category')
    tag_options = sorted({tag for rec in public_records for tag in rec.get('tag_filters', [])})
    tag_filter = filter_cols[3].multiselect('Tag', tag_options, key='filter_tag')

    btn_cols = st.columns([1, 1, 4])
    with btn_cols[0]:
        st.button('Search', key='filter_search', on_click=_apply_filters, type='primary')
    with btn_cols[1]:
        st.button('Clear all', key='filter_clear', on_click=_clear_filters)

    if not st.session_state.get('filter_applied', False):
        return public_records

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



TAB_LIST = '📋 List'
TAB_EDITOR = '✏️ Edit'
TAB_KEY = 'active_view'


def _switch_to_editor(record: dict[str, Any]) -> None:
    """Callback — must be used via on_click so state is set before widget renders."""
    load_record_into_editor(record)
    st.session_state[TAB_KEY] = TAB_EDITOR


def main() -> None:
    ensure_data_files()
    st.title('UNSC Metadata Backend')
    st.caption('Register, edit, search, and export metadata as public JSON')

    try:
        records = load_records()
        public_records = generate_public_records(records)
    except Exception as exc:
        st.error('Failed to load saved data. Please check records.json / public_records.json.')
        st.code(str(exc))
        st.stop()
    record_by_id = {rec['record_id']: rec for rec in records}

    init_if_missing(TAB_KEY, TAB_LIST)
    nav_cols = st.columns([1, 1, 3, 1])
    with nav_cols[0]:
        st.button(
            TAB_EDITOR,
            use_container_width=True,
            type='primary' if st.session_state[TAB_KEY] == TAB_EDITOR else 'secondary',
            on_click=lambda: st.session_state.__setitem__(TAB_KEY, TAB_EDITOR),
            key='nav_editor',
        )
    with nav_cols[1]:
        st.button(
            TAB_LIST,
            use_container_width=True,
            type='primary' if st.session_state[TAB_KEY] == TAB_LIST else 'secondary',
            on_click=lambda: st.session_state.__setitem__(TAB_KEY, TAB_LIST),
            key='nav_list',
        )
    with nav_cols[3]:
        show_help = st.button('Help', key='nav_help', use_container_width=True)
    active_view = st.session_state[TAB_KEY]

    if show_help:
        help_ja, help_en = st.columns(2)
        with help_ja:
            st.info(
                '### 使い方ガイド\n\n'
                '---\n'
                '#### STEP 1 : レコードを登録する\n'
                '1. **「✏️ Edit」** ボタンを押す\n'
                '2. **「New」** を押すと空のフォームが開く\n'
                '3. Resolution number・日付・タイトルなど必要な項目を入力\n'
                '4. Sanctions や UN peace operations が該当する場合は「Add ... block」で入力欄を追加\n'
                '5. 入力が終わったら **「Save」** ボタンを押す\n\n'
                '#### STEP 2 : 登録済みレコードを確認・修正する\n'
                '1. **「📋 List」** ボタンを押す\n'
                '2. 「Search filters」を開いて年・地域・カテゴリなどで絞り込める\n'
                '3. 修正したいレコードの行にある **「Edit」** ボタンを押す\n'
                '4. フォームが開くので内容を修正して **「Save」**\n\n'
                '#### STEP 3 : 公開用 JSON を生成する\n'
                '1. List 画面の **「Regenerate public JSON」** ボタンを押す\n'
                '2. `data/public_records.json` が最新の内容で上書きされる\n\n'
                '#### STEP 4 : フロントエンドに反映する\n'
                '1. 生成された **`data/public_records.json`** を先生に渡す\n'
                '2. 先生がフロント側のリポジトリにファイルを配置してデプロイ\n'
                '3. 公開サイトに反映される\n\n'
                '---\n'
                '*Save のたびに公開用JSONも自動更新されます。'
                '「Regenerate public JSON」は、手動で最新状態を作り直したいときに使ってください。*'
            )
        with help_en:
            st.info(
                '### How to Use\n\n'
                '---\n'
                '#### STEP 1 : Register a record\n'
                '1. Click the **"✏️ Edit"** button\n'
                '2. Click **"New"** to open a blank form\n'
                '3. Fill in Resolution number, date, title, and other fields\n'
                '4. If applicable, click **"Add ... block"** to add Sanctions or UN peace operations sections\n'
                '5. Click **"Save"** when done\n\n'
                '#### STEP 2 : Review / edit existing records\n'
                '1. Click the **"📋 List"** button\n'
                '2. Open **"Search filters"** to filter by year, region, category, etc.\n'
                '3. Click **"Edit"** on the row you want to modify\n'
                '4. Update the form and click **"Save"**\n\n'
                '#### STEP 3 : Generate public JSON\n'
                '1. On the list view, click **"Regenerate public JSON"**\n'
                '2. `data/public_records.json` will be overwritten with the latest data\n\n'
                '#### STEP 4 : Deploy to the frontend\n'
                '1. Hand the generated **`data/public_records.json`** to Prof. Lim\n'
                '2. Prof. Lim places the file in the frontend repository and deploys\n'
                '3. The public site is updated\n\n'
                '---\n'
                '*Public JSON is also auto-updated on every save. '
                'Use "Regenerate public JSON" to manually rebuild it when needed.*'
            )

    # ── List view ──
    if active_view == TAB_LIST:
        with st.expander('Search filters', expanded=False):
            filtered_public = run_filters(public_records)

        header_cols = st.columns([1, 1, 3])
        with header_cols[0]:
            st.markdown(f'**{len(filtered_public)}** shown / {len(public_records)} total')
        with header_cols[1]:
            try:
                save_public_records(records, PUBLIC_RECORDS_PATH)
                public_json = json.dumps(generate_public_records(records), ensure_ascii=False, indent=2)
            except Exception as exc:
                st.error('Failed to generate public JSON.')
                st.code(str(exc))
                public_json = None
            if public_json is not None:
                st.download_button('Download public JSON', data=public_json, file_name='public_records.json', mime='application/json')

        if not filtered_public:
            st.info('No matching records.')
        else:
            for row_idx, rec in enumerate(filtered_public):
                cols = st.columns([1.5, 1, 3, 2, 2, 0.8])
                with cols[0]:
                    st.text(rec.get('resolution_number', ''))
                with cols[1]:
                    st.text(rec.get('date', ''))
                with cols[2]:
                    st.text(rec.get('resolution_title', '') or '')
                with cols[3]:
                    st.text(', '.join(rec.get('geographical_locations', [])))
                with cols[4]:
                    st.text(', '.join(rec.get('categories_present', [])))
                with cols[5]:
                    st.button('Edit', key=f'edit_row_{row_idx}', on_click=_switch_to_editor, args=(record_by_id[rec['record_id']],))

    # ── Editor view ──
    elif active_view == TAB_EDITOR:
        if st.session_state.pop('save_success', False):
            st.success('Record saved successfully.')
        editor_top = st.columns([1, 1, 1, 2])
        with editor_top[0]:
            st.button('New', key='new_from_editor', on_click=_switch_to_editor, args=(default_record(),))
        with editor_top[1]:
            if 'current_record' in st.session_state and st.button('Reload'):
                load_record_into_editor(st.session_state.current_record)
                st.rerun()
        with editor_top[2]:
            if 'current_record' in st.session_state and st.button('Cancel'):
                clear_editor_widget_state()
                del st.session_state['current_record']
                st.rerun()

        if 'current_record' not in st.session_state:
            st.info('Click "New" or use "Edit" on the list view to start editing.')
        else:
            current_record = st.session_state.current_record
            st.divider()
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
            save_cols = st.columns([1, 4])
            with save_cols[0]:
                if st.button('Save', type='primary'):
                    draft = materialize_current_record()
                    normalized, errors = normalize_record(draft)
                    if errors:
                        st.error('Cannot save. Please fix the following:')
                        for error in errors:
                            st.write(f'- {error}')
                    else:
                        updated = upsert_record(records, normalized)
                        try:
                            save_records(updated)
                            save_public_records(updated, PUBLIC_RECORDS_PATH)
                        except Exception as exc:
                            st.error('Save failed. Please check file permissions and destination.')
                            st.code(str(exc))
                        else:
                            clear_editor_widget_state()
                            if 'current_record' in st.session_state:
                                del st.session_state['current_record']
                            st.session_state['save_success'] = True
                            st.rerun()


if __name__ == '__main__':
    main()
