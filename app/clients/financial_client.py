from abc import ABC, abstractmethod


class FinancialClient(ABC):
    @abstractmethod
    def list_payments(self, **kwargs):
        pass

    @abstractmethod
    def get_customer(self, customer_id: str):
        pass
