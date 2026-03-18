# CAPP Testnet Setup Guide

This guide walks you through setting up CAPP for multi-chain testnet exploration on Aptos, Starknet, Polygon, Base, and Arbitrum.

**⏱️ Estimated Setup Time: 15-30 minutes**

---

## Prerequisites

Before you begin, ensure you have:

1. **Node.js & npm** (v18+) - For the frontend wallet app
2. **Python 3.9+** - For the backend API
3. **An Alchemy API Key** - Already provided: `FX7-uiaeRx_TaEyI2HGC0`
4. **Testnet Faucets Access** - Faucets are free and require only a wallet address (see links below)

---

## Step 1: Setup Backend Environment

### 1.1 Copy Testnet Configuration

```bash
cd /Users/chikau/CAPP/CAPP

# The .env.testnet file is already configured
# It contains:
# - Aptos testnet RPC: https://api.testnet.aptoslabs.com/v1
# - Starknet Sepolia RPC: https://starknet-sepolia.public.blastapi.io/rpc/v0_7
# - Polygon Amoy RPC: https://rpc-amoy.polygon.technology
# - Base Sepolia RPC: https://base-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}
# - Arbitrum Sepolia RPC: https://arb-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}
```

### 1.2 Load Testnet Environment Variables

To use testnet configuration, export the Alchemy API key:

```bash
export ALCHEMY_API_KEY=FX7-uiaeRx_TaEyI2HGC0

# Optionally load all testnet vars:
export $(grep -v '^#' /Users/chikau/CAPP/CAPP/.env.testnet | xargs)
```

### 1.3 Start the Backend API

```bash
cd /Users/chikau/CAPP/CAPP

# Start with testnet config
export ALCHEMY_API_KEY=FX7-uiaeRx_TaEyI2HGC0
export DATABASE_URL=sqlite:///./capp.db
python3 -m uvicorn apps.api.app.main:app --reload --port 8000
```

**✅ Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

---

## Step 2: Setup Frontend Environment

### 2.1 Ensure Frontend is Running

The frontend should already be running from earlier setup:

```bash
# If not running, start it:
cd /Users/chikau/CAPP/CAPP/apps/wallet
npm run dev
```

**✅ Expected Output:**
```
- Local:         http://localhost:3000
- Ready in 1.5s
```

### 2.2 Verify Testnet Mode

The Web3Provider now includes Base and Arbitrum testnet chains. Check:

1. Open http://localhost:3000
2. Look for "CONNECT EVM" button → click it
3. You should see these chains:
   - ✅ Ethereum Sepolia
   - ✅ Polygon Amoy
   - ✅ Arbitrum Sepolia
   - ✅ Base Sepolia
   - ✅ Optimism Sepolia

---

## Step 3: Fund Your Testnet Wallets

To test wallet connections and transactions, you need testnet tokens. Use these faucets:

### Ethereum Sepolia
- **Faucet**: https://www.sepoliafaucet.io/
- **Token**: ETH
- **Amount**: 0.05 ETH per request

### Polygon Amoy (formerly Mumbai)
- **Faucet**: https://faucet.polygon.technology/
- **Token**: MATIC
- **Amount**: 0.5 MATIC per request

### Base Sepolia
- **Faucet**: https://sepolia-faucet.allthatnode.com/base
- **Token**: ETH
- **Amount**: 0.1 ETH per request

### Arbitrum Sepolia
- **Faucet**: https://faucet.arbitrum.io/
- **Token**: ETH
- **Amount**: 0.1 ETH per request

### Aptos Testnet
- **Faucet**: https://faucet.testnet.aptoslabs.com/
- **Instructions**:
  1. Install Petra wallet extension: https://petra.app/
  2. Switch to testnet in Petra settings
  3. Paste your account address into the faucet

### Starknet Sepolia
- **Faucet**: https://starknet-faucet.vercel.app/
- **Token**: ETH (on Starknet testnet)
- **Amount**: 0.1 ETH per request

---

## Step 4: Configure Private Keys (Optional - for Testing Transactions)

To test actual transactions (not just balance queries), you need testnet private keys:

```bash
# Add to your .env or shell environment:
export EVM_PRIVATE_KEY=your_testnet_private_key_here       # For Base/Arbitrum
export APTOS_PRIVATE_KEY=your_aptos_testnet_private_key    # For Aptos
export STARKNET_PRIVATE_KEY=your_starknet_testnet_private_key

# Never commit these to git - use a secrets manager in production
```

⚠️ **SECURITY WARNING**: Never use private keys for real funds. Only use testnet private keys with testnet wallets.

---

## Step 5: Test Connectivity

### Test Backend RPC Connectivity

```bash
# Test Aptos testnet
curl http://127.0.0.1:8000/wallet/stats

# Expected response:
# {
#   "total_value_usd": 1234.56,
#   "hot_wallet_balance": 1000.00,
#   "yield_balance": 234.56,
#   "apy": 6.8,
#   "is_sweeping": true,
#   ...
# }
```

### Test Frontend Wallet Connection

1. Open http://localhost:3000
2. Click "CONNECT EVM" button
3. Select one of the testnet chains (e.g., Sepolia)
4. Approve the connection in your wallet
5. You should see your balance displayed

---

## Step 6: Deploy Contracts (Optional)

To test with real smart contracts on testnet:

```bash
cd /Users/chikau/CAPP/CAPP

# Deploy to all testnets at once
bash scripts/deploy_all_testnets.sh

# Or deploy to individual chains:
bash scripts/deploy_aptos_testnet.sh
bash scripts/deploy_polygon_testnet.sh
bash scripts/deploy_base_testnet.sh
bash scripts/deploy_arbitrum_testnet.sh
```

Deployment artifacts will be saved to:
- `.deploy_base_sepolia.json`
- `.deploy_arbitrum_sepolia.json`
- `.deploy_polygon_amoy.json` (if exists)
- `.env.testnet.deployed` (summary of all addresses)

---

## Step 7: Verify Deployments on Block Explorers

After deployment, verify contracts on block explorers:

| Chain | Explorer |
|-------|----------|
| Ethereum Sepolia | https://sepolia.etherscan.io |
| Polygon Amoy | https://amoy.polygonscan.com |
| Base Sepolia | https://sepolia.basescan.org |
| Arbitrum Sepolia | https://sepolia.arbiscan.io |
| Aptos Testnet | https://explorer.aptoslabs.com/?network=testnet |
| Starknet Sepolia | https://sepolia.starkscan.co |

---

## Troubleshooting

### RPC Connection Failed
- **Check**: Alchemy API key is set: `echo $ALCHEMY_API_KEY`
- **Solution**: Re-export the key from Step 1.2
- **Alternative**: Use public RPCs instead (slower but free):
  - Base Sepolia: `https://base-sepolia.blockpi.network/v1/rpc/public`
  - Arbitrum Sepolia: `https://arbitrum-sepolia.blockpi.network/v1/rpc/public`

### Wallet Won't Connect
- **Check**: Frontend loaded at http://localhost:3000
- **Check**: Is testnet mode enabled? (should show Sepolia chains by default)
- **Solution**: Hard refresh the page (Cmd+Shift+R or Ctrl+Shift+R)
- **Solution**: Clear browser cache and localStorage

### Balance Shows $0.00
- **Check**: Have you funded your wallet? Use the faucets above
- **Check**: Are you on the correct testnet?
- **Solution**: Wait 30 seconds for the block to be mined, then refresh

### Backend Won't Start
- **Error**: `ALCHEMY_API_KEY not set`
- **Solution**: Run `export ALCHEMY_API_KEY=FX7-uiaeRx_TaEyI2HGC0`

- **Error**: `Address already in use :8000`
- **Solution**: Kill the old process: `lsof -ti:8000 | xargs kill -9`

---

## Next Steps

1. ✅ **Wallet Testing**: Connect wallets and view balances (See TESTNET_CHECKLIST.md)
2. 🔄 **Routing Tests**: Test the payment routing engine
3. 💰 **Yield Optimization**: Test smart sweep features
4. 🔗 **Cross-Chain**: Test multi-chain interactions

See [TESTNET_CHECKLIST.md](./TESTNET_CHECKLIST.md) for comprehensive test scenarios.

---

## Resources

- **CAPP Documentation**: [README.md](../README.md)
- **Testnet Checklist**: [TESTNET_CHECKLIST.md](./TESTNET_CHECKLIST.md)
- **Aptos Docs**: https://aptos.dev/
- **Starknet Docs**: https://docs.starknet.io/
- **Polygon Docs**: https://polygon.technology/
- **Base Docs**: https://docs.base.org/
- **Arbitrum Docs**: https://docs.arbitrum.io/

---

**Questions or issues?** Open an issue on the CAPP repository.
