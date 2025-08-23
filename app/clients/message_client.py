from abc import abstractmethod
import base64
import requests


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


class MessageClient():
    @abstractmethod
    def send_message(self, **kwargs):
        pass


    @abstractmethod
    def get_contact_data(self, **kwargs) -> ContactData:
        pass


    @abstractmethod
    def get_file_data(self, url: str) -> str | None:
        try:
            response = requests.get(url)
            response.raise_for_status()

            base64_content = base64.b64encode(response.content).decode('utf-8')
            return base64_content
        except requests.exceptions.RequestException as e:
            print(f"Error while downloading file: {e}") # TODO: add logger and raise custom exception
            return None
