# Polygon Volume Inflation Bot

Educational demonstration of DeFi volume manipulation using QuickSwap on Polygon.

## Overview

This bot executes repeated stablecoin swaps (USDC ↔ USDT) on Polygon's QuickSwap DEX to artificially inflate trading volume metrics. It demonstrates how easily volume can be manipulated in DeFi and provides quantitative performance data for EVM-based L2 networks.

### Key Characteristics

- **Network:** Polygon Mainnet (Chain ID: 137)
- **DEX:** QuickSwap (Uniswap V2 fork)
- **Trading Fee:** 0.3% per swap
- **Expected Time:** ~30 minutes for 150 cycles
- **Expected Cost:** ~69% capital loss (trading fees dominate)
- **Volume Multiplier:** ~209x

## Prerequisites

### 1. Python Environment
```bash
python --version  # Requires Python 3.8+
```

### 2. Wallet Setup
- **USDC:** At least $50 (token address: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`)
- **MATIC:** At least $5 for gas fees (~$3 needed for 300 transactions)
- **Private Key:** Export format from MetaMask or similar

### 3. RPC Endpoint (Optional but Recommended)
Free public RPC works but may be slow. Consider:
- [Alchemy](https://www.alchemy.com/) - Free tier: 300M compute units/month
- [Ankr](https://www.ankr.com/) - Public endpoints available
- [Polygon's official RPC](https://polygon-rpc.com/) - Public (rate limited)

## Installation

```bash
# Navigate to polygon-bot directory
cd polygon-bot

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import web3; print(f'web3.py version: {web3.__version__}')"
```

## Configuration

### Environment Variables

```bash
# Required: Your wallet's private key
export PRIVATE_KEY="your_private_key_here"  # Without 0x prefix

# Optional: Custom RPC endpoint
export POLYGON_RPC_URL="https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY"
```

**Security Note:** Never commit private keys to git. Use environment variables or a `.env` file (added to `.gitignore`).

### Optional: Using .env File

```bash
# Create .env file (in polygon-bot directory)
cat > .env << EOF
PRIVATE_KEY=your_private_key_here
POLYGON_RPC_URL=https://polygon-rpc.com
EOF

# Load environment variables
set -a; source .env; set +a
```

## Usage

### Basic Usage

```bash
# Run with default settings (150 cycles, full balance)
python volume_bot.py
```

### Advanced Configuration

Edit `volume_bot.py` and modify the `bot.run()` call:

```python
# Option 1: Custom number of cycles
bot.run(num_cycles=100, use_full_balance=True)

# Option 2: Fixed amount per swap (useful for testing)
bot.run(num_cycles=10, use_full_balance=False, fixed_amount=10.0)

# Option 3: Adjust slippage tolerance (in swap_tokens method)
# Default is 5% - reduce for better prices, increase if swaps fail
```

## How It Works

### 1. Architecture

```
Python Script
    ↓
Web3.py (Ethereum library)
    ↓
Polygon RPC Endpoint
    ↓
QuickSwap Router Contract
    ↓
USDC/USDT Liquidity Pool
```

### 2. Execution Flow

Each cycle consists of two swaps:

```
Cycle N:
  1. Check USDC balance
  2. Swap USDC → USDT (full balance)
  3. Wait 3 seconds
  4. Check USDT balance
  5. Swap USDT → USDC (99% of balance)
  6. Wait 2 seconds
  7. Record statistics
  8. Repeat
```

### 3. Cost Breakdown

**Per Transaction:**
- Gas: ~0.01 MATIC ($0.01)
- Trading fee: 0.3% of swap amount

**For 150 Cycles (300 transactions):**
- Gas fees: ~$3.00
- Trading fees: ~$31.50 (on $50 initial capital)
- **Total loss: ~$34.50 (69% of capital)**

### 4. Why So Expensive?

The 0.3% trading fee compounds geometrically:
```
Swap 1: $50.00 → $49.85 (lost $0.15)
Swap 2: $49.85 → $49.70 (lost $0.15)
...
After 300 swaps: $50.00 → $15.50 (lost $34.50)
```

This is: 50 × (0.997)^300 ≈ $15.50

## Expected Results

### Performance Metrics (150 cycles, $50 capital)

| Metric | Expected Value |
|--------|---------------|
| Execution Time | ~30 minutes |
| Total Volume | $10,476 |
| Volume Multiplier | 209x |
| Capital Remaining | $15.50 (31%) |
| Capital Lost | $34.50 (69%) |
| Gas Fees | $3.00 |
| Trading Fees | $31.50 |
| Transaction Rate | 10 tx/min |
| Success Rate | >95% |

### Output Example

```
🚀 POLYGON VOLUME INFLATION BOT
============================================================

💰 Initial Balances:
   USDC: 50.00
   USDT: 0.00
   MATIC: 5.2340

🔓 Checking token approvals...
   Approval TX: 0xabc123...
✅ Approval successful!

============================================================
Starting 150 cycles...
============================================================

--- Cycle 1/150 ---
💱 Swapping 50.00 USDC -> USDT...
✅ Received 49.85 USDT (Gas: 0.000234 MATIC)
   TX: 0xdef456...
💱 Swapping 49.35 USDT -> USDC...
✅ Received 49.20 USDC (Gas: 0.000234 MATIC)
   TX: 0xghi789...

[... 148 more cycles ...]

============================================================
📊 FINAL REPORT
============================================================

⏱️  Execution Summary:
   Duration: 30.2 minutes (1812 seconds)
   Successful cycles: 150
   Failed cycles: 0
   Total transactions: 300
   Transaction rate: 9.9 tx/min

💰 Capital Analysis:
   Starting USDC: $50.00
   Final USDC: $15.50
   Final USDT: $0.02
   Capital lost: $34.50 (69.0%)
   Capital remaining: $15.50 (31.0%)

📈 Volume Metrics:
   Total volume generated: $10,476.00
   Volume multiplier: 209.5x

⛽ Cost Breakdown:
   Total gas fees: 0.070200 MATIC (≈$3.00)
   Trading fees (estimated): $31.50
   Final MATIC balance: 5.1638

============================================================
✅ Run complete! Generated $10,476.00 volume from $50.00
============================================================

📄 Detailed results saved to: polygon_results_20241120_143022.json
```

## Output Files

### JSON Results File

The bot saves detailed transaction data:

```json
{
  "summary": {
    "network": "Polygon",
    "start_balance": 50.0,
    "final_balance": 15.5,
    "total_volume": 10476.0,
    "transaction_count": 300,
    "successful_cycles": 150,
    "failed_cycles": 0,
    "volume_multiplier": 209.5,
    "capital_loss_percentage": 69.0,
    "execution_time_seconds": 1812.4,
    "tx_rate_per_minute": 9.9
  },
  "transactions": [
    {
      "timestamp": "2024-11-20T14:30:45.123456",
      "tx_hash": "0xabc123...",
      "from_token": "0x2791...",
      "to_token": "0xc213...",
      "amount_in": 50.0,
      "amount_out": 49.85,
      "gas_fee_matic": 0.000234
    },
    ...
  ]
}
```

## Troubleshooting

### Common Issues

**1. "Failed to connect to Polygon RPC"**
```bash
# Try a different RPC endpoint
export POLYGON_RPC_URL="https://polygon-rpc.com"
# Or use Alchemy/Ankr
```

**2. "Insufficient USDC balance"**
```bash
# Check your balance on PolygonScan
# Ensure you have USDC on Polygon (not Ethereum mainnet)
# Bridge USDC: https://wallet.polygon.technology/
```

**3. "Low MATIC balance"**
```bash
# You need ~$5 worth of MATIC for gas fees
# Get MATIC from exchanges or bridge from Ethereum
```

**4. "Swap failed" or "Transaction reverted"**
- **Slippage too low:** Increase slippage tolerance in code
- **Insufficient liquidity:** Try smaller amounts
- **Gas price too low:** RPC will auto-adjust, wait and retry
- **Network congestion:** Wait a few minutes and retry

**5. "Rate limited by RPC"**
- Use a premium RPC endpoint (Alchemy, Infura)
- Add delays between transactions (increase sleep times)

## Performance Optimization

### Not Recommended for Polygon

Unlike Solana, Polygon optimization has limited impact:

1. **Can't reduce delays much** - Need to wait for block confirmations
2. **Priority fees don't help** - Fixed ~2s block time
3. **Trading fees dominate** - 0.3% is unavoidable on QuickSwap

**Better Approach:** Use Solana (see `../solana-bot/`) for:
- 15x faster execution
- 28x lower costs
- 97% capital preservation vs 31%

## Smart Contract Addresses

All contracts verified on [PolygonScan](https://polygonscan.com):

- **USDC:** `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
- **USDT:** `0xc2132D05D31c914a87C6611C10748AEb04B58e8F`
- **QuickSwap Router:** `0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff`

## Security Warnings

⚠️ **Important Security Considerations:**

1. **Use a separate testing wallet** - Don't use your main wallet
2. **Start with small amounts** - Test with $10 before using $50
3. **Verify contract addresses** - Double-check on PolygonScan
4. **Never share private keys** - Environment variables only
5. **Monitor transactions** - Check PolygonScan for confirmations

## Educational Value

### What This Demonstrates

✅ **Volume manipulation is trivial** - $50 → $10K volume
✅ **Trading fees compound quickly** - 0.3% per swap = 69% loss
✅ **EVM L2 performance** - ~10 tx/min on Polygon
✅ **Gas optimization limits** - Can't optimize much further

### Better Metrics to Use

Instead of raw volume, check:
- **Unique active wallets**
- **Volume/TVL ratio**
- **Liquidity depth**
- **Transaction patterns** (circular trading detection)
- **Holder distribution**

## Comparison with Solana

| Metric | Polygon | Solana Optimized | Winner |
|--------|---------|------------------|--------|
| Time | 30 min | 2 min | Solana (15x faster) |
| Cost | 69% loss | 3% loss | Solana (23x cheaper) |
| Capital Kept | 31% | 97% | Solana (3x better) |
| Trading Fee | 0.3% | 0.01% | Solana (30x lower) |
| Gas Fee | $0.01/tx | $0.001/tx | Solana (10x lower) |

**Conclusion:** Solana is dramatically superior for high-frequency trading.

## License

MIT License - Educational use only

## Disclaimer

**Educational purposes only.** This demonstrates DeFi vulnerabilities to promote awareness. Do not use for market manipulation. Always disclose methodology when presenting results.

## Support

For issues or questions:
- Check [../docs/QUICKSTART.md](../docs/QUICKSTART.md)
- Review [../docs/SECURITY.md](../docs/SECURITY.md)
- Open an issue on GitHub

---

**⚠️ Remember:** This is for education, not profit. The high trading fees make this economically unviable. Use Solana for actual testing.
