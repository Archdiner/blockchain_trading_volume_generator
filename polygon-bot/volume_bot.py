#!/usr/bin/env python3
"""
Polygon Volume Inflation Bot
Educational demonstration of DeFi volume manipulation via repeated stablecoin swaps.

This bot uses QuickSwap (Uniswap V2 fork) on Polygon to execute USDC<->USDT swaps,
generating significant apparent volume from minimal capital.

WARNING: Educational purposes only. High trading fees (0.3%) cause significant capital loss.
"""

import os
import sys
import time
import json
from decimal import Decimal
from datetime import datetime
from typing import Optional, Tuple

from web3 import Web3
from eth_account import Account
from web3.exceptions import ContractLogicError


# Contract addresses on Polygon Mainnet
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDT_ADDRESS = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
QUICKSWAP_ROUTER = "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"

# ERC20 ABI (minimal - balanceOf, approve, allowance)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

# QuickSwap Router ABI (Uniswap V2 compatible)
ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class PolygonVolumeBot:
    """
    Polygon-based volume inflation bot using QuickSwap DEX.

    Executes repeated USDC<->USDT swaps to generate artificial trading volume.
    Tracks metrics including gas fees, capital loss, and volume multiplier.
    """

    def __init__(self, private_key: str, rpc_url: Optional[str] = None):
        """
        Initialize the bot with wallet and RPC connection.

        Args:
            private_key: Ethereum private key (with or without 0x prefix)
            rpc_url: Polygon RPC endpoint (defaults to public endpoint)
        """
        # Set up Web3 connection
        if rpc_url is None:
            rpc_url = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Polygon RPC: {rpc_url}")

        print(f"✅ Connected to Polygon (Chain ID: {self.w3.eth.chain_id})")

        # Set up wallet
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key

        self.account = Account.from_key(private_key)
        self.address = self.account.address

        print(f"📍 Wallet address: {self.address}")

        # Initialize contracts
        self.usdc = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS), abi=ERC20_ABI
        )
        self.usdt = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDT_ADDRESS), abi=ERC20_ABI
        )
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(QUICKSWAP_ROUTER), abi=ROUTER_ABI
        )

        # Token decimals (both USDC and USDT use 6 decimals on Polygon)
        self.usdc_decimals = 6
        self.usdt_decimals = 6

        # Statistics tracking
        self.start_time = None
        self.total_volume = 0.0
        self.total_fees_paid = 0.0  # In MATIC
        self.transaction_count = 0
        self.transactions = []
        self.initial_usdc_balance = 0.0

    def get_balance(self, token_address: str, decimals: int = 6) -> float:
        """Get token balance for the wallet."""
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=ERC20_ABI
        )
        balance = token.functions.balanceOf(self.address).call()
        return balance / (10 ** decimals)

    def get_matic_balance(self) -> float:
        """Get MATIC balance for gas fees."""
        balance = self.w3.eth.get_balance(self.address)
        return float(Web3.from_wei(balance, 'ether'))

    def approve_token(self, token_address: str, spender: str) -> bool:
        """
        Approve router to spend tokens.
        Only needs to be called once per token.
        """
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=ERC20_ABI
        )

        # Check current allowance
        allowance = token.functions.allowance(self.address, spender).call()

        if allowance > 0:
            print(f"✅ Token already approved: {token_address}")
            return True

        print(f"🔓 Approving {token_address}...")

        # Approve max uint256 for unlimited spending
        max_approval = 2**256 - 1

        try:
            # Build transaction
            approve_tx = token.functions.approve(spender, max_approval).build_transaction({
                'from': self.address,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.address),
            })

            # Sign and send
            signed = self.account.sign_transaction(approve_tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)

            print(f"   Approval TX: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt['status'] == 1:
                print(f"✅ Approval successful!")
                return True
            else:
                print(f"❌ Approval failed!")
                return False

        except Exception as e:
            print(f"❌ Approval error: {e}")
            return False

    def swap_tokens(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        decimals_in: int = 6,
        decimals_out: int = 6,
        slippage_percent: float = 5.0
    ) -> Optional[Tuple[str, float, float]]:
        """
        Execute a token swap via QuickSwap.

        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Amount to swap (human-readable)
            decimals_in: Input token decimals
            decimals_out: Output token decimals
            slippage_percent: Maximum acceptable slippage

        Returns:
            Tuple of (tx_hash, amount_out, gas_fee_matic) or None on failure
        """
        try:
            # Convert to wei
            amount_in_wei = int(amount_in * (10 ** decimals_in))

            if amount_in_wei == 0:
                print("❌ Amount too small to swap")
                return None

            # Get expected output amount
            path = [
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
            ]

            amounts_out = self.router.functions.getAmountsOut(amount_in_wei, path).call()
            expected_out = amounts_out[1]

            # Apply slippage tolerance
            min_amount_out = int(expected_out * (1 - slippage_percent / 100))

            # Deadline: 10 minutes from now
            deadline = int(time.time()) + 600

            # Build swap transaction
            swap_tx = self.router.functions.swapExactTokensForTokens(
                amount_in_wei,
                min_amount_out,
                path,
                self.address,
                deadline
            ).build_transaction({
                'from': self.address,
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.address),
            })

            # Sign and send
            signed = self.account.sign_transaction(swap_tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)

            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt['status'] != 1:
                print(f"❌ Swap failed!")
                return None

            # Calculate gas fee in MATIC
            gas_used = receipt['gasUsed']
            gas_price = receipt['effectiveGasPrice']
            gas_fee_matic = float(Web3.from_wei(gas_used * gas_price, 'ether'))

            # Calculate actual output
            amount_out = expected_out / (10 ** decimals_out)

            # Update statistics
            self.total_volume += amount_in
            self.total_fees_paid += gas_fee_matic
            self.transaction_count += 1

            # Record transaction
            self.transactions.append({
                'timestamp': datetime.now().isoformat(),
                'tx_hash': tx_hash.hex(),
                'from_token': token_in,
                'to_token': token_out,
                'amount_in': amount_in,
                'amount_out': amount_out,
                'gas_fee_matic': gas_fee_matic,
            })

            return (tx_hash.hex(), amount_out, gas_fee_matic)

        except Exception as e:
            print(f"❌ Swap error: {e}")
            return None

    def run(self, num_cycles: int = 150, use_full_balance: bool = True, fixed_amount: float = 50.0):
        """
        Execute volume inflation strategy.

        Args:
            num_cycles: Number of swap cycles to execute (1 cycle = 2 swaps)
            use_full_balance: If True, swap entire balance each time
            fixed_amount: If use_full_balance is False, swap this fixed amount
        """
        print("\n" + "="*60)
        print("🚀 POLYGON VOLUME INFLATION BOT")
        print("="*60)

        # Check balances
        usdc_balance = self.get_balance(USDC_ADDRESS, self.usdc_decimals)
        usdt_balance = self.get_balance(USDT_ADDRESS, self.usdt_decimals)
        matic_balance = self.get_matic_balance()

        print(f"\n💰 Initial Balances:")
        print(f"   USDC: {usdc_balance:.2f}")
        print(f"   USDT: {usdt_balance:.2f}")
        print(f"   MATIC: {matic_balance:.4f}")

        if usdc_balance < 1.0:
            print("\n❌ Error: Insufficient USDC balance (need at least $1)")
            return

        if matic_balance < 0.5:
            print("\n⚠️  Warning: Low MATIC balance. May not be enough for gas fees.")

        self.initial_usdc_balance = usdc_balance

        # Approve tokens (one-time)
        print("\n🔓 Checking token approvals...")
        router_address = Web3.to_checksum_address(QUICKSWAP_ROUTER)

        if not self.approve_token(USDC_ADDRESS, router_address):
            print("❌ Failed to approve USDC")
            return

        if not self.approve_token(USDT_ADDRESS, router_address):
            print("❌ Failed to approve USDT")
            return

        print("\n" + "="*60)
        print(f"Starting {num_cycles} cycles...")
        print("="*60 + "\n")

        self.start_time = time.time()
        successful_cycles = 0
        failed_cycles = 0

        for i in range(num_cycles):
            print(f"\n--- Cycle {i+1}/{num_cycles} ---")

            # Swap 1: USDC -> USDT
            usdc_balance = self.get_balance(USDC_ADDRESS, self.usdc_decimals)

            if usdc_balance < 0.1:
                print(f"❌ Insufficient USDC balance: {usdc_balance:.2f}")
                failed_cycles += 1
                continue

            swap_amount = usdc_balance if use_full_balance else min(fixed_amount, usdc_balance)

            print(f"💱 Swapping {swap_amount:.2f} USDC -> USDT...")
            result = self.swap_tokens(
                USDC_ADDRESS, USDT_ADDRESS, swap_amount,
                self.usdc_decimals, self.usdt_decimals
            )

            if result is None:
                print("❌ Swap 1 failed!")
                failed_cycles += 1
                continue

            tx_hash1, amount_out1, gas_fee1 = result
            print(f"✅ Received {amount_out1:.2f} USDT (Gas: {gas_fee1:.6f} MATIC)")
            print(f"   TX: {tx_hash1}")

            time.sleep(3)  # Brief delay between swaps

            # Swap 2: USDT -> USDC
            usdt_balance = self.get_balance(USDT_ADDRESS, self.usdt_decimals)

            # Use 99% of balance to account for any rounding
            swap_amount = usdt_balance * 0.99

            print(f"💱 Swapping {swap_amount:.2f} USDT -> USDC...")
            result = self.swap_tokens(
                USDT_ADDRESS, USDC_ADDRESS, swap_amount,
                self.usdt_decimals, self.usdc_decimals
            )

            if result is None:
                print("❌ Swap 2 failed!")
                failed_cycles += 1
                continue

            tx_hash2, amount_out2, gas_fee2 = result
            print(f"✅ Received {amount_out2:.2f} USDC (Gas: {gas_fee2:.6f} MATIC)")
            print(f"   TX: {tx_hash2}")

            successful_cycles += 1

            # Progress update every 10 cycles
            if (i + 1) % 10 == 0:
                elapsed = time.time() - self.start_time
                rate = self.transaction_count / elapsed * 60
                print(f"\n📊 Progress: {successful_cycles} cycles, {self.transaction_count} tx, {rate:.1f} tx/min")

            time.sleep(2)  # Brief delay before next cycle

        # Generate final report
        self._generate_report(successful_cycles, failed_cycles)

    def _generate_report(self, successful_cycles: int, failed_cycles: int):
        """Generate and display final statistics report."""
        duration = time.time() - self.start_time

        final_usdc = self.get_balance(USDC_ADDRESS, self.usdc_decimals)
        final_usdt = self.get_balance(USDT_ADDRESS, self.usdt_decimals)
        final_matic = self.get_matic_balance()

        capital_lost = self.initial_usdc_balance - final_usdc
        capital_lost_pct = (capital_lost / self.initial_usdc_balance * 100) if self.initial_usdc_balance > 0 else 0
        volume_multiplier = (self.total_volume / self.initial_usdc_balance) if self.initial_usdc_balance > 0 else 0

        print("\n" + "="*60)
        print("📊 FINAL REPORT")
        print("="*60)
        print(f"\n⏱️  Execution Summary:")
        print(f"   Duration: {duration/60:.1f} minutes ({duration:.0f} seconds)")
        print(f"   Successful cycles: {successful_cycles}")
        print(f"   Failed cycles: {failed_cycles}")
        print(f"   Total transactions: {self.transaction_count}")
        print(f"   Transaction rate: {self.transaction_count / duration * 60:.1f} tx/min")

        print(f"\n💰 Capital Analysis:")
        print(f"   Starting USDC: ${self.initial_usdc_balance:.2f}")
        print(f"   Final USDC: ${final_usdc:.2f}")
        print(f"   Final USDT: ${final_usdt:.2f}")
        print(f"   Capital lost: ${capital_lost:.2f} ({capital_lost_pct:.1f}%)")
        print(f"   Capital remaining: ${final_usdc:.2f} ({100-capital_lost_pct:.1f}%)")

        print(f"\n📈 Volume Metrics:")
        print(f"   Total volume generated: ${self.total_volume:.2f}")
        print(f"   Volume multiplier: {volume_multiplier:.1f}x")

        print(f"\n⛽ Cost Breakdown:")
        print(f"   Total gas fees: {self.total_fees_paid:.6f} MATIC (≈${self.total_fees_paid * 0.9:.2f})")
        print(f"   Trading fees (estimated): ${capital_lost - (self.total_fees_paid * 0.9):.2f}")
        print(f"   Final MATIC balance: {final_matic:.4f}")

        print("\n" + "="*60)
        print(f"✅ Run complete! Generated ${self.total_volume:.2f} volume from ${self.initial_usdc_balance:.2f}")
        print("="*60 + "\n")

        # Save detailed results to JSON
        results = {
            'summary': {
                'network': 'Polygon',
                'start_balance': self.initial_usdc_balance,
                'final_balance': final_usdc,
                'total_volume': self.total_volume,
                'transaction_count': self.transaction_count,
                'successful_cycles': successful_cycles,
                'failed_cycles': failed_cycles,
                'volume_multiplier': volume_multiplier,
                'capital_loss_percentage': capital_lost_pct,
                'execution_time_seconds': duration,
                'tx_rate_per_minute': self.transaction_count / duration * 60,
            },
            'transactions': self.transactions,
        }

        filename = f"polygon_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"📄 Detailed results saved to: {filename}\n")


def main():
    """Main entry point."""
    print("\n🔬 Polygon Volume Inflation Bot")
    print("Educational demonstration of DeFi metric manipulation\n")

    # Get private key from environment
    private_key = os.getenv('PRIVATE_KEY')
    if not private_key:
        print("❌ Error: PRIVATE_KEY environment variable not set")
        print("\nUsage:")
        print("  export PRIVATE_KEY='your_private_key_here'")
        print("  python volume_bot.py")
        sys.exit(1)

    # Optional: Custom RPC endpoint
    rpc_url = os.getenv('POLYGON_RPC_URL')

    try:
        # Initialize bot
        bot = PolygonVolumeBot(private_key, rpc_url)

        # Run with 150 cycles (default)
        # This will generate ~$10,000 volume from $50
        bot.run(num_cycles=150, use_full_balance=True)

    except KeyboardInterrupt:
        print("\n\n⚠️  Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
