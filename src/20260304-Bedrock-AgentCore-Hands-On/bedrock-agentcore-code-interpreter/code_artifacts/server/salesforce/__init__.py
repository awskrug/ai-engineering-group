# servers/salesforce/__init__.py
from .sfdc_get_record import sfdc_get_record
from .sfdc_update_record import sfdc_update_record

__all__ = [
    'sfdc_get_record',
    'sfdc_update_record',
]
