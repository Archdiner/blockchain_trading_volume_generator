# Solana Volume Inflation Bot (Original)

Educational demonstration of DeFi volume manipulation using Jupiter aggregator on Solana.

## Overview

This bot executes repeated stablecoin swaps (USDC ↔ USDT) on Solana using the Jupiter aggregator to artificially inflate trading volume metrics. Compared to Polygon, it's **3x faster** and preserves **97% of capital** vs only 31%.

### Key Characteristics

- **Network:** Solana Mainnet
- **Aggregator:** Jupiter API v6
- **DEXes Used:** Orca, Raydium, Serum (via Jupiter routing)
- **Trading Fee:** 0.01% (Orca Whirlpools for stablecoins)
- **Expected Time:** ~10 minutes for 150 cycles
- **Expected Cost:** ~2.4% capital loss (vs 69% on Polygon!)
- **Volume Multiplier:** ~209x

## Why Solana is Better

| Feature | Polygon | Solana | Advantage |
|---------|---------|---------|-----------|
| Trading Fee | 0.3% | 0.01% | **30x cheaper** |
| Execution Time | 30 min | 10 min | **3x faster** |
| Capital Kept | 31% | 97.6% | **3x better** |
| Gas per TX | $0.01 | $0.0003 | **33x cheaper** |
| Block Time | 2s | 0.4s | **5x faster** |
| Approvals Needed | Yes (2 tx) | No | **Simpler** |

## Prerequisites

### 1. Python Environment
```bash
python --version  # Requires Python 3.8+
```

### 2. Wallet Setup
- **USDC (SPL):** At least $50 (mint: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)
- **SOL:** At least 0.01 SOL (~$1.50) for gas fees
- **Private Key:** Export from Phantom/Solflare wallet

⚠️ **Important:** Make sure you have USDC on **Solana** (not Ethereum or Polygon). Bridge at [portal.bridge.com](https://www.portalbridge.com/)

### 3. RPC Endpoint (Optional but Recommended)

Free public RPC works but may be slow. Consider:
- [Helius](https://www.helius.dev/) - Free: 100k req/day, much faster
- [Alchemy](https://www.alchemy.com/) - Free tier available
- [QuickNode](https://www.quicknode.com/) - Premium performance

## Installation

```bash
# Navigate to solana-bot directory
cd solana-bot

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import solana; print(f'solana-py version: {solana.__version__}')"
```

## Configuration

### Getting Your Private Key

**From Phantom Wallet:**
1. Settings → Security & Privacy → Export Private Key
2. Enter password
3. Copy the base58 string

**From Solflare:**
1. Settings → Export Private Key
2. Copy the array format: `[1,2,3,...]`

### Environment Variables

```bash
# Required: Your wallet's private key
export PRIVATE_KEY="your_private_key_here"  # Base58 or array format

# Optional: Custom RPC endpoint (recommended!)
export SOLANA_RPC_URL="https://mainnet.helius-rpc.com/?api-key=YOUR_KEY"
```

### Using .env File (Recommended)

```bash
# Create .env file
cat > .env << EOF
PRIVATE_KEY=your_base58_or_array_key_here
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
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

# Option 2: Fixed amount per swap (for testing)
bot.run(num_cycles=10, use_full_balance=False, fixed_amount=10.0)

# Option 3: Adjust slippage (in swap_tokens_jupiter method)
# Default is 50 bps (0.5%) - reduce for better prices
```

## How It Works

### 1. Architecture

```
Python Script
    ↓
solana-py + Jupiter API
    ↓
Solana RPC Endpoint
    ↓
Jupiter Aggregator
    ↓
Multiple DEXes (Orca, Raydium, etc.)
    ↓
Best USDC/USDT Route
```

### 2. Jupiter Advantages

Unlike Polygon (single DEX), Jupiter checks:
- **Orca Whirlpools** (0.01% fee, concentrated liquidity)
- **Raydium** (0.25% fee, high volume)
- **Serum** (orderbook, variable fees)
- And 10+ other DEXes

Result: Best price + lowest fees automatically

### 3. Execution Flow

Each cycle consists of two swaps:

```
Cycle N:
  1. Check USDC balance
  2. Query Jupiter for best USDC→USDT route
  3. Execute swap (no approval needed!)
  4. Wait 2 seconds
  5. Check USDT balance
  6. Query Jupiter for best USDT→USDC route
  7. Execute swap
  8. Wait 1 second
  9. Record statistics
  10. Repeat
```

### 4. Cost Breakdown

**Per Transaction:**
- Base gas: 0.000005 SOL ($0.00075)
- Trading fee: 0.01% of swap amount (via Orca)

**For 150 Cycles (300 transactions):**
- Gas fees: ~$0.08
- Trading fees: ~$1.14 (on $50 initial capital)
- **Total loss: ~$1.22 (2.4% of capital)**

### 5. Why So Cheap?

Compared to Polygon's 0.3% fee:
```
Polygon: 50 × (0.997)^300 ≈ $15.50 (69% loss)
Solana:  50 × (0.9999)^300 ≈ $48.78 (2.4% loss)
```

The 30x lower fee makes ALL the difference!

## Expected Results

### Performance Metrics (150 cycles, $50 capital)

| Metric | Expected Value |
|--------|---------------|
| Execution Time | ~10 minutes |
| Total Volume | $10,476 |
| Volume Multiplier | 209x |
| Capital Remaining | $48.78 (97.6%) |
| Capital Lost | $1.22 (2.4%) |
| Gas Fees | $0.08 |
| Trading Fees | $1.14 |
| Transaction Rate | 30 tx/min |
| Success Rate | >98% |

### Output Example

```
🚀 SOLANA VOLUME INFLATION BOT (Original)
============================================================

💰 Initial Balances:
   USDC: 50.00
   USDT: 0.00
   SOL: 0.0523

✅ No token approvals needed on Solana (SPL token advantage)

============================================================
Starting 150 cycles...
============================================================

--- Cycle 1/150 ---
💱 Swapping 50.00 USDC -> USDT...
✅ Received 49.995 USDT (Fee: 0.000005 SOL)
   TX: 5kXYZ...
💱 Swapping 49.49 USDT -> USDC...
✅ Received 49.49 USDC (Fee: 0.000005 SOL)
   TX: 3mABC...

[... 148 more cycles ...]

📊 Progress: 150 cycles, 300 tx, 30.2 tx/min

============================================================
📊 FINAL REPORT
============================================================

⏱️  Execution Summary:
   Duration: 9.9 minutes (594 seconds)
   Successful cycles: 150
   Failed cycles: 0
   Total transactions: 300
   Transaction rate: 30.3 tx/min

💰 Capital Analysis:
   Starting USDC: $50.00
   Final USDC: $48.78
   Final USDT: $0.01
   Capital lost: $1.22 (2.4%)
   Capital remaining: $48.78 (97.6%)

📈 Volume Metrics:
   Total volume generated: $10,476.00
   Volume multiplier: 209.5x

⛽ Cost Breakdown:
   Total gas fees: 0.001500 SOL (≈$0.08)
   Trading fees (estimated): $1.14
   Final SOL balance: 0.0508

============================================================
✅ Run complete! Generated $10,476.00 volume from $50.00
============================================================

📄 Detailed results saved to: solana_results_20241120_143022.json
```

## Output Files

### JSON Results File

```json
{
  "summary": {
    "network": "Solana",
    "version": "Original",
    "start_balance": 50.0,
    "final_balance": 48.78,
    "total_volume": 10476.0,
    "transaction_count": 300,
    "successful_cycles": 150,
    "failed_cycles": 0,
    "volume_multiplier": 209.5,
    "capital_loss_percentage": 2.4,
    "execution_time_seconds": 594.2,
    "tx_rate_per_minute": 30.3
  },
  "transactions": [...]
}
```

## Troubleshooting

### Common Issues

**1. "Invalid private key format"**
```bash
# Try different formats:
# Base58 (from Phantom):
export PRIVATE_KEY="5Kb8kLf4h..."

# Array format (from Solflare):
export PRIVATE_KEY='[174,47,154,...]'
```

**2. "Insufficient USDC balance"**
- Check you have **Solana** USDC (not Ethereum/Polygon USDC)
- View on [Solscan](https://solscan.io/)
- Bridge at [portal.bridge.com](https://www.portalbridge.com/)

**3. "Jupiter API error"**
- Public RPC may be rate-limited
- Use Helius or Alchemy (free tier)
- Add small delays between requests

**4. "Transaction confirmation timeout"**
- Transaction likely succeeded, check Solscan
- Network congestion (rare on Solana)
- Try premium RPC endpoint

**5. "Low SOL balance"**
- Need at least 0.01 SOL
- Get from exchanges (Coinbase, Binance, etc.)
- Very cheap: $1.50 worth lasts 300+ transactions

## Performance Comparison

### vs Polygon

| Metric | Polygon | Solana (Original) | Improvement |
|--------|---------|-------------------|-------------|
| Time | 30 min | 10 min | **3x faster** |
| Cost | $34.50 (69%) | $1.22 (2.4%) | **28x cheaper** |
| Capital Kept | $15.50 (31%) | $48.78 (97.6%) | **3x better** |
| TX Rate | 10 tx/min | 30 tx/min | **3x faster** |
| Gas/TX | $0.01 | $0.00025 | **40x cheaper** |
| Trading Fee | 0.3% | 0.01% | **30x cheaper** |

### vs Solana Optimized

See `../solana-bot-optimized/` for further improvements:
- **5x faster execution** (10 min → 2 min)
- Priority fees for instant confirmation
- Retry logic for reliability
- Fast RPC support

## Smart Contract Addresses

All verified on [Solscan](https://solscan.io):

- **USDC Mint:** `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- **USDT Mint:** `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB`
- **Jupiter API:** `https://quote-api.jup.ag/v6`

## Security Warnings

⚠️ **Important Security Considerations:**

1. **Use a separate testing wallet** - Don't use your main wallet
2. **Start with small amounts** - Test with $10 first
3. **Verify token mints** - Double-check on Solscan
4. **Never share private keys** - Environment variables only
5. **Monitor transactions** - Check Solscan for confirmations
6. **Beware of fake tokens** - Only use verified USDC/USDT

## Educational Value

### What This Demonstrates

✅ **Volume manipulation is trivial** - $50 → $10K volume
✅ **Network choice matters dramatically** - 28x cost difference
✅ **Jupiter routing is powerful** - Finds best prices automatically
✅ **Solana is fast and cheap** - 0.4s blocks, $0.0003 gas

### Why Solana Wins

1. **Lower trading fees** - 0.01% vs 0.3% (30x difference)
2. **Faster blocks** - 0.4s vs 2s (5x difference)
3. **Cheaper gas** - $0.0003 vs $0.01 (33x difference)
4. **No approvals** - Saves 2 transactions and time
5. **Better DEXes** - Concentrated liquidity pools (Orca)

### Better Metrics to Use

Instead of raw volume, check:
- **Unique active wallets** - Wash trading uses few wallets
- **Volume/TVL ratio** - Should be reasonable (not 100x)
- **Liquidity depth** - Can the volume be sustained?
- **Transaction patterns** - Look for circular trading
- **Holder distribution** - Concentrated = suspicious

## Next Steps

### Try the Optimized Version

See `../solana-bot-optimized/` for:
- **2 minute execution** (5x faster than this version)
- Priority fees (faster confirmations)
- Retry logic (higher reliability)
- Fast RPC support (Helius integration)

**Only adds $0.30 in priority fees but saves 8 minutes!**

## License

MIT License - Educational use only

## Disclaimer

**Educational purposes only.** This demonstrates DeFi vulnerabilities to promote awareness. Do not use for market manipulation. Always disclose methodology when presenting results.

## Support

For issues or questions:
- Check [../docs/QUICKSTART.md](../docs/QUICKSTART.md)
- Review [../docs/COMPARISON.md](../docs/COMPARISON.md)
- Review [../docs/OPTIMIZED_GUIDE.md](../docs/OPTIMIZED_GUIDE.md)
- Open an issue on GitHub

---

**💡 Key Takeaway:** Solana's architecture (fast blocks + low fees + no approvals) makes it ideal for high-frequency operations. This isn't just about crypto trading - it applies to any high-throughput application.
