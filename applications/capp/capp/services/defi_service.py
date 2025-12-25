
import structlog
from typing import Dict, Any, Optional
from decimal import Decimal
from web3 import Web3

from applications.capp.capp.config.settings import get_settings
from applications.capp.capp.models.payments import Chain

logger = structlog.get_logger(__name__)

# Minimal Aave V3 Pool ABI
AAVE_V3_POOL_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"internalType": "uint256", "name": "totalCollateralBase", "type": "uint256"},
            {"internalType": "uint256", "name": "totalDebtBase", "type": "uint256"},
            {"internalType": "uint256", "name": "availableBorrowsBase", "type": "uint256"},
            {"internalType": "uint256", "name": "currentLiquidationThreshold", "type": "uint256"},
            {"internalType": "uint256", "name": "ltv", "type": "uint256"},
            {"internalType": "uint256", "name": "healthFactor", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "asset", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "address", "name": "onBehalfOf", "type": "address"},
            {"internalType": "uint16", "name": "referralCode", "type": "uint16"}
        ],
        "name": "supply",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

class AaveService:
    """
    Interaction with Aave V3 Smart Contracts via Web3.py
    """
    
    # Aave V3 Pool Address (Arbitrum Mainnet)
    # Source: https://docs.aave.com/developers/deployed-contracts/v3-mainnet/arbitrum
    AAVE_POOL_ADDRESS = "0x794a61358D6845594F94dc1DB02A252b5b4814aD"

    # USDC Address (Arbitrum Mainnet)
    USDC_ADDRESS = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"

    def __init__(self):
        self.settings = get_settings()
        self.logger = logger.bind(service="AaveService")
        
        # Initialize Web3 Connection
        self.w3 = Web3(Web3.HTTPProvider(self.settings.ARBITRUM_RPC_URL))
        
        if self.w3.is_connected():
            self.logger.info("Connected to Arbitrum RPC")
        else:
            self.logger.error("Failed to connect to Arbitrum RPC")
            
        self.pool_contract = self.w3.eth.contract(
            address=self.AAVE_POOL_ADDRESS,
            abi=AAVE_V3_POOL_ABI
        )

    async def get_user_data(self, user_address: str) -> Dict[str, Any]:
        """
        Fetch real User Account Data from Aave V3
        """
        try:
            # Web3.py calls are synchronous by default, usually wrapped in executor for async
            # For simplicity in this agent, calling directly (might block loop briefly)
            data = self.pool_contract.functions.getUserAccountData(user_address).call()
            
            return {
                "totalCollateralBase": data[0],
                "totalDebtBase": data[1],
                "availableBorrowsBase": data[2],
                "currentLiquidationThreshold": data[3],
                "ltv": data[4],
                "healthFactor": data[5]
            }
        except Exception as e:
            self.logger.error("Error fetching Aave user data", error=str(e))
            return {}

    def build_supply_tx(self, amount: Decimal, user_address: str) -> Dict[str, Any]:
        """
        Construct the transaction data for 'supply' function.
        Does NOT sign or broadcast.
        """
        try:
            # Convert to atomic units (USDC = 6 decimals)
            amount_atomic = int(amount * 1_000_000)
            
            tx = self.pool_contract.functions.supply(
                self.USDC_ADDRESS,
                amount_atomic,
                user_address,
                0 # Referral Code
            ).build_transaction({
                'from': user_address,
                'nonce': self.w3.eth.get_transaction_count(user_address),
                # Gas parameters would be estimated here or set later
            })
            
            return tx
        except Exception as e:
            self.logger.error("Error building supply tx", error=str(e))
            return {}

# Singleton
aave_service = AaveService()
