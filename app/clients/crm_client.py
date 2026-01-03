from abc import ABC, abstractmethod


class CRMClient(ABC):
    @abstractmethod
    def create_lead(
        self, deal_name: str, contact_name: str, contact_phone_number: str
    ) -> str | None:
        pass

    @abstractmethod
    def change_stage(
        self, deal_id: str, deal_stage_id: str, user_id: str | None
    ) -> bool:
        pass
