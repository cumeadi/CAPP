import pytest
from capp import CAPPClient

@pytest.mark.asyncio
async def test_client_init():
    client = CAPPClient(api_key="sk_REDACTED", sandbox=True)
    assert client.sandbox is True
    assert client.api_key == "sk_REDACTED"
    await client.close()

@pytest.mark.asyncio
async def test_context_manager():
    async with CAPPClient(api_key="sk_REDACTED", sandbox=True) as client:
        assert client.api_key == "sk_REDACTED"
