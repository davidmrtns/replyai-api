import json
import requests

from .crm_client import CRMClient


class RDStationClient(CRMClient):
    def __init__(
            self,
            rdstation_token: str,
            initial_deal_stage_id: str,
            default_deal_source_id: str,
            initial_deal_stage_user_id: str,
    ):
        self.headers = {
            'Accept': 'application/json',
            "Content-Type": "application/json"
        }
        self.base_url = 'https://crm.rdstation.com/api/v1'
        self.rdstation_token = rdstation_token
        self.initial_deal_stage_id = initial_deal_stage_id
        self.default_deal_source_id = default_deal_source_id
        self.initial_deal_stage_user_id = initial_deal_stage_user_id


    def create_lead(
            self,
            deal_name: str,
            contact_name: str,
            contact_phone_number: str
    ) -> str | None:
        endpoint = f'{self.base_url}/deals?token={self.rdstation_token}'

        request = {
            'deal': {
                'name': deal_name,
                'rating': 1,
                'user_id': self.initial_deal_stage_user_id,
                'deal_stage_id': self.initial_deal_stage_id
            },
            'deal_source': {
                '_id': self.default_deal_source_id
            },
            'contacts': [
                {
                    'name': contact_name,
                    'phones': [
                        {
                            'phone': contact_phone_number,
                            'type': 'cellphone'
                        }
                    ]
                }
            ]
        }

        response = requests.post(endpoint, headers=self.headers, json=request)
        response_obj: dict = json.loads(response.content) # TODO: rename to response_json
        return response_obj.get('id', None)


    def change_stage(
            self,
            deal_id: str,
            deal_stage_id: str,
            user_id: str | None
    ) -> bool:
        endpoint = f'{self.base_url}/deals/{deal_id}?token={self.rdstation_token}'

        request = {
            'deal_stage_id': deal_stage_id
        }

        if user_id:
            request['deal'] = {
                'user_id': user_id
            }

        response = requests.put(endpoint, headers=self.headers, json=request)
        return response.status_code == 200
