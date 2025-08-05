import enum

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum, Time, Float
from sqlalchemy.orm import relationship

from app.db.database import Base


class MessageClientTypeEnum(str, enum.Enum):
    digisac = "digisac"
    evolution = "evolution"


class AgendaClientTypeEnum(str, enum.Enum):
    outlook = "outlook"
    google_calendar = "google_calendar"


class CRMClientTypeEnum(str, enum.Enum):
    rdstation = "rdstation"


class FinancialClientTypeEnum(str, enum.Enum):
    asaas = "asaas"


class EventCancellationTypeEnum(str, enum.Enum):
    keep = "keep"
    delete = "delete"


class AssistantPurposeEnum(str, enum.Enum):
    reply = "reply"
    recall = "recall"
    rewrite = "rewrite"
    schedule = "schedule"
    charge = "charge"


class LastMessageFromEnum(str, enum.Enum):
    assistant = "assistant"
    customer = "customer"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, index=True, nullable=False)
    company_name = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    ai_reply_error_message = Column(String)
    message_client_type = Column(Enum(MessageClientTypeEnum))
    agenda_client_type = Column(Enum(AgendaClientTypeEnum))
    crm_client_type = Column(Enum(CRMClientTypeEnum))
    financial_client_type = Column(Enum(FinancialClientTypeEnum))
    recall_timeout_minutes = Column(Integer)
    final_recall_timeout_minutes = Column(Integer)
    recall_quantity = Column(Integer, default=0)
    recall_is_active = Column(Boolean, default=False, nullable=False)
    confirmation_recall_is_active = Column(Boolean, default=False, nullable=False)
    agenda_starting_time = Column(Time)
    agenda_ending_time = Column(Time)
    timezone = Column(String)
    event_cancellation_type = Column(Enum(EventCancellationTypeEnum))
    appointment_duration_in_minutes = Column(Integer)
    appointment_confirmation_is_active = Column(Boolean, default=False, nullable=False)
    charge_due_payments = Column(Boolean, default=False, nullable=False)
    send_due_payments_on_charge = Column(Boolean, default=False, nullable=False)
    charge_due_payments_is_active = Column(Boolean, default=False, nullable=False)
    openai_api_key = Column(String)
    elevenlabs_api_key = Column(String)
    default_assistant_id = Column(Integer, ForeignKey("assistants.id"))

    default_assistant = relationship("Assistant", foreign_keys=[default_assistant_id])


class Voice(Base):
    __tablename__ = "voices"

    id = Column(Integer, primary_key=True, index=True)
    voice_name = Column(String)
    elevenlabs_voice_id = Column(String, nullable=False)
    stability = Column(Float)
    similarity_boost = Column(Float)
    style = Column(Float)
    company_id = Column(Integer, ForeignKey("companies.id"))

    assistant = relationship("Assistant", backref="voice")
    company = relationship("Company", backref="voices")


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(Integer, primary_key=True, index=True)
    openai_assistant_id = Column(String, nullable=False)
    assistant_name = Column(String, nullable=False)
    purpose = Column(Enum(AssistantPurposeEnum), nullable=False)
    shortcut = Column(String)
    voice_id = Column(Integer, ForeignKey("voices.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id")) # TODO: check table order with company

    company = relationship("Company", backref="assistants", foreign_keys=[company_id])


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, index=True)
    last_message_from = Column(Enum(LastMessageFromEnum), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"))

    contact = relationship("Contact", backref="threads", foreign_keys=[contact_id])


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(String, index=True)
    phone_number = Column(String)
    contact_name = Column(String)
    current_thread = Column(Integer, ForeignKey("threads.id"), nullable=True, default=None)
    current_assistant = Column(Integer, ForeignKey("assistants.id"), nullable=True, default=None)
    last_message_at = Column(DateTime)
    recall_count = Column(Integer, default=0)
    under_appointment_confirmation = Column(Boolean, default=False)
    receive_ai_replies = Column(Boolean, default=True)
    awaiting_human_contact = Column(Boolean, default=False)
    deal_id = Column(String, default=None)
    company_id = Column(Integer, ForeignKey("companies.id"))

    company = relationship("Company", backref="contacts")


class DigisacClient(Base):
    __tablename__ = "digisac_clients"

    id = Column(Integer, primary_key=True, index=True)
    digisac_slug = Column(String)
    service_id = Column(String)
    digisac_token = Column(String)
    digisac_default_user = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))

    company = relationship("Company")


class EvolutionAPIClient(Base):
    __tablename__ = "evolutionapi_clients"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String)
    instance_name = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))

    company = relationship("Company")


class OutlookClient(Base):
    __tablename__ = "outlook_clients"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String)
    refresh_token = Column(String)
    expires_in = Column(Integer)
    expires_at = Column(Float)
    default_user = Column(String)
    timezone = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))

    company = relationship("Company")


class GoogleCalendarClient(Base):
    __tablename__ = "googlecalendar_clients"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String)
    refresh_token = Column(String)
    expires_in = Column(Integer)
    client_email = Column(String)
    timezone = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))

    company = relationship("Company")


class RDStationCRMClient(Base):
    __tablename__ = "rdstationcrm_clients"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String)
    default_source_id = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))

    company = relationship("Company")


class RDStationCRMDealStage(Base):
    __tablename__ = "rdstationcrm_deal_stages"

    id = Column(Integer, primary_key=True, index=True)
    shortcut = Column(String)
    deal_stage_id = Column(String)
    user_id = Column(String)
    is_initial_deal_stage = Column(Boolean)
    rdstationcrm_client_id = Column(Integer, ForeignKey("rdstationcrm_clients.id"))

    rdstationcrm_client = relationship("RDStationCRMClient", backref="stages")
