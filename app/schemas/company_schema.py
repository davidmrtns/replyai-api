from typing import List, Optional
from datetime import time

from app.db.models import (
    AgendaClientTypeEnum,
    CRMClientTypeEnum,
    EventCancellationTypeEnum,
    FinancialClientTypeEnum,
    MessageClientTypeEnum,
)
from app.schemas.employee_schema import EmployeeSchema
from .base import OrmBaseModel, StrictBaseModel


class CompanySchema(OrmBaseModel):
    id: int

    slug: str
    company_name: str
    token: str
    is_active: bool

    ai_reply_error_message: Optional[str] = None
    default_assistant_id: Optional[int] = None

    message_client_type: Optional[str]
    agenda_client_type: Optional[str]
    crm_client_type: Optional[str]
    financial_client_type: Optional[str]

    recall_timeout_minutes: Optional[int] = None
    final_recall_timeout_minutes: Optional[int] = None
    recall_quantity: int = 0
    recall_is_active: bool = False
    confirmation_recall_is_active: bool = False
    agenda_starting_time: Optional[time] = None
    agenda_ending_time: Optional[time] = None
    timezone: Optional[str] = None
    event_cancellation_type: Optional[str] = None
    appointment_duration_in_minutes: Optional[int] = None
    appointment_confirmation_is_active: bool = False

    charge_due_payments: bool = False
    send_due_payments_on_charge: bool = False
    charge_due_payments_is_active: bool = False
    openai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None

    employees: List[EmployeeSchema]
    # TODO: add other related data, such as clients


class CompanyMinSchema(OrmBaseModel):
    id: int
    slug: str
    company_name: str


class CreateCompanySchema(StrictBaseModel):
    company_name: str
    slug: str
    timezone: str
    openai_api_key: str
    elevenlabs_api_key: Optional[str] = None
    is_active: bool


class UpdateCompanySchema(StrictBaseModel):
    company_name: Optional[str] = None
    is_active: Optional[bool] = None

    ai_reply_error_message: Optional[str] = None
    default_assistant_id: Optional[int] = None

    message_client_type: Optional[MessageClientTypeEnum] = None
    agenda_client_type: Optional[AgendaClientTypeEnum] = None
    crm_client_type: Optional[CRMClientTypeEnum] = None
    financial_client_type: Optional[FinancialClientTypeEnum] = None

    recall_timeout_minutes: Optional[int] = None
    final_recall_timeout_minutes: Optional[int] = None
    recall_quantity: Optional[int] = None
    recall_is_active: Optional[bool] = None
    confirmation_recall_is_active: Optional[bool] = None
    agenda_starting_time: Optional[time] = None
    agenda_ending_time: Optional[time] = None
    timezone: Optional[str] = None
    event_cancellation_type: Optional[EventCancellationTypeEnum] = None
    appointment_duration_in_minutes: Optional[int] = None
    appointment_confirmation_is_active: Optional[bool] = None

    charge_due_payments: Optional[bool] = None
    send_due_payments_on_charge: Optional[bool] = None
    charge_due_payments_is_active: Optional[bool] = None

    openai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
