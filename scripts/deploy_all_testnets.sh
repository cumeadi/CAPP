#!/bin/bash
# Master deployment script for all CAPP testnet chains
# Orchestrates deployments to: Aptos, Starknet, Polygon, Base, Arbitrum

set -e

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "   🌐 CAPP Multi-Chain Testnet Deployment Orchestrator"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

# Track deployments
DEPLOYMENTS=()
ERRORS=()

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run a deployment script
deploy_chain() {
    local chain_name=$1
    local script_path=$2

    echo -e "\n${YELLOW}→ Deploying to $chain_name...${NC}"

    if [ ! -f "$script_path" ]; then
        echo -e "${RED}✗ Script not found: $script_path${NC}"
        ERRORS+=("$chain_name: Script not found")
        return 1
    fi

    if bash "$script_path"; then
        echo -e "${GREEN}✓ $chain_name deployment complete${NC}"
        DEPLOYMENTS+=("$chain_name")
        return 0
    else
        echo -e "${RED}✗ $chain_name deployment failed${NC}"
        ERRORS+=("$chain_name: See error above")
        return 1
    fi
}

# Main deployment sequence
echo "📋 Deployment Plan:"
echo "  1. Aptos (Devnet)"
echo "  2. Starknet (Sepolia)"
echo "  3. Polygon (Amoy)"
echo "  4. Base (Sepolia)"
echo "  5. Arbitrum (Sepolia)"
echo ""

read -p "Continue with deployments? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

echo ""
echo "───────────────────────────────────────────────────────────────────────────────"

# Deploy to each chain
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

deploy_chain "Aptos" "$SCRIPT_DIR/deploy_aptos_testnet.sh" || true
deploy_chain "Starknet" "$SCRIPT_DIR/deploy_starknet_testnet.sh" || true
deploy_chain "Polygon" "$SCRIPT_DIR/deploy_polygon_testnet.sh" || true
deploy_chain "Base" "$SCRIPT_DIR/deploy_base_testnet.sh" || true
deploy_chain "Arbitrum" "$SCRIPT_DIR/deploy_arbitrum_testnet.sh" || true

# Summary
echo ""
echo "───────────────────────────────────────────────────────────────────────────────"
echo "📊 Deployment Summary"
echo "───────────────────────────────────────────────────────────────────────────────"

if [ ${#DEPLOYMENTS[@]} -gt 0 ]; then
    echo -e "${GREEN}✓ Successful Deployments:${NC}"
    for chain in "${DEPLOYMENTS[@]}"; do
        echo "  ✓ $chain"
    done
    echo ""
fi

if [ ${#ERRORS[@]} -gt 0 ]; then
    echo -e "${RED}✗ Failed Deployments:${NC}"
    for error in "${ERRORS[@]}"; do
        echo "  ✗ $error"
    done
    echo ""
fi

# Collect all deployment addresses
echo -e "${YELLOW}📝 Collecting Deployment Addresses...${NC}"
OUTPUT_FILE=".env.testnet.deployed"

cat > "$OUTPUT_FILE" <<EOF
# Auto-generated from deploy_all_testnets.sh
# Generated: $(date -u +'%Y-%m-%d %H:%M:%S UTC')
# NEVER commit this file - add to .gitignore

# Contract Addresses by Network
EOF

# Append any .deploy_*.json files to the output
for deploy_file in .deploy_*.json; do
    if [ -f "$deploy_file" ]; then
        echo "" >> "$OUTPUT_FILE"
        echo "# From $deploy_file" >> "$OUTPUT_FILE"
        grep -E '"address"|"chainId"|"network"' "$deploy_file" >> "$OUTPUT_FILE" || true
    fi
done

echo -e "${GREEN}✓ Deployment addresses saved to $OUTPUT_FILE${NC}"
echo ""
echo "───────────────────────────────────────────────────────────────────────────────"
echo "✨ Next Steps:"
echo "   1. Review deployment addresses in individual .deploy_*.json files"
echo "   2. Update contracts/testnet_addresses.json with real addresses"
echo "   3. Verify contracts on block explorers:"
echo "      • Aptos: https://explorer.aptoslabs.com/?network=testnet"
echo "      • Starknet: https://sepolia.starkscan.co/"
echo "      • Polygon: https://amoy.polygonscan.com/"
echo "      • Base: https://sepolia.basescan.org/"
echo "      • Arbitrum: https://sepolia.arbiscan.io/"
echo "   4. Test with: npm run test:testnet"
echo "───────────────────────────────────────────────────────────────────────────────"
echo ""
