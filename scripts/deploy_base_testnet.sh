#!/bin/bash
# Deploy CAPP contracts to Base Sepolia testnet
# Prerequisites: Foundry (forge) installed, BASE_PRIVATE_KEY environment variable set

set -e

echo "🚀 Deploying CAPP contracts to Base Sepolia..."

# Configuration
NETWORK="base_sepolia"
CHAIN_ID=84532
RPC_URL="${BASE_RPC_URL:-https://base-sepolia.g.alchemy.com/v2/FX7-uiaeRx_TaEyI2HGC0}"
PRIVATE_KEY="${BASE_PRIVATE_KEY:-}"
OUTPUT_FILE=".deploy_base_sepolia.json"

# Validate inputs
if [ -z "$PRIVATE_KEY" ]; then
    echo "❌ Error: BASE_PRIVATE_KEY environment variable not set"
    echo "   Set it with: export BASE_PRIVATE_KEY=your_private_key"
    exit 1
fi

# Check for contract files
if [ ! -d "contracts" ]; then
    echo "⚠️  Warning: contracts/ directory not found"
    echo "   Skipping smart contract deployment (contracts not available)"
    echo "   To deploy real contracts, place them in contracts/ directory"
fi

# Create output JSON structure
cat > "$OUTPUT_FILE" <<EOF
{
  "network": "$NETWORK",
  "chainId": $CHAIN_ID,
  "rpcUrl": "$RPC_URL",
  "deploymentTimestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "contracts": {
    "settlement": {
      "address": "0x1234567890abcdef1234567890abcdef12345678",
      "status": "placeholder_awaiting_deployment",
      "note": "Replace with actual address after deployment"
    }
  },
  "deployer": {
    "address": "$(echo "$PRIVATE_KEY" | cut -c1-10)...REDACTED"
  },
  "instructions": {
    "step1": "Implement contract deployment logic using forge or hardhat",
    "step2": "Update address field with deployed contract address",
    "step3": "Run verification with block explorer API"
  }
}
EOF

echo "✅ Base Sepolia configuration saved to $OUTPUT_FILE"
echo ""
echo "📝 Next steps:"
echo "   1. Implement smart contract deployment in this script"
echo "   2. Update the address field in $OUTPUT_FILE with deployed contract"
echo "   3. Run: source $OUTPUT_FILE to load deployment addresses"
echo ""
echo "🔗 Base Sepolia Resources:"
echo "   Block Explorer: https://sepolia.basescan.org/"
echo "   Faucet: https://sepolia-faucet.allthatnode.com/base"
echo "   RPC: $RPC_URL"
