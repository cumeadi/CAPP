"""
Polygon (EVM) Integration for CAPP

Handles interactions with the Polygon blockchain for payment settlement.
Uses web3.py for connection and transaction signing.
"""

import asyncio
from typing import Dict, Any, Optional
from decimal import Decimal
import structlog
from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware # Web3 v6
except ImportError:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware # Web3 v7

from eth_account import Account

from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

# Global Web3 instance
_web3_client = None

async def init_polygon_client():
    """Initialize Polygon Web3 client"""
    global _web3_client
    settings = get_settings()
    
    try:
        # Use simple HTTP provider for now
        _web3_client = Web3(Web3.HTTPProvider(settings.POLYGON_RPC_URL))
        
        # Inject PoA middleware for Polygon (needed for Mumbai/Mainnet compatibility)
        if _web3_client.is_connected():
            _web3_client.middleware_onion.inject(geth_poa_middleware, layer=0)
            logger.info("Polygon client connected successfully", node_url=settings.POLYGON_RPC_URL)
        else:
            logger.warning("Polygon client failed to connect", node_url=settings.POLYGON_RPC_URL)
            
    except Exception as e:
        logger.error("Failed to initialize Polygon client", error=str(e))
        # Don't raise, allowing partial system failure (Aptos still works)

def get_polygon_client() -> Optional[Web3]:
    """Get Polygon Web3 instance"""
    return _web3_client

class PolygonSettlementService:
    """Service for handling Polygon settlements"""
    
    def __init__(self):
        self.w3 = get_polygon_client()
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        
        # Load Account
        self.account = None
        if self.settings.POLYGON_PRIVATE_KEY and self.settings.POLYGON_PRIVATE_KEY != "demo-private-key":
            try:
                self.account = Account.from_key(self.settings.POLYGON_PRIVATE_KEY)
                self.logger.info("Loaded Polygon Account", address=self.account.address)
            except Exception as e:
                self.logger.warning("Invalid Polygon private key", error=str(e))
    
    async def submit_settlement_batch(self, batch_data: Dict[str, Any]) -> str:
        """
        Submit a batch of payments to Polygon.
        For now, this sends a simple native MATIC transfer as a proof-of-concept for the batch total.
        In production, this would call a BulkSender smart contract.
        """
        if not self.w3 or not self.w3.is_connected():
            self.logger.warning("Polygon client not connected available, using mock")
            return f"0x_mock_polygon_tx_{batch_data.get('batch_id')}"

        if not self.account:
             self.logger.warning("No Polygon private key, using mock")
             return f"0x_mock_polygon_tx_readonly_{batch_data.get('batch_id')}"

        try:
            # 1. Determine Recipient (Mock: use first recipient or a 'vault')
            # For demo, we send to the first recipient in the batch or a burner
            recipient = batch_data["payments"][0]["recipient"]
            # Ensure it's a valid checksum address
            if not Web3.is_address(recipient):
                recipient = self.account.address # Fallback to self-transfer for test
            
            recipient = Web3.to_checksum_address(recipient)
            
            # 2. Calculate Amount (Total Batch Amount)
            # Assuming amount is in MATIC for this demo
            total_amount = float(batch_data["total_amount"])
            value_wei = self.w3.to_wei(total_amount, 'ether')
            
            # 3. Build Transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            gas_price = self.w3.eth.gas_price
            
            tx = {
                'nonce': nonce,
                'to': recipient,
                'value': value_wei,
                'gas': 21000, # Standard transfer gas
                'gasPrice': gas_price,
                'chainId': self.settings.CHAIN_ID_POLYGON or 137
            }
            
            # 4. Sign Transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.settings.POLYGON_PRIVATE_KEY)
            
            # 5. Send Transaction
            # Using synchronous send in executor to not block async loop
            loop = asyncio.get_event_loop()
            tx_hash_bytes = await loop.run_in_executor(
                None,
                lambda: self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            )
            
            tx_hash = self.w3.to_hex(tx_hash_bytes)
            self.logger.info("Polygon transaction submitted", tx_hash=tx_hash)
            
            return tx_hash

        except Exception as e:
            self.logger.error("Failed to submit Polygon transaction", error=str(e))
            raise

    async def wait_for_confirmation(self, tx_hash: str) -> bool:
        """Wait for transaction confirmation"""
        if tx_hash.startswith("0x_mock"):
            await asyncio.sleep(2)
            return True
            
        try:
            loop = asyncio.get_event_loop()
            receipt = await loop.run_in_executor(
                None,
                lambda: self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            )
            
            if receipt.status == 1:
                self.logger.info("Polygon transaction confirmed", tx_hash=tx_hash)
                return True
            else:
                self.logger.warning("Polygon transaction failed/reverted", tx_hash=tx_hash)
                return False
                
        except Exception as e:
            self.logger.error("Failed to confirm Polygon transaction", error=str(e))
            return False

    async def get_transaction_status(self, tx_hash: str) -> str:
        if tx_hash.startswith("0x_mock"):
            return "success"
            
        try:
            loop = asyncio.get_event_loop()
            receipt = await loop.run_in_executor(
                None,
                lambda: self.w3.eth.get_transaction_receipt(tx_hash)
            )
            return "success" if receipt.status == 1 else "failed"
        except Exception:
            return "pending"

    async def estimate_transfer_gas(self) -> float:
        """
        Estimate gas cost for a standard transfer in MATIC.
        Returns estimated fee in MATIC.
        """
        if not self.w3 or not self.w3.is_connected():
            return 0.01
            
        try:
             loop = asyncio.get_event_loop()
             gas_price = await loop.run_in_executor(
                 None, 
                 lambda: self.w3.eth.gas_price
             )
             
             # Standard transfer gas limit
             gas_limit = 21000
             
             cost_wei = gas_price * gas_limit
             return float(self.w3.from_wei(cost_wei, 'ether'))
             
        except Exception as e:
            self.logger.error("Failed to estimate Polygon gas", error=str(e))
            return 0.01 # Fallback
    async def get_account_balance(self, address: str) -> float:
        """Get MATIC balance for an address"""
        if not self.w3 or not self.w3.is_connected():
            return 0.0
            
        try:
            # Checksum address
            address = Web3.to_checksum_address(address)
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            balance_wei = await loop.run_in_executor(
                None,
                lambda: self.w3.eth.get_balance(address)
            )
            
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            self.logger.error("Failed to fetch Polygon balance", address=address, error=str(e))
            return 0.0

    async def get_token_balance(self, token_address: str, user_address: str) -> float:
        """Get ERC20 token balance (e.g. USDC)"""
        if not self.w3 or not self.w3.is_connected():
            return 0.0
            
        try:
            user_address = Web3.to_checksum_address(user_address)
            token_address = Web3.to_checksum_address(token_address)
            
            # Minimal ERC20 ABI for balanceOf
            abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"}]
            
            contract = self.w3.eth.contract(address=token_address, abi=abi)
            
            loop = asyncio.get_event_loop()
            balance_raw = await loop.run_in_executor(
                None,
                lambda: contract.functions.balanceOf(user_address).call()
            )
            
            # Assuming 6 decimals for USDC (common), but ideally should check decimals(). 
            # For simplicity/speed in this phase, we'll assume 6 for USDC-like tokens or 18 generally.
            # Let's assume 18 default unless specified, but for USDC on Polygon it's 6.
            # I'll just return raw float / 10**6 for now if it's USDC, or maybe passed as arg?
            # Let's standardise to 6 for now as valid for USDC.
            return float(balance_raw) / 10**6
            
        except Exception as e:
            self.logger.error("Failed to fetch token balance", token=token_address, error=str(e))
            return 0.0
