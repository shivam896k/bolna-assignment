import requests
import time
import os
from datetime import datetime, timedelta
from logger import logger

class OpenAiApiClient:
    def __init__(self, base_url=None):
        self.base_url = base_url or os.environ.get('OPEN_API_BASE_URL')

    def make_request(self, params):
        try:
            # params['start_at'] = '2025-07-06T04:10:34.846Z'
            params['start_at'] = (datetime.now() - timedelta(minutes==10)).strftime("%Y-%m-%dT%H:%M:%SZ")
            params['end_at'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            response = requests.get(self.base_url, params=params, timeout=5)
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []
