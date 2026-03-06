#!/usr/bin/env python3
"""
testnet_faucet.py — CI testnet faucet integration for CAPP

Requests testnet tokens from public faucets so that CI pipeline test wallets
are funded before running integration tests.

Supported networks:
  - Aptos Devnet  (via Aptos Faucet REST API)
  - Starknet Sepolia  (via Starknet Sepolia faucet API)
  - Polygon Amoy  (via Alchemy / Polygon faucet)

Usage:
  python scripts/testnet_faucet.py --network aptos
  python scripts/testnet_faucet.py --network starknet
  python scripts/testnet_faucet.py --network polygon
  python scripts/testnet_faucet.py --all        # fund all networks
  python scripts/testnet_faucet.py --check       # verify balances
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Configuration (read from env, populated by .env.testnet in CI)
# ---------------------------------------------------------------------------
APTOS_FAUCET_URL = os.getenv(
    "APTOS_FAUCET_URL", "https://faucet.devnet.aptoslabs.com"
)
APTOS_ACCOUNT_ADDRESS = os.getenv("APTOS_ACCOUNT_ADDRESS", "")
APTOS_NODE_URL = os.getenv(
    "APTOS_NODE_URL", "https://api.devnet.aptoslabs.com/v1"
)

STARKNET_RPC_URL = os.getenv(
    "STARKNET_RPC_URL",
    "https://starknet-sepolia.public.blastapi.io/rpc/v0_7",
)
STARKNET_ACCOUNT_ADDRESS = os.getenv("STARKNET_ACCOUNT_ADDRESS", "")

POLYGON_RPC_URL = os.getenv(
    "POLYGON_RPC_URL", "https://rpc-amoy.polygon.technology"
)
POLYGON_PRIVATE_KEY = os.getenv("POLYGON_PRIVATE_KEY", "")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    val = os.getenv(name, "")
    if not val or val.startswith("REPLACE_"):
        print(f"❌  {name} is not set or is a placeholder. Skipping.", file=sys.stderr)
        return ""
    return val


def _octas_to_apt(octas: int) -> float:
    return octas / 1e8


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    attempts: int = 3,
    delay: float = 2.0,
    **kwargs,
) -> Optional[httpx.Response]:
    for i in range(attempts):
        try:
            resp = await client.get(url, **kwargs)
            if resp.status_code < 500:
                return resp
        except httpx.RequestError as exc:
            print(f"    Request error ({url}): {exc}")
        if i < attempts - 1:
            await asyncio.sleep(delay)
    return None


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    attempts: int = 3,
    delay: float = 2.0,
    **kwargs,
) -> Optional[httpx.Response]:
    for i in range(attempts):
        try:
            resp = await client.post(url, **kwargs)
            if resp.status_code < 500:
                return resp
        except httpx.RequestError as exc:
            print(f"    Request error ({url}): {exc}")
        if i < attempts - 1:
            await asyncio.sleep(delay)
    return None


# ---------------------------------------------------------------------------
# Aptos
# ---------------------------------------------------------------------------

async def fund_aptos(amount_octas: int = 100_000_000) -> bool:
    """Request APT from Aptos devnet faucet."""
    address = _require_env("APTOS_ACCOUNT_ADDRESS")
    if not address:
        return False

    print(f"\n💧  Aptos: funding {address} with {_octas_to_apt(amount_octas):.2f} APT …")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await _post_with_retry(
            client,
            f"{APTOS_FAUCET_URL}/mint",
            params={"address": address, "amount": amount_octas},
        )
        if resp is None:
            print("    ❌  Faucet request failed after retries.")
            return False

        if resp.status_code in (200, 202):
            txns = resp.json() if resp.content else []
            print(f"    ✅  Funded. Txn hashes: {txns}")
            # Brief wait for the tx to land
            await asyncio.sleep(3)
            return True
        else:
            print(f"    ❌  Faucet returned HTTP {resp.status_code}: {resp.text[:200]}")
            return False


async def check_aptos_balance() -> Optional[float]:
    """Return APT balance for the configured Aptos account."""
    address = _require_env("APTOS_ACCOUNT_ADDRESS")
    if not address:
        return None

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await _get_with_retry(
            client,
            f"{APTOS_NODE_URL}/accounts/{address}/resource/0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>",
        )
        if resp and resp.status_code == 200:
            data = resp.json()
            octas = int(data["data"]["coin"]["value"])
            apt = _octas_to_apt(octas)
            print(f"    Aptos balance: {apt:.4f} APT ({octas} octas)")
            return apt
        print("    Could not fetch Aptos balance.")
        return None


# ---------------------------------------------------------------------------
# Starknet Sepolia
# ---------------------------------------------------------------------------

async def fund_starknet() -> bool:
    """
    Request Sepolia ETH via Starknet faucet.

    Starknet does not have a single open API faucet endpoint; we call the
    Alchemy Starknet Sepolia faucet if ALCHEMY_API_KEY is set, otherwise
    we print instructions for the user.
    """
    address = _require_env("STARKNET_ACCOUNT_ADDRESS")
    if not address:
        return False

    alchemy_key = os.getenv("ALCHEMY_API_KEY", "")

    if alchemy_key and not alchemy_key.startswith("REPLACE_"):
        print(f"\n💧  Starknet: requesting Sepolia ETH for {address} via Alchemy faucet …")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await _post_with_retry(
                client,
                "https://sepoliafaucet.com/api/fund",
                json={"address": address, "network": "starknet-sepolia"},
                headers={"Authorization": f"Bearer {alchemy_key}"},
            )
            if resp and resp.status_code in (200, 201, 202):
                print(f"    ✅  Starknet faucet response: {resp.text[:200]}")
                return True
            code = resp.status_code if resp else "N/A"
            print(f"    ❌  Starknet faucet returned HTTP {code}.")
            return False

    # Fallback: manual instructions
    print(
        f"\n⚠️   No Starknet faucet API key available.\n"
        f"     Fund manually at https://faucet.starknet.io/ for address:\n"
        f"     {address}\n"
        f"     Or set ALCHEMY_API_KEY in .env.testnet."
    )
    return False


async def check_starknet_balance() -> Optional[float]:
    """Return ETH balance on Starknet Sepolia (approximate, via JSON-RPC)."""
    address = _require_env("STARKNET_ACCOUNT_ADDRESS")
    if not address:
        return None

    ETH_CONTRACT = "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7"
    payload = {
        "jsonrpc": "2.0",
        "method": "starknet_call",
        "params": [
            {
                "contract_address": ETH_CONTRACT,
                "entry_point_selector": "0x2e4263afad30923c891518314c3c95dbe830a16874e8abc5777a9a20b54c76e",  # balanceOf
                "calldata": [address],
            },
            "latest",
        ],
        "id": 1,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(STARKNET_RPC_URL, json=payload)
            if resp.status_code == 200:
                result = resp.json().get("result", [])
                if result:
                    # result is [low, high] felt252 pair
                    wei = int(result[0], 16) + (int(result[1], 16) << 128)
                    eth = wei / 1e18
                    print(f"    Starknet ETH balance: {eth:.6f} ETH")
                    return eth
        except Exception as exc:  # noqa: BLE001
            print(f"    Balance check error: {exc}")
    print("    Could not fetch Starknet balance.")
    return None


# ---------------------------------------------------------------------------
# Polygon Amoy
# ---------------------------------------------------------------------------

async def fund_polygon() -> bool:
    """
    Request MATIC/POL from Polygon Amoy faucet.
    Uses Alchemy faucet if ALCHEMY_API_KEY is set, else prints instructions.
    """
    alchemy_key = _require_env("ALCHEMY_API_KEY")
    if not alchemy_key:
        print(
            "\n⚠️   ALCHEMY_API_KEY not set — cannot call Polygon Amoy faucet automatically.\n"
            "     Fund at https://faucet.polygon.technology/ (Amoy network)."
        )
        return False

    # Derive the EVM address from the private key if available
    polygon_key = os.getenv("POLYGON_PRIVATE_KEY", "")
    if not polygon_key or polygon_key.startswith("REPLACE_"):
        print("    ❌  POLYGON_PRIVATE_KEY not set. Cannot derive address.", file=sys.stderr)
        return False

    try:
        from eth_account import Account  # type: ignore[import]
        account = Account.from_key(polygon_key)
        address = account.address
    except ImportError:
        print(
            "    ⚠️   eth_account not installed — set POLYGON_ACCOUNT_ADDRESS env var\n"
            "           or install with: pip install eth-account"
        )
        address = os.getenv("POLYGON_ACCOUNT_ADDRESS", "")
        if not address:
            return False

    print(f"\n💧  Polygon Amoy: funding {address} via Alchemy faucet …")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await _post_with_retry(
            client,
            f"https://polygon-amoy.g.alchemy.com/v2/{alchemy_key}",
            json={
                "jsonrpc": "2.0",
                "method": "alchemy_requestTestnetFunds",
                "params": [address],
                "id": 1,
            },
        )
        if resp and resp.status_code == 200:
            body = resp.json()
            if "error" not in body:
                print(f"    ✅  Polygon faucet: {body}")
                return True
            print(f"    ❌  Faucet error: {body['error']}")
            return False
        code = resp.status_code if resp else "N/A"
        print(f"    ❌  Polygon faucet returned HTTP {code}.")
        return False


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

async def main() -> int:
    parser = argparse.ArgumentParser(
        description="CAPP testnet faucet integration for CI."
    )
    parser.add_argument("--aptos", action="store_true", help="Fund Aptos devnet account")
    parser.add_argument("--starknet", action="store_true", help="Fund Starknet Sepolia account")
    parser.add_argument("--polygon", action="store_true", help="Fund Polygon Amoy account")
    parser.add_argument("--all", dest="all_networks", action="store_true", help="Fund all networks")
    parser.add_argument("--check", action="store_true", help="Check balances without funding")
    args = parser.parse_args()

    if not any([args.aptos, args.starknet, args.polygon, args.all_networks, args.check]):
        parser.print_help()
        return 1

    if args.check:
        print("── Balance Check ──────────────────────────────────────────")
        await check_aptos_balance()
        await check_starknet_balance()
        return 0

    success = True
    if args.aptos or args.all_networks:
        ok = await fund_aptos()
        success = success and ok

    if args.starknet or args.all_networks:
        ok = await fund_starknet()
        success = success and ok

    if args.polygon or args.all_networks:
        ok = await fund_polygon()
        success = success and ok

    # Brief wait then print balances
    if args.all_networks:
        print("\n⏳  Waiting 5 s for transactions to land …")
        await asyncio.sleep(5)
        print("\n── Post-fund balances ─────────────────────────────────────")
        await check_aptos_balance()
        await check_starknet_balance()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
