
import pytest
from decimal import Decimal
from applications.capp.capp.adapters.yearn import YearnAdapter, AdapterConfig

@pytest.mark.asyncio
async def test_yearn_adapter_deposit_withdraw():
    # Setup
    config = AdapterConfig(name="Yearn", network="mainnet")
    adapter = YearnAdapter(config)
    
    # Initial Balance
    balance = await adapter.get_balance("USDC")
    assert balance == Decimal("0")
    
    # Test Deposit
    amount = Decimal("100.00")
    tx_hash = await adapter.deposit("USDC", amount)
    assert tx_hash.startswith("0x")
    
    # Check Balance updated
    new_balance = await adapter.get_balance("USDC")
    assert new_balance == amount
    
    # Test Withdraw
    tx_hash_out = await adapter.withdraw("USDC", Decimal("50.00"))
    assert tx_hash_out.startswith("0x")
    
    # Final Balance
    final_balance = await adapter.get_balance("USDC")
    assert final_balance == Decimal("50.00")

@pytest.mark.asyncio
async def test_yearn_adapter_apy():
    config = AdapterConfig(name="Yearn", network="mainnet")
    adapter = YearnAdapter(config)
    
    apy = await adapter.get_apy("USDC")
    assert apy > 0
    assert isinstance(apy, Decimal)
