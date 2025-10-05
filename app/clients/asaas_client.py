import requests
from requests import Response

from .financial_client import FinancialClient


class AsaasClient(FinancialClient):
    def __init__(self, token: str):
        self.headers = {
            'accept': 'application/json',
            'access_token': token
        }
        self.base_url = 'https://api.asaas.com/v3'


    def list_payments(
            self,
            due_date_le: str | None = None,
            due_date_ge: str | None = None,
            status: str | None = None,
            limit: str | None = None
    ) -> Response:
        endpoint = f'{self.base_url}/payments'
        params = {}

        if due_date_le:
            params['dueDate[le]'] = due_date_le
        if due_date_ge:
            params['dueDate[ge]'] = due_date_ge
        if status:
            params['status'] = status
        if limit:
            params['limit'] = limit

        response = requests.get(endpoint, headers=self.headers, params=params)
        return response


    def get_customer(self, customer_id: str) -> Response:
        endpoint = f'{self.base_url}/customers/{customer_id}'

        response = requests.get(endpoint, headers=self.headers)
        return response
