
from web3 import Web3

def generate_key():
    w3 = Web3()
    account = w3.eth.account.create()
    print("\n=== NEW POLYGON TESTNET ACCOUNT ===")
    print(f"Private Key: {account.key.hex()}")
    print(f"Address:     {account.address}")
    print("===================================")
    print("\nAction: Add these to your apps/api/.env file.")
    print("Then fund this address at: https://faucet.polygon.technology/")

if __name__ == "__main__":
    generate_key()
