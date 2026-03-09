"""Fixed form specification for the UNSC metadata backend.

The Excel workbook is the source of truth for category structure, field labels,
conditional inputs, repeated blocks, and option sets. This module translates
that workbook into implementation-friendly Python structures.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

CATEGORY_LABELS = {
    'general': 'General',
    'sanctions': 'Sanctions',
    'un_peace_operations': 'UN peace operations',
    'non_un_operations_enforcement_actions': 'Non-UN operations/enforcement actions',
    'criminal_tribunals': 'Criminal Tribunals',
    'other_subsidiary_organs': 'Other subsidiary organs',
    'thematic_resolutions': 'Thematic resolutions',
    'membership': 'Membership',
    'appointment_related': 'Appointment related',
    'other': 'Other',
}

CATEGORY_ORDER = [
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
]

TIME_PERIOD_MODE_MAP = {
    'Established for': 'established_for',
    'Established until': 'established_until',
    'Extended for': 'extended_for',
    'Extended until': 'extended_until',
}
TIME_PERIOD_MODE_MAP_REVERSE = {v: k for k, v in TIME_PERIOD_MODE_MAP.items()}

TRANSFER_DIRECTION_MAP = {'To': 'to', 'From': 'from'}
TRANSFER_DIRECTION_MAP_REVERSE = {v: k for k, v in TRANSFER_DIRECTION_MAP.items()}

YES_NO_OPTIONS = [None, True, False]

GENERAL_REQUIRED_FIELDS = [
    'un_document_url',
    'resolution_number',
    'date',
    'resolution_title',
]

TAG_FILTER_PATHS = {
    'general': [
        ('general', 'geographical_locations'),
        ('general', 'threat_level'),
        ('general', 'charter_invoked'),
    ],
    'sanctions': [
        ('items_regulated_inbound',),
        ('items_regulated_outbound',),
        ('items_regulated_domestic',),
        ('exceptions',),
        ('target_state',),
        ('reason',),
        ('sanctions_status',),
        ('sanctions_change',),
    ],
    'un_peace_operations': [
        ('operation_type',),
        ('mission_name',),
        ('mission_activity',),
        ('mission_activation_termination',),
        ('change_in_authorized_strength',),
        ('collaboration',),
        ('mandate',),
    ],
    'non_un_operations_enforcement_actions': [
        ('mission_name',),
        ('authorization_action',),
        ('authorization_activation_termination',),
        ('change_in_authorized_strength',),
        ('collaboration',),
        ('mandate',),
    ],
    'criminal_tribunals': [('criminal_tribunals', 'tribunal_name')],
    'other_subsidiary_organs': [('other_subsidiary_organs', 'subsidiary_organ_type')],
    'membership': [('membership', 'new_member_name')],
    'appointment_related': [('appointment_related', 'organization')],
}


def default_time_period() -> dict[str, Any]:
    return {
        'mode': None,
        'duration_value': '',
        'duration_unit': None,
        'until_date': '',
    }


def default_modified_resolution() -> dict[str, Any]:
    return {'enabled': False, 'resolution_number': ''}



def default_inter_mission_loan_transfer() -> dict[str, Any]:
    return {'direction': None, 'target': ''}



def default_personnel_levels() -> dict[str, Any]:
    return {
        'military': '',
        'police': '',
        'civilian': '',
        'other': '',
    }



def default_sanction_block() -> dict[str, Any]:
    return {
        'modified_resolution': default_modified_resolution(),
        'items_regulated_inbound': [],
        'items_regulated_outbound': [],
        'items_regulated_domestic': [],
        'exceptions': [],
        'target_comprehensive': False,
        'target_region': '',
        'target_state': [],
        'target_non_state': '',
        'target_entities_business': '',
        'target_individual': '',
        'reason': [],
        'sanctions_status': None,
        'sanctions_change': None,
        'sanctions_time_period': default_time_period(),
    }



def default_un_peace_operation_block() -> dict[str, Any]:
    return {
        'operation_type': None,
        'mission_name': None,
        'mission_activity': None,
        'authorization_time_period': default_time_period(),
        'mission_activation_termination': None,
        'deployed_personnel_levels': default_personnel_levels(),
        'description': '',
        'change_in_authorized_strength': None,
        'collaboration': [],
        'inter_mission_loan_transfer': default_inter_mission_loan_transfer(),
        'authorization_level_all_necessary_measures': False,
        'mandate': [],
    }



def default_non_un_operation_block() -> dict[str, Any]:
    return {
        'mission_name': None,
        'authorization_action': None,
        'authorization_time_period': default_time_period(),
        'authorization_activation_termination': None,
        'deployed_personnel_levels': default_personnel_levels(),
        'description': '',
        'change_in_authorized_strength': None,
        'collaboration': [],
        'authorization_level_all_necessary_measures': False,
        'mandate': [],
    }



def default_record() -> dict[str, Any]:
    return {
        'record_id': str(uuid4()),
        'general': {
            'un_document_url': '',
            'resolution_number': '',
            'date': '',
            'meeting_number': '',
            'geographical_locations': [],
            'resolution_title': '',
            'references_resolutions': [],
            'references_prst': [],
            'references_other': [],
            'threat_level': None,
            'charter_invoked': [],
            'referrals': '',
        },
        'sanctions': [],
        'un_peace_operations': [],
        'non_un_operations_enforcement_actions': [],
        'criminal_tribunals': {'tribunal_name': []},
        'other_subsidiary_organs': {'subsidiary_organ_type': []},
        'thematic_resolutions': {'theme': ''},
        'membership': {'new_member_name': [], 'other_membership_issue': ''},
        'appointment_related': {'organization': []},
        'other': {'note': '', 'annex_attached': False},
        'created_at': None,
        'updated_at': None,
    }



def clone_record(record: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(record)
