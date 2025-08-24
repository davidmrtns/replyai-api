from abc import abstractmethod
from io import BytesIO
from typing import Tuple


FileData = Tuple[str, str, BytesIO]


class ContactData:
    def __init__(self, contact_name: str, phone_number: str):
        self.contact_name = contact_name
        self.phone_number = phone_number


    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            contact_name=data["contact_name"],
            phone_number=data["phone_number"]
        )


    def to_dict(self):
        return {
            "contactName": self.contact_name,
            "phoneNumber": self.phone_number
        }


    def __str__(self):
        import json
        return json.dumps(self.to_dict(), indent=2)
    

class MediaMessageData:
    def __init__(self, mediatype: str, mimetype: str, caption: str, media: str, filename: str):
        self.mediatype = mediatype
        self.mimetype = mimetype
        self.caption = caption
        self.media = media
        self.filename = filename


class MessageClient:
    @abstractmethod
    def send_message(self, **kwargs):
        pass


    @abstractmethod
    def get_contact_data(self, **kwargs) -> ContactData:
        pass


    @abstractmethod
    def get_contact_id(self, phone_number: str, **kwargs) -> str:
        pass


    @abstractmethod
    def get_file_data(self, **kwargs) -> FileData | None:
        pass
