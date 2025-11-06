from abc import ABC
from api_client.open_ai_api_client import OpenAiApiClient
from parser.open_ai_api_response_parser import OpenAiApiResponseParser

class ResponseParserFactory(ABC):
    @staticmethod
    def parse_response(source, data):
        if source == 'openai':
            return OpenAiApiResponseParser(data).parse()
        else:
            raise ValueError('Invalid source')
