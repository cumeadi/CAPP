import httpx
from .._utils import handle_api_error

class ComplianceModule:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def get_csv_report(self, organization_id: str) -> str:
        """
        Downloads the full transaction history for the organization as CSV.
        Returns the CSV file content as a string.
        """
        res = await self._client.get(f"/compliance/reports/csv?organization_id={organization_id}")
        handle_api_error(res)
        return res.text
