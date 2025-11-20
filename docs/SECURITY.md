# Security Best Practices

Comprehensive security guide for blockchain bot operations.

## ⚠️ Critical Security Warnings

### Never Do These Things

❌ **Never commit private keys to git**
❌ **Never share private keys with anyone**
❌ **Never use main wallet for testing**
❌ **Never skip transaction verification**
❌ **Never trust unverified contract addresses**
❌ **Never use hardcoded private keys**
❌ **Never disable SSL/TLS verification**
❌ **Never run with root privileges**

---

## Private Key Management

### ✅ Best Practices

**1. Use Environment Variables**

```bash
# Good: Environment variable
export PRIVATE_KEY="your_key_here"
python volume_bot.py

# Bad: Hardcoded in script
private_key = "0xabc123..."  # NEVER DO THIS!
```

**2. Use .env Files (with .gitignore)**

```bash
# Create .env file
cat > .env << EOF
PRIVATE_KEY=your_key_here
SOLANA_RPC_URL=your_rpc_url
EOF

# Add to .gitignore
echo ".env" >> .gitignore

# Load in script
from dotenv import load_dotenv
load_dotenv()
private_key = os.getenv('PRIVATE_KEY')
```

**3. Use Separate Testing Wallets**

```
Main Wallet (Hardware)
├─ $10,000+ in assets
└─ Never export private key

Testing Wallet (Software)
├─ $100-500 max
└─ Export private key for bots
```

**4. Use Hardware Wallets for Main Funds**

- Ledger, Trezor for main storage
- Software wallet for testing only
- Never connect hardware wallet to scripts

### ❌ What Not to Do

```python
# TERRIBLE - Hardcoded key in code
private_key = "0xabc123def456..."
bot = Bot(private_key)

# TERRIBLE - Key in git
# .env file committed to repository

# TERRIBLE - Key in plaintext file
with open('key.txt') as f:
    private_key = f.read()

# TERRIBLE - Key in logs
print(f"Using private key: {private_key}")
```

### 🔒 Key Storage Options

| Method | Security | Convenience | Best For |
|--------|----------|-------------|----------|
| **Hardware Wallet** | ⭐⭐⭐⭐⭐ | ⭐ | Main funds |
| **Environment Variable** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Development |
| **.env File** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Local dev |
| **Encrypted File** | ⭐⭐⭐ | ⭐⭐ | Production |
| **Cloud Secrets** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Cloud deployment |
| **Plaintext File** | ⭐ | ⭐⭐⭐⭐⭐ | NEVER |
| **Hardcoded** | ⭐ | ⭐⭐⭐⭐⭐ | NEVER |

---

## Network Security

### RPC Endpoint Security

**1. Use HTTPS Only**

```python
# Good: HTTPS
rpc_url = "https://api.mainnet-beta.solana.com"

# Bad: HTTP (man-in-the-middle attacks)
rpc_url = "http://api.mainnet-beta.solana.com"
```

**2. Verify RPC Provider**

```python
# Good: Official providers
TRUSTED_PROVIDERS = [
    "api.mainnet-beta.solana.com",
    "mainnet.helius-rpc.com",
    "solana-mainnet.g.alchemy.com",
    "polygon-rpc.com",
    "polygon-mainnet.g.alchemy.com",
]

def validate_rpc_url(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https':
        raise ValueError("RPC must use HTTPS")
    if not any(trusted in parsed.netloc for trusted in TRUSTED_PROVIDERS):
        print("⚠️  Warning: Untrusted RPC provider")
```

**3. Rate Limiting Protection**

```python
# Implement backoff on rate limits
import time
from functools import wraps

def rate_limit_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except RateLimitError:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                else:
                    raise
    return wrapper
```

### API Key Security

**Don't expose API keys:**

```bash
# Bad: API key in URL (visible in logs)
https://mainnet.helius-rpc.com/?api-key=EXPOSED_KEY

# Good: Use environment variable
export HELIUS_API_KEY="your_key"

# In code:
api_key = os.getenv('HELIUS_API_KEY')
rpc_url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
```

---

## Transaction Security

### Pre-Transaction Checks

**Always verify before signing:**

```python
def verify_transaction(tx_data):
    """Verify transaction before signing."""

    # 1. Check destination address
    if tx_data['to'] not in KNOWN_CONTRACTS:
        print("⚠️  Warning: Unknown contract address")
        confirm = input("Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            raise ValueError("Transaction cancelled by user")

    # 2. Check amount
    max_amount = 1000  # $1000 max
    if tx_data['amount'] > max_amount:
        raise ValueError(f"Amount exceeds maximum: {max_amount}")

    # 3. Check gas price
    if tx_data['gasPrice'] > Web3.to_wei(100, 'gwei'):
        print("⚠️  Warning: High gas price!")

    # 4. Verify token addresses
    if tx_data['token'] not in VERIFIED_TOKENS:
        raise ValueError("Unverified token address")

    return True
```

### Contract Address Verification

**Polygon:**
```python
# Verify on PolygonScan FIRST
VERIFIED_ADDRESSES = {
    'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
    'QuickSwap': '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff',
}

def check_address(name, address):
    """Verify contract address matches known good address."""
    expected = VERIFIED_ADDRESSES.get(name)
    if expected and address.lower() != expected.lower():
        raise ValueError(f"Invalid {name} address!")
```

**Solana:**
```python
# Verify on Solscan FIRST
VERIFIED_MINTS = {
    'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    'USDT': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',
}

def check_mint(name, mint):
    """Verify token mint matches known good mint."""
    expected = VERIFIED_MINTS.get(name)
    if expected and str(mint) != expected:
        raise ValueError(f"Invalid {name} mint!")
```

### Slippage Protection

```python
# Set reasonable slippage limits
SLIPPAGE_LIMITS = {
    'stablecoin': 1.0,    # 1% max for stablecoin swaps
    'volatile': 5.0,       # 5% max for volatile assets
    'illiquid': 10.0,      # 10% max for illiquid assets
}

def check_slippage(expected, received, asset_type='stablecoin'):
    """Verify slippage is within acceptable range."""
    slippage = abs(expected - received) / expected * 100

    max_slippage = SLIPPAGE_LIMITS[asset_type]
    if slippage > max_slippage:
        raise ValueError(f"Slippage too high: {slippage:.2f}%")

    return True
```

---

## Operational Security

### Wallet Setup

**1. Create Dedicated Test Wallet**

```bash
# Solana: Create new wallet
solana-keygen new --outfile test-wallet.json

# Move to secure location
mv test-wallet.json ~/.config/solana/test-wallet.json
chmod 600 ~/.config/solana/test-wallet.json

# Ethereum/Polygon: Use MetaMask
# Create new account, label as "Testing Bot"
```

**2. Fund Appropriately**

```
Test Wallet Funding:
├─ $50-100 USDC (for testing)
├─ $5-10 gas token (SOL/MATIC)
└─ Nothing else!

Never fund with:
❌ Large amounts (>$500)
❌ NFTs
❌ Other valuable tokens
❌ Funds from main wallet directly
```

**3. Monitor Continuously**

```python
# Add balance checks
def monitor_balances(bot):
    """Alert if balance drops unexpectedly."""
    initial_balance = bot.get_balance()

    while bot.running:
        current_balance = bot.get_balance()
        loss = initial_balance - current_balance

        # Alert on unexpected loss
        if loss > initial_balance * 0.5:  # >50% loss
            print("🚨 ALERT: Unexpected balance loss!")
            bot.stop()
            send_alert("Balance dropped by 50%+")

        time.sleep(60)  # Check every minute
```

### Error Handling

**Don't expose sensitive info in errors:**

```python
# Bad: Exposes private key
try:
    bot = Bot(private_key)
except Exception as e:
    print(f"Error with key {private_key}: {e}")  # NEVER!

# Good: Safe error messages
try:
    bot = Bot(private_key)
except ValueError as e:
    print(f"Invalid private key format")
except ConnectionError as e:
    print(f"Failed to connect to RPC")
except Exception as e:
    print(f"Initialization error: {type(e).__name__}")
```

### Logging Security

**Safe logging practices:**

```python
import logging

# Configure safe logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Good: Safe logs
logging.info("Transaction sent")
logging.info(f"Swap complete: {amount} USDC")

# Bad: Exposes sensitive data
logging.info(f"Using private key: {private_key}")  # NEVER!
logging.info(f"RPC API key: {api_key}")  # NEVER!
```

---

## Code Security

### Input Validation

```python
def validate_inputs(num_cycles, amount):
    """Validate user inputs."""

    # Check num_cycles
    if not isinstance(num_cycles, int):
        raise TypeError("num_cycles must be integer")
    if num_cycles < 1 or num_cycles > 1000:
        raise ValueError("num_cycles must be 1-1000")

    # Check amount
    if not isinstance(amount, (int, float)):
        raise TypeError("amount must be numeric")
    if amount < 0:
        raise ValueError("amount must be positive")
    if amount > 10000:
        print("⚠️  Warning: Large amount")
        confirm = input("Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            raise ValueError("Cancelled by user")

    return True
```

### Dependency Security

**Keep dependencies updated:**

```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies
pip install --upgrade web3 solana solders

# Pin versions in production
# requirements.txt:
web3==6.11.3  # Pinned version
solana==0.30.2
```

**Verify package integrity:**

```bash
# Check package hashes
pip install --require-hashes -r requirements.txt

# Use trusted package index only
pip install --index-url https://pypi.org/simple web3
```

### Code Review Checklist

- [ ] No hardcoded private keys
- [ ] No hardcoded API keys
- [ ] No sensitive data in logs
- [ ] Input validation on all user inputs
- [ ] Contract addresses verified
- [ ] Error messages don't expose keys
- [ ] HTTPS for all network connections
- [ ] Rate limiting implemented
- [ ] Transaction verification before signing
- [ ] Slippage limits set
- [ ] Maximum transaction amount enforced

---

## Environment Security

### Development Environment

```bash
# 1. Separate environments
export ENV=development
export PRIVATE_KEY="test_wallet_key"
export AMOUNT_LIMIT=100

# 2. Production (different keys!)
export ENV=production
export PRIVATE_KEY="prod_wallet_key"
export AMOUNT_LIMIT=1000
```

### File Permissions

```bash
# Secure sensitive files
chmod 600 .env
chmod 600 private_key.txt
chmod 700 ~/.config/solana/

# Check permissions
ls -la .env
# Should show: -rw------- (owner read/write only)
```

### Git Security

**Essential .gitignore entries:**

```gitignore
# Private keys
*.key
*.json
private_keys.txt
test-wallet.json

# Environment files
.env
.env.local
.env.*.local

# Logs (may contain sensitive data)
*.log
logs/

# Results (may contain wallet addresses)
*_results_*.json
```

**Check for leaked secrets:**

```bash
# Before committing
git diff --cached

# Scan for secrets
git secrets --scan
# or
gitleaks detect
```

---

## Emergency Procedures

### If Private Key is Compromised

**Immediate Actions:**

1. **Transfer funds out immediately**
```bash
# Solana: Transfer all assets
solana transfer <NEW_WALLET> ALL --from <COMPROMISED_WALLET>

# Polygon: Use MetaMask to transfer
# Send all tokens to new wallet
```

2. **Revoke all approvals**
```python
# Polygon: Revoke token approvals
def revoke_approvals(token_address):
    token = w3.eth.contract(address=token_address, abi=ERC20_ABI)
    tx = token.functions.approve(ROUTER, 0).build_transaction({...})
    # Sign and send
```

3. **Document the incident**
```
When: [timestamp]
What: Private key compromised
How: [git commit / screenshot / etc]
Impact: [$X in wallet at time]
Actions: Funds transferred to [new wallet]
```

4. **Rotate all credentials**
- Generate new wallet
- Update .env files
- Change RPC API keys
- Review all access logs

### If Unauthorized Transaction Detected

1. **Stop all bots immediately**
2. **Check transaction on block explorer**
3. **If malicious, transfer remaining funds**
4. **Analyze how it happened**
5. **Implement additional security**

### Emergency Contacts

```
Emergency Checklist:
├─ [ ] Stop all running bots
├─ [ ] Transfer funds to safe wallet
├─ [ ] Revoke all token approvals
├─ [ ] Rotate all API keys
├─ [ ] Review git history for leaks
├─ [ ] Check server access logs
└─ [ ] Implement additional security
```

---

## Security Testing

### Pre-Deployment Checklist

Before running with real funds:

- [ ] Tested with testnet (devnet/mumbai)
- [ ] Tested with minimal amounts ($1-5)
- [ ] Verified all contract addresses
- [ ] Checked transaction on block explorer
- [ ] Reviewed code for security issues
- [ ] No private keys in code/git
- [ ] Environment variables configured
- [ ] Slippage limits set appropriately
- [ ] Maximum amounts configured
- [ ] Error handling tested
- [ ] Logging reviewed (no sensitive data)

### Security Audit Commands

```bash
# 1. Check for hardcoded secrets
grep -r "private_key\s*=\s*['\"]" .
grep -r "0x[a-fA-F0-9]{64}" .
grep -r "api[_-]key\s*=\s*['\"]" .

# 2. Check file permissions
find . -name "*.env" -ls
find . -name "*.key" -ls
find . -name "*private*" -ls

# 3. Check git history
git log --all --full-history --source --pretty=format: --name-only | \
  grep -E "key|private|secret"

# 4. Check for vulnerabilities
safety check
bandit -r .
```

---

## Compliance & Ethics

### Legal Considerations

**Understand the law:**

✅ **Generally Legal:**
- Trading your own funds
- Using public DEXes
- Educational research
- Transparent reporting

❌ **Potentially Illegal:**
- Misleading investors
- Market manipulation for profit
- Pump and dump schemes
- Wash trading for tax evasion

### Ethical Use

**Acceptable:**
- Educational demonstrations (with disclosure)
- Research purposes (with transparency)
- Testing and development (small amounts)
- Proof of concept (documented)

**Unacceptable:**
- Manipulating project rankings
- Deceiving investors
- False volume reporting
- Market manipulation for personal gain

### Disclosure Template

```markdown
## Disclosure

This is an educational demonstration of DeFi volume inflation
conducted for research purposes.

- Purpose: Educational / Research
- Methodology: Repeated USDC/USDT swaps
- Funding: Personal funds only
- Transparency: All transaction hashes provided
- Disclosure: This is artificial volume, not organic trading

Transaction hashes:
- 0xabc...
- 0xdef...
[... all transactions ...]
```

---

## Additional Resources

### Security Tools

- **Hardhat**: Smart contract testing
- **Slither**: Solidity static analyzer
- **MythX**: Security analysis platform
- **OpenZeppelin**: Secure contract library
- **Git-secrets**: Prevent committing secrets
- **Safety**: Python dependency checker
- **Bandit**: Python security linter

### Best Practices Guides

- [Solana Security Best Practices](https://docs.solana.com/developing/programming-model/security)
- [Ethereum Security](https://ethereum.org/en/developers/docs/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)

### Incident Response

- Document everything
- Preserve evidence (logs, transactions)
- Analyze root cause
- Implement fixes
- Test thoroughly
- Update documentation

---

## Summary

### Security Priorities

1. **Private Key Security** (Critical)
   - Never commit to git
   - Use environment variables
   - Separate testing wallets
   - Hardware wallets for main funds

2. **Transaction Security** (High)
   - Verify addresses
   - Check amounts
   - Set slippage limits
   - Monitor continuously

3. **Network Security** (Medium)
   - HTTPS only
   - Trusted RPC providers
   - Rate limiting
   - API key protection

4. **Operational Security** (Medium)
   - Input validation
   - Error handling
   - Safe logging
   - Regular audits

### Remember

**Security is not optional. A single mistake can lead to total loss of funds.**

**Better safe than sorry. Always err on the side of caution.**

**Security is a process, not a product. Continuously improve and stay vigilant.**

---

**🔒 Stay safe, stay secure!**
