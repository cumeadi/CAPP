import aiohttp
import structlog
from typing import Dict, Any, Optional
from decimal import Decimal

from applications.capp.capp.core.agent_wallet import AgentWallet

logger = structlog.get_logger(__name__)

class X402Client:
    """
    HTTP Client wrapper that handles x402 Payment Challenges automatically.
    """
    def __init__(self, wallet: AgentWallet):
        self.wallet = wallet

    async def get(self, url: str) -> Dict[str, Any]:
        """
        Perform a GET request. 
        If 402 is returned, attempts to pay and retry.
        """
        async with aiohttp.ClientSession() as session:
            # 1. Initial Request
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                
                if response.status == 402:
                    return await self._handle_payment_challenge(response, url, session)
                
                # Other errors
                response.raise_for_status()
                
    async def _handle_payment_challenge(self, response: aiohttp.ClientResponse, url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Parse x402 headers, pay via wallet, and retry.
        Stats:
        - HTTP 402 Payment Required
        - Headers: 
            WWW-Authenticate: X402 amount=0.01; currency=USDC; address=0x123...;
        """
        # 1. Parse Challenge
        auth_header = response.headers.get("WWW-Authenticate")
        if not auth_header or "X402" not in auth_header:
            raise Exception("Invalid 402 Response: Missing X402 header")
            
        logger.info("Received x402 Payment Challenge", url=url, header=auth_header)
        
        # Simple Parser (In prod, use a robust parser)
        # Format: X402 amount=0.05, currency=USDC, address=0xRecipient, ref=123
        try:
            params = {}
            parts = auth_header.replace("X402 ", "").split(",")
            for part in parts:
                k, v = part.strip().split("=")
                params[k] = v
                
            amount = Decimal(params.get("amount", "0"))
            currency = params.get("currency", "USDC")
            address = params.get("address")
            ref = params.get("ref", "x402_payment")
            
            if not address:
                raise ValueError("No address in x402 header")
                
        except Exception as e:
            logger.error("Failed to parse x402 header", error=str(e))
            raise e
            
        # 2. Pay Request
        logger.info("Paying x402 Invoice...", amount=str(amount), currency=currency)
        try:
            # Spend from Agent Wallet
            tx = self.wallet.spend(amount, address, f"x402 Access: {url}")
            
            # 3. Retry with Proof
            # In a real system, we'd sign a message or provide tx hash.
            # Here we simulate passing the tx_id as the 'Authorization' token.
            headers = {
                "Authorization": f"X402-Proof tx={tx.tx_id}"
            }
            
            logger.info("Retrying request with payment proof", proof=tx.tx_id)
            async with session.get(url, headers=headers) as retry_response:
                if retry_response.status == 200:
                    logger.info("x402 Payment Accepted. Resource Unlocked.")
                    return await retry_response.json()
                else:
                    logger.error("x402 Retry Failed", status=retry_response.status)
                    retry_response.raise_for_status()

        except ValueError as e:
            logger.warning("x402 Payment Failed (Budget/Balance)", error=str(e))
            raise e
