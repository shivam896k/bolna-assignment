from abc import ABC
from api_client.open_ai_api_client import OpenAiApiClient

class MonitorFactory(ABC):
    @staticmethod
    def fetch_transactions(source, base_url=None):
        if source == 'openai':
            params = {}
            return OpenAiApiClient(base_url=base_url).make_request(params=params)
        else:
            raise ValueError('Invalid source')
