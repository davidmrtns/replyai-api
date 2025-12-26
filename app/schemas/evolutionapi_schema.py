from pydantic import BaseModel
from typing import Optional, List, Literal


class Key(BaseModel):
    remoteJid: str
    fromMe: bool
    id: str
    participant: Optional[str] = None


class DeviceListMetadata(BaseModel):
    senderKeyHash: Optional[str] = None
    senderTimestamp: Optional[str] = None
    senderAccountType: Optional[str] = None
    receiverAccountType: Optional[str] = None
    recipientKeyHash: Optional[str] = None
    recipientTimestamp: Optional[str] = None


class SenderKeyDistributionMessage(BaseModel):
    groupId: str
    axolotlSenderKeyDistributionMessage: str


class MessageContextInfo(BaseModel):
    deviceListMetadata: Optional[DeviceListMetadata] = None
    deviceListMetadataVersion: Optional[int] = None
    messageSecret: str


class ExtendedTextMessage(BaseModel):
    text: str


class ImageMessage(BaseModel):
    url: str
    mimetype: str
    caption: Optional[str] = None
    fileSha256: str
    fileLength: str
    height: int
    width: int
    mediaKey: str
    fileEncSha256: str
    directPath: str
    mediaKeyTimestamp: str
    jpegThumbnail: str
    firstScanSidecar: Optional[str] = None
    firstScanLength: Optional[int] = None
    scansSidecar: Optional[str] = None
    scanLengths: Optional[List[int]] = None
    midQualityFileSha256: Optional[str] = None


class AudioMessage(BaseModel):
    url: str
    mimetype: str
    fileSha256: str
    fileLength: str
    seconds: int
    ptt: bool
    mediaKey: str
    fileEncSha256: str
    directPath: str
    mediaKeyTimestamp: str
    streamingSidecar: str
    waveform: Optional[str] = None


class DocumentMessage(BaseModel):
    url: str
    mimetype: str
    title: str
    fileSha256: str
    fileLength: str
    mediaKey: str
    fileName: str
    fileEncSha256: str
    directPath: str
    mediaKeyTimestamp: str
    contactVcard: bool


class ReactionMessage(BaseModel):
    key: Key
    text: str
    senderTimestampMs: str


class Message(BaseModel):
    conversation: Optional[str] = None
    extendedTextMessage: Optional[ExtendedTextMessage] = None
    imageMessage: Optional[ImageMessage] = None
    audioMessage: Optional[AudioMessage] = None
    documentMessage: Optional[DocumentMessage] = None
    reactionMessage: Optional[ReactionMessage] = None
    base64: Optional[str] = (
        None  # TODO: check if EvolutionAPI V.2 provides base64 directly
    )
    senderKeyDistributionMessage: Optional[SenderKeyDistributionMessage] = None
    messageContextInfo: Optional[MessageContextInfo] = None


class Data(BaseModel):
    key: Key
    pushName: str
    status: str
    message: Message
    messageType: Literal[
        "conversation",
        "extendedTextMessage",
        "imageMessage",
        "audioMessage",
        "videoMessage",
        "documentMessage",
        "reactionMessage",
    ]
    messageTimestamp: int
    instanceId: str
    source: str


class EvolutionAPIRequest(BaseModel):
    event: str
    instance: str
    data: Data
    destination: str
    date_time: str
    sender: str
    server_url: str
    apikey: str
