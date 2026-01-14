import structlog
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.account.account import Account
from starknet_py.net.models.chains import StarknetChainId
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.contract import Contract

from applications.capp.capp.config.settings import settings

logger = structlog.get_logger(__name__)

class StarknetClient:
    """
    Client for interacting with the Starknet Blockchain.
    Handles connection, account management, and transaction submission.
    """
    
    def __init__(self, node_url: str = None, private_key: str = None, account_address: str = None, chain_id_str: str = None):
        self.node_url = node_url or settings.STARKNET_NODE_URL
        self.client = FullNodeClient(node_url=self.node_url)
        self.account = None
        
        # Determine Chain ID
        self.chain_id = StarknetChainId.SEPOLIA if (chain_id_str or settings.STARKNET_CHAIN_ID) == "SN_SEPOLIA" else StarknetChainId.MAINNET

        # Initialize Account if credentials provided
        self._init_account(private_key or settings.STARKNET_PRIVATE_KEY, account_address or settings.STARKNET_ACCOUNT_ADDRESS)

    def _init_account(self, private_key_hex: str, account_address_hex: str):
        """Initialize the Starknet Account object."""
        if not private_key_hex or private_key_hex == "0x0" or not account_address_hex or account_address_hex == "0x0":
            logger.info("StarknetClient initialized in Read-Only mode (no credentials provided)")
            return

        try:
            # Basic validation
            key_pair = KeyPair.from_private_key(int(private_key_hex, 16))
            self.account = Account(
                client=self.client,
                address=account_address_hex,
                key_pair=key_pair,
                chain=self.chain_id,
            )
            logger.info("Starknet Account initialized", address=account_address_hex)
        except Exception as e:
            logger.error("Failed to initialize Starknet Account", error=str(e))
            self.account = None

    async def get_block_number(self):
        """Get the latest block number."""
        try:
            return await self.client.get_block_number()
        except Exception as e:
            logger.error("Failed to get block number", error=str(e))
            return None

    async def get_balance(self, token_address: str = None) -> int:
        """
        Get the balance of the current account.
        Defaults to ETH token if no address provided.
        """
        if not self.account:
            logger.warning("No account initialized, cannot check balance")
            return 0
            
        eth_address = "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7" # ETH on Starknet
        target_token = token_address or eth_address
        
        try:
            balance = await self.account.get_balance(target_token)
            return balance
        except Exception as e:
            logger.error("Failed to get balance", error=str(e))
            return 0

    async def get_balance_of(self, address: str, token_address: str = None) -> int:
        """
        Get balance of ANY address.
        """
        from starknet_py.net.client_models import Call
        from starknet_py.hash.selector import get_selector_from_name
        
        eth_address = "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7"
        target_token = token_address or eth_address
        
        try:
            # Selector for 'balanceOf'
            balance_of_selector = get_selector_from_name("balanceOf")
            
            call = Call(
                to_addr=int(target_token, 16),
                selector=balance_of_selector,
                calldata=[int(address, 16)]
            )
            
            # call_contract returns list of ints (felt)
            # Uint256 is 2 felts (low, high)
            response = await self.client.call_contract(call)
            
            # Parse Uint256
            low = response[0]
            high = response[1]
            balance = (high << 128) + low
            
            return balance
        except Exception as e:
            logger.error("Failed to get balance of address", address=address, error=str(e))
            raise

    async def transfer(self, recipient_address: str, amount: int, token_address: str = None) -> str:
        """
        Transfer tokens to a recipient.
        Returns the transaction hash.
        """
        if not self.account:
            raise ValueError("Account not initialized")

        eth_address = "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7"
        target_token = token_address or eth_address

        try:
            # Simple transfer call (using high-level account Invoke)
            # Starknet.py account.transfer simplifies the wrapper call to ERC20 transfer
            # But specific ERC20 ABI might be needed if not standard. 
            # Account.client.get_balance is simpler, but for transfer we might need Contract wrapper.
            # Starknet-py has a helper for ETH transfer usually.
            
            # For standard ERC20, we can use the execute method on account
            # But let's verify if 'transfer' helper exists or we construct the call.
            
            # Using execute with a Call
            from starknet_py.net.client_models import Call
            
            call = Call(
                to_addr=int(target_token, 16),
                selector=0x83afd3f4caedc6eebf44246fe54e38c95e3179a5ec9ea81740eca5b482d12e, # transfer selector
                calldata=[int(recipient_address, 16), amount, 0] # uint256 amount (low, high)
            )
            
            resp = await self.account.execute(calls=call, auto_estimate=True)
            logger.info("Starknet transfer submitted", tx_hash=hex(resp.transaction_hash))
            return hex(resp.transaction_hash)
            
        except Exception as e:
            logger.error("Failed to execute transfer", error=str(e))
            raise

    async def estimate_transfer_fee(self, recipient_address: str, amount: int, token_address: str = None) -> float:
        """
        Estimate fee for a transfer.
        Returns estimated fee in ETH (float).
        """
        # If no account active, return Mock/Standard Estimate
        if not self.account:
             return 0.00015 # Standard Mock
             
        eth_address = "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7"
        target_token = token_address or eth_address
        
        try:
             from starknet_py.net.client_models import Call
             
             call = Call(
                to_addr=int(target_token, 16),
                selector=0x83afd3f4caedc6eebf44246fe54e38c95e3179a5ec9ea81740eca5b482d12e,
                calldata=[int(recipient_address, 16), amount, 0]
             )
             
             # Estimate Fee using Account wrapper
             estimated_fee = await self.account.estimate_fee(calls=call)
             
             # estimated_fee.overall_fee is in Wei/Fri
             fee_wei = estimated_fee.overall_fee
             return float(fee_wei) / 1e18
             
        except Exception as e:
            logger.warning("Failed to estimate Starknet fee, using default", error=str(e))
            return 0.0002 # Fallback conservative estimate

    def compute_address(self, public_key: int, salt: int = 20) -> str:
        """
        Compute the counterfactual address of an OpenZeppelin Account.
        This allows generating an address offline before deploying the contract.
        
        Using OpenZeppelin Account contract class hash (v0.8.1 or compatible).
        """
        from starknet_py.hash.address import compute_address
        from starknet_py.net.models import StarknetChainId
        
        # OpenZeppelin Account Class Hash (Standard on Sepolia/Mainnet for recent versions)
        # Verify this hash for the specific version we want to support.
        # For now, using a known common hash for OZ Account (v0.8.1)
        # Note: In production, this should be configurable or fetched dynamically.
        # This is the class hash for OpenZeppelin Account v0.8.1
        OZ_ACCOUNT_CLASS_HASH = 0x05400e90f7e0ae78bd02c77cd75527280470e2fe19c54970dd79dc37a9d3645c
        
        # PROXY_CLASS_HASH is often used if we use a proxy pattern, 
        # but modern Starknet often uses direct deploy of the account class.
        # Let's assume direct deploy for simplicity unless standard requires proxy.
        # Starknet.py 'deploy_account' usually works with the class directly.
        
        # The constructor calldata for OZ account is usually just [public_key]
        constructor_calldata = [public_key]
        
        address = compute_address(
            class_hash=OZ_ACCOUNT_CLASS_HASH,
            constructor_calldata=constructor_calldata,
            salt=salt,
            deployer_address=0, # Account contracts are usually deployed by 0 (udc-like but self-deployed address computation)
        )
        
        return hex(address)

    async def deploy_account(self, public_key: int, private_key: int, salt: int = 20) -> str:
        """
        Deploy a pre-calculated account to the network.
        Requires the address to be funded with ETH for gas.
        """
        from starknet_py.net.account.account import Account
        from starknet_py.net.signer.stark_curve_signer import KeyPair
        
        # 1. Compute Address (to verify or log)
        address = self.compute_address(public_key, salt)
        logger.info("Deploying account", address=address)
        
        # 2. Initialize the Account object (even though it's not deployed yet)
        # We need the Signer to sign the DEPLOY_ACCOUNT transaction
        key_pair = KeyPair(private_key=private_key, public_key=public_key)
        
        # OZ Account Class Hash
        OZ_ACCOUNT_CLASS_HASH = 0x05400e90f7e0ae78bd02c77cd75527280470e2fe19c54970dd79dc37a9d3645c
        
        account = Account(
            client=self.client,
            address=address,
            key_pair=key_pair,
            chain=self.chain_id,
        )
        
        # 3. Create and Sign Deploy Account Transaction
        try:
            # Starknet.py helper for deploying standard accounts
            # Using deploy_account_v3 as v1/original is likely deprecated
            deploy_result = await Account.deploy_account_v3(
                address=address,
                class_hash=OZ_ACCOUNT_CLASS_HASH,
                salt=salt,
                key_pair=key_pair,
                client=self.client,
                # chain=self.chain_id, # Removed
                constructor_calldata=[public_key],
                auto_estimate=True # requires account to be funded
            )
            
            logger.info("Deploy Account transaction submitted", tx_hash=hex(deploy_result.hash))
            
            # Wait for acceptance?
            # await deploy_result.wait_for_acceptance()
            return hex(deploy_result.hash)
            
        except Exception as e:
            logger.error("Failed to deploy account", error=str(e))
            raise

# Singleton instance accessor
_starknet_client = None

def get_starknet_client() -> StarknetClient:
    global _starknet_client
    if not _starknet_client:
        _starknet_client = StarknetClient()
    return _starknet_client
