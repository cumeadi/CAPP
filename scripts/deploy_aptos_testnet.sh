#!/usr/bin/env bash
# deploy_aptos_testnet.sh — Deploy CAPP Move modules to Aptos devnet
#
# Prerequisites:
#   - Aptos CLI installed (https://aptos.dev/tools/aptos-cli/install-cli)
#   - APTOS_PRIVATE_KEY set in environment or .env.testnet
#   - APTOS_ACCOUNT_ADDRESS set in environment or .env.testnet
#
# Usage:
#   ./scripts/deploy_aptos_testnet.sh [--network devnet|testnet] [--fund]

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
NETWORK="${APTOS_NETWORK:-devnet}"
MOVE_DIR="$(cd "$(dirname "$0")/../packages/blockchain/move" && pwd)"
FUND="${1:-}"

# Load .env.testnet if it exists and vars are not already set
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_TESTNET="$SCRIPT_DIR/../.env.testnet"
if [[ -f "$ENV_TESTNET" ]]; then
    # shellcheck disable=SC1090
    set -o allexport
    source "$ENV_TESTNET"
    set +o allexport
fi

# ---------------------------------------------------------------------------
# Validate required env vars
# ---------------------------------------------------------------------------
if [[ -z "${APTOS_PRIVATE_KEY:-}" ]]; then
    echo "❌  APTOS_PRIVATE_KEY is not set. Exiting." >&2
    exit 1
fi

if [[ -z "${APTOS_ACCOUNT_ADDRESS:-}" ]]; then
    echo "❌  APTOS_ACCOUNT_ADDRESS is not set. Exiting." >&2
    exit 1
fi

echo "🚀  Deploying to Aptos ${NETWORK}"
echo "    Account : ${APTOS_ACCOUNT_ADDRESS}"
echo "    Move dir: ${MOVE_DIR}"

# ---------------------------------------------------------------------------
# Initialise Aptos CLI profile (idempotent)
# ---------------------------------------------------------------------------
aptos init \
    --profile capp-testnet \
    --network "$NETWORK" \
    --private-key "$APTOS_PRIVATE_KEY" \
    --skip-faucet \
    --assume-yes 2>/dev/null || true

# ---------------------------------------------------------------------------
# Optional: fund account from faucet (devnet only)
# ---------------------------------------------------------------------------
if [[ "$FUND" == "--fund" || "${CI_FAUCET_FUND:-false}" == "true" ]]; then
    if [[ "$NETWORK" == "devnet" || "$NETWORK" == "testnet" ]]; then
        echo "💧  Requesting faucet funds for ${APTOS_ACCOUNT_ADDRESS}..."
        aptos account fund-with-faucet \
            --profile capp-testnet \
            --account "$APTOS_ACCOUNT_ADDRESS" \
            --amount 100000000 || {
            echo "⚠️   Faucet request failed (non-fatal)."
        }
    else
        echo "⚠️   Faucet only available on devnet/testnet — skipping."
    fi
fi

# ---------------------------------------------------------------------------
# Compile Move modules
# ---------------------------------------------------------------------------
echo "🔨  Compiling Move modules..."
aptos move compile \
    --package-dir "$MOVE_DIR" \
    --named-addresses capp="$APTOS_ACCOUNT_ADDRESS"

# ---------------------------------------------------------------------------
# Run Move tests before deploying
# ---------------------------------------------------------------------------
echo "🧪  Running Move unit tests..."
aptos move test \
    --package-dir "$MOVE_DIR" \
    --named-addresses capp="$APTOS_ACCOUNT_ADDRESS"

# ---------------------------------------------------------------------------
# Publish (deploy) modules
# ---------------------------------------------------------------------------
echo "📦  Publishing Move modules..."
aptos move publish \
    --profile capp-testnet \
    --package-dir "$MOVE_DIR" \
    --named-addresses capp="$APTOS_ACCOUNT_ADDRESS" \
    --assume-yes

echo "✅  Aptos deployment complete."
echo "    View on explorer: https://explorer.aptoslabs.com/account/${APTOS_ACCOUNT_ADDRESS}?network=${NETWORK}"
