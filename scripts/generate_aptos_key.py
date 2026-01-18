
from aptos_sdk.account import Account

def generate_key():
    account = Account.generate()
    print("\n=== NEW APTOS TESTNET ACCOUNT ===")
    print(f"Private Key: {str(account.private_key)}")
    print(f"Address:     {str(account.address())}")
    print("=================================")
    print("\nAction: Add these to your apps/api/.env file.")
    print("Then fund this address at: https://custom-faucet.testnet.aptoslabs.com/")

if __name__ == "__main__":
    generate_key()
