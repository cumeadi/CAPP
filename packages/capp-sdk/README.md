# CAPP Python SDK

The official Python SDK for the CAPP Network.

## Installation

```bash
pip install capp-sdk
```

## Quickstart

```python
import asyncio
from capp import CAPPClient

async def main():
    # Initialize in sandbox mode
    client = CAPPClient(api_key="sk_REDACTED", sandbox=True)
    
    # Check balance
    balances = await client.wallet.get_balance()
    print(balances)

if __name__ == "__main__":
    asyncio.run(main())
```
