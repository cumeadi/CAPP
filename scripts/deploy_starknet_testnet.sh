#!/usr/bin/env bash
# deploy_starknet_testnet.sh — Deploy CAPP Cairo contracts to Starknet Sepolia testnet
#
# Prerequisites:
#   - starkli installed  (https://book.starkli.rs/installation)
#   - scarb  installed   (https://docs.swmansion.com/scarb/download)
#   - STARKNET_PRIVATE_KEY  set in environment or .env.testnet
#   - STARKNET_ACCOUNT_ADDRESS set in environment or .env.testnet
#   - STARKNET_RPC_URL   set (defaults to public Sepolia endpoint)
#
# Usage:
#   ./scripts/deploy_starknet_testnet.sh [--declare-only]

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
CONTRACTS_DIR="$(cd "$(dirname "$0")/../apps/contracts/starknet" && pwd)"
DECLARE_ONLY="${1:-}"

# Load .env.testnet if not already sourced
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_TESTNET="$SCRIPT_DIR/../.env.testnet"
if [[ -f "$ENV_TESTNET" ]]; then
    # shellcheck disable=SC1090
    set -o allexport
    source "$ENV_TESTNET"
    set +o allexport
fi

STARKNET_RPC_URL="${STARKNET_RPC_URL:-https://starknet-sepolia.public.blastapi.io/rpc/v0_7}"

# ---------------------------------------------------------------------------
# Validate required env vars
# ---------------------------------------------------------------------------
for VAR in STARKNET_PRIVATE_KEY STARKNET_ACCOUNT_ADDRESS; do
    if [[ -z "${!VAR:-}" ]]; then
        echo "❌  $VAR is not set. Exiting." >&2
        exit 1
    fi
done

echo "🚀  Deploying to Starknet Sepolia"
echo "    Account  : ${STARKNET_ACCOUNT_ADDRESS}"
echo "    RPC URL  : ${STARKNET_RPC_URL}"
echo "    Contracts: ${CONTRACTS_DIR}"

# ---------------------------------------------------------------------------
# Export starkli env vars
# ---------------------------------------------------------------------------
export STARKNET_RPC="$STARKNET_RPC_URL"
export STARKNET_ACCOUNT="$STARKNET_ACCOUNT_ADDRESS"

# ---------------------------------------------------------------------------
# Write signer keystore from private key (ephemeral, removed on exit)
# ---------------------------------------------------------------------------
KEYSTORE_DIR="$(mktemp -d)"
KEYSTORE_FILE="$KEYSTORE_DIR/signer.json"
trap 'rm -rf "$KEYSTORE_DIR"' EXIT

echo "🔑  Creating ephemeral keystore..."
starkli signer keystore from-key "$KEYSTORE_FILE" \
    --private-key "$STARKNET_PRIVATE_KEY" \
    --password "" 2>/dev/null

STARKLI_OPTS="--keystore $KEYSTORE_FILE --keystore-password '' --account $STARKNET_ACCOUNT"

# ---------------------------------------------------------------------------
# Build contracts with Scarb
# ---------------------------------------------------------------------------
echo "🔨  Building Cairo contracts..."
(cd "$CONTRACTS_DIR" && scarb build)

# Locate compiled sierra artifact(s)
SIERRA_FILES=("$CONTRACTS_DIR"/target/dev/*.contract_class.json)
if [[ ${#SIERRA_FILES[@]} -eq 0 ]]; then
    echo "❌  No compiled Sierra artifacts found in ${CONTRACTS_DIR}/target/dev/" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Declare & Deploy each contract
# ---------------------------------------------------------------------------
for SIERRA_FILE in "${SIERRA_FILES[@]}"; do
    CONTRACT_NAME="$(basename "$SIERRA_FILE" .contract_class.json)"
    CASM_FILE="${SIERRA_FILE%.contract_class.json}.compiled_contract_class.json"

    echo ""
    echo "──────────────────────────────────────────"
    echo "  Contract : $CONTRACT_NAME"
    echo "──────────────────────────────────────────"

    # --- Declare ---
    echo "📣  Declaring ${CONTRACT_NAME}..."
    # shellcheck disable=SC2086
    CLASS_HASH=$(starkli declare \
        $STARKLI_OPTS \
        --rpc "$STARKNET_RPC_URL" \
        --compiler-version 2.6.2 \
        "$SIERRA_FILE" \
        --casm-file "$CASM_FILE" \
        --watch 2>&1 | grep -oE '0x[0-9a-fA-F]+' | tail -1)

    echo "    Class hash: $CLASS_HASH"

    if [[ "$DECLARE_ONLY" == "--declare-only" ]]; then
        echo "    Skipping deploy (--declare-only flag set)."
        continue
    fi

    # --- Deploy ---
    echo "🚢  Deploying ${CONTRACT_NAME}..."
    # shellcheck disable=SC2086
    DEPLOYED_ADDRESS=$(starkli deploy \
        $STARKLI_OPTS \
        --rpc "$STARKNET_RPC_URL" \
        "$CLASS_HASH" \
        --watch 2>&1 | grep -oE '0x[0-9a-fA-F]+' | tail -1)

    echo "    Deployed at: $DEPLOYED_ADDRESS"
    echo "    Explorer   : https://sepolia.starkscan.co/contract/${DEPLOYED_ADDRESS}"

    # Persist address to a deployment artefact
    DEPLOY_LOG="$SCRIPT_DIR/../.deploy_${CONTRACT_NAME}_sepolia.json"
    cat > "$DEPLOY_LOG" <<JSON
{
  "network": "sepolia",
  "contract": "$CONTRACT_NAME",
  "class_hash": "$CLASS_HASH",
  "address": "$DEPLOYED_ADDRESS",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
    echo "    Artefact   : $DEPLOY_LOG"
done

echo ""
echo "✅  Starknet deployment complete."
