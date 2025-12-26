from pydantic import BaseModel
from typing import Optional, List, Union
from datetime import datetime


class MessageData(BaseModel):
    ack: Optional[int] = None
    isNew: Optional[bool] = None
    isFirst: Optional[bool] = None


class Message(BaseModel):
    id: Optional[str] = None
    isFromMe: Optional[bool] = None
    sent: Optional[bool] = None
    type: Optional[str] = None
    timestamp: Optional[datetime] = None
    data: Optional[MessageData] = None
    visible: Optional[bool] = None
    accountId: Optional[str] = None
    contactId: Optional[str] = None
    fromId: Optional[str] = None
    serviceId: Optional[str] = None
    toId: Optional[str] = None
    userId: Optional[str] = None
    ticketId: Optional[str] = None
    ticketUserId: Optional[str] = None
    ticketDepartmentId: Optional[str] = None
    quotedMessageId: Optional[str] = None
    origin: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    deletedAt: Optional[datetime] = None
    hsmId: Optional[str] = None
    isComment: Optional[bool] = None
    reactionParentMessageId: Optional[str] = None
    isTranscribing: Optional[bool] = None
    transcribeError: Optional[str] = None
    text: Optional[str] = None
    obfuscated: Optional[bool] = None
    file: Optional[Union[str, dict]] = None
    files: Optional[Union[List[str], List[dict]]] = None
    quotedMessage: Optional[dict] = None
    isFromBot: Optional[bool] = None


class Data(BaseModel):
    id: str
    contactId: str
    serviceId: str
    accountId: str
    command: str
    message: Optional[Message]


class DigisacRequest(BaseModel):
    event: str
    data: Data
    webhookId: str
    timestamp: datetime
