import os
import requests

class ServiceNowClient:
    def __init__(self):
        self.base_url = os.environ["SERVICENOW_INSTANCE"]
        self.auth = (
            os.environ["SERVICENOW_USER"],
            os.environ["SERVICENOW_PASSWORD"],
        )
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({"Accept": "application/json"})

    def _url(self, table: str, sys_id: str | None = None) -> str:
        url = f"{self.base_url}/api/now/table/{table}"
        return f"{url}/{sys_id}" if sys_id else url
    
    def query(self, table: str, encoded_query: str, fields: list[str]) -> list[dict]:
        results = []
        offset = 0
        limit = 100
        while True:
            response = self.session.get(
                self._url(table),
                params = {
                    "sysparm_query": encoded_query,
                    "sysparm_fields": ",".join(fields),
                    "sysparm_limit": limit,
                    "sysparm_offset": offset,
                },
                timeout = 30,
            )
            response.raise_for_status()
            page = response.json()["result"]
            results.extend(page)
            if len(page) < limit:
                return results
            offset += limit

    def create(self, table: str, payload: dict) -> dict:
        response = self.session.post(self._url(table), json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["result"]
    
    def update(self, table: str, sys_id: str, payload: dict) -> dict:
        response = self.session.patch(
            self._url(table, sys_id), json=payload, timeout=30
        )
        response.raise_for_status()
        return response.json()["result"]