#!/usr/bin/env python3
"""
Solana Volume Inflation Bot (Original Version)
Educational demonstration of DeFi volume manipulation via repeated stablecoin swaps.

This bot uses Jupiter aggregator on Solana to execute USDC<->USDT swaps,
generating significant apparent volume from minimal capital with much lower fees than Polygon.

Features:
- Jupiter API v6 integration (finds best routes across all Solana DEXes)
- ~10 minute execution time (150 cycles)
- ~2.4% capital loss (vs 69% on Polygon)
- 0.01% trading fees (vs 0.3% on Polygon)
"""

import os
import sys
import time
import json
import base58
import requests
from decimal import Decimal
from datetime import datetime
from typing import Optional, Tuple, List

from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned


# Token mints on Solana Mainnet
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

# Jupiter API endpoint
JUPITER_API = "https://quote-api.jup.ag/v6"

# Associated Token Program ID
SPL_ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID = Pubkey.from_string(
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
)
SPL_TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")


class SolanaVolumeBot:
    """
    Solana-based volume inflation bot using Jupiter aggregator.

    Executes repeated USDC<->USDT swaps to generate artificial trading volume.
    Much more cost-effective than Polygon due to lower fees and faster execution.
    """

    def __init__(self, private_key_str: str, rpc_url: Optional[str] = None):
        """
        Initialize the bot with wallet and RPC connection.

        Args:
            private_key_str: Solana private key (array format or base58)
            rpc_url: Solana RPC endpoint (defaults to public endpoint)
        """
        # Set up Solana RPC connection
        if rpc_url is None:
            rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

        self.client = Client(rpc_url)

        # Parse private key
        try:
            # Try parsing as JSON array first
            if private_key_str.startswith('['):
                key_bytes = bytes(json.loads(private_key_str))
            else:
                # Try base58 decoding
                key_bytes = base58.b58decode(private_key_str)

            self.keypair = Keypair.from_bytes(key_bytes)
            self.pubkey = self.keypair.pubkey()

        except Exception as e:
            raise ValueError(f"Invalid private key format: {e}")

        print(f"✅ Connected to Solana")
        print(f"📍 Wallet address: {self.pubkey}")

        # Token mints as Pubkey objects
        self.usdc_mint = Pubkey.from_string(USDC_MINT)
        self.usdt_mint = Pubkey.from_string(USDT_MINT)

        # Derive associated token accounts
        self.usdc_ata = self._get_associated_token_address(self.pubkey, self.usdc_mint)
        self.usdt_ata = self._get_associated_token_address(self.pubkey, self.usdt_mint)

        print(f"   USDC ATA: {self.usdc_ata}")
        print(f"   USDT ATA: {self.usdt_ata}")

        # Statistics tracking
        self.start_time = None
        self.total_volume = 0.0
        self.total_fees_paid = 0.0  # In SOL
        self.transaction_count = 0
        self.transactions = []
        self.initial_usdc_balance = 0.0

    def _get_associated_token_address(self, owner: Pubkey, mint: Pubkey) -> Pubkey:
        """Derive associated token account address."""
        seeds = [
            bytes(owner),
            bytes(SPL_TOKEN_PROGRAM_ID),
            bytes(mint),
        ]

        # Find program address
        address, _ = Pubkey.find_program_address(
            seeds, SPL_ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID
        )

        return address

    def get_token_balance(self, mint: Pubkey) -> float:
        """Get token balance for a specific mint."""
        try:
            ata = self._get_associated_token_address(self.pubkey, mint)

            response = self.client.get_token_account_balance(ata)

            if response.value is None:
                return 0.0

            # Return ui_amount (human-readable amount)
            return float(response.value.ui_amount or 0.0)

        except Exception as e:
            # Account might not exist yet
            return 0.0

    def get_sol_balance(self) -> float:
        """Get SOL balance for gas fees."""
        try:
            response = self.client.get_balance(self.pubkey)
            lamports = response.value
            return lamports / 1e9  # Convert lamports to SOL

        except Exception as e:
            print(f"Error getting SOL balance: {e}")
            return 0.0

    def swap_tokens_jupiter(
        self,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage_bps: int = 50
    ) -> Optional[Tuple[str, float, float]]:
        """
        Execute a token swap via Jupiter aggregator.

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount to swap (in UI units, e.g., 50.0 USDC)
            slippage_bps: Slippage tolerance in basis points (50 = 0.5%)

        Returns:
            Tuple of (tx_signature, amount_out, fee_sol) or None on failure
        """
        try:
            # Convert amount to lamports (6 decimals for both USDC and USDT)
            amount_lamports = int(amount * 1e6)

            if amount_lamports == 0:
                print("❌ Amount too small to swap")
                return None

            # Step 1: Get quote from Jupiter
            quote_url = f"{JUPITER_API}/quote"
            quote_params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount_lamports,
                'slippageBps': slippage_bps,
            }

            quote_response = requests.get(quote_url, params=quote_params, timeout=10)
            quote_response.raise_for_status()
            quote_data = quote_response.json()

            expected_out_lamports = int(quote_data['outAmount'])
            expected_out = expected_out_lamports / 1e6

            # Step 2: Get swap transaction
            swap_url = f"{JUPITER_API}/swap"
            swap_body = {
                'quoteResponse': quote_data,
                'userPublicKey': str(self.pubkey),
                'wrapAndUnwrapSol': True,
            }

            swap_response = requests.post(swap_url, json=swap_body, timeout=10)
            swap_response.raise_for_status()
            swap_data = swap_response.json()

            # Step 3: Deserialize and sign transaction
            swap_transaction_buf = base58.b58decode(swap_data['swapTransaction'])
            transaction = VersionedTransaction.from_bytes(swap_transaction_buf)

            # Sign transaction
            signed_tx = VersionedTransaction(
                transaction.message,
                [self.keypair]
            )

            # Step 4: Send transaction
            tx_bytes = bytes(signed_tx)
            response = self.client.send_raw_transaction(tx_bytes)

            if response.value:
                signature = str(response.value)
            else:
                print("❌ Failed to send transaction")
                return None

            # Step 5: Wait for confirmation
            start_time = time.time()
            timeout = 30

            while time.time() - start_time < timeout:
                try:
                    status_response = self.client.get_signature_statuses([response.value])

                    if status_response.value and status_response.value[0]:
                        status = status_response.value[0]

                        if status.confirmation_status:
                            # Transaction confirmed
                            # Get transaction details for fee
                            tx_response = self.client.get_transaction(
                                response.value,
                                max_supported_transaction_version=0
                            )

                            fee_lamports = 5000  # Default estimate
                            if tx_response.value and tx_response.value.transaction.meta:
                                fee_lamports = tx_response.value.transaction.meta.fee

                            fee_sol = fee_lamports / 1e9

                            # Update statistics
                            self.total_volume += amount
                            self.total_fees_paid += fee_sol
                            self.transaction_count += 1

                            # Record transaction
                            self.transactions.append({
                                'timestamp': datetime.now().isoformat(),
                                'signature': signature,
                                'from_token': input_mint,
                                'to_token': output_mint,
                                'amount_in': amount,
                                'amount_out': expected_out,
                                'fee_sol': fee_sol,
                            })

                            return (signature, expected_out, fee_sol)

                except Exception as e:
                    pass

                time.sleep(0.5)

            print(f"⚠️  Transaction sent but confirmation timeout: {signature}")
            return (signature, expected_out, 0.000005)

        except requests.exceptions.RequestException as e:
            print(f"❌ Jupiter API error: {e}")
            return None
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
        print("🚀 SOLANA VOLUME INFLATION BOT (Original)")
        print("="*60)

        # Check balances
        usdc_balance = self.get_token_balance(self.usdc_mint)
        usdt_balance = self.get_token_balance(self.usdt_mint)
        sol_balance = self.get_sol_balance()

        print(f"\n💰 Initial Balances:")
        print(f"   USDC: {usdc_balance:.2f}")
        print(f"   USDT: {usdt_balance:.2f}")
        print(f"   SOL: {sol_balance:.4f}")

        if usdc_balance < 1.0:
            print("\n❌ Error: Insufficient USDC balance (need at least $1)")
            return

        if sol_balance < 0.01:
            print("\n⚠️  Warning: Low SOL balance. May not be enough for gas fees.")

        self.initial_usdc_balance = usdc_balance

        # Note: No token approvals needed on Solana!
        print("\n✅ No token approvals needed on Solana (SPL token advantage)")

        print("\n" + "="*60)
        print(f"Starting {num_cycles} cycles...")
        print("="*60 + "\n")

        self.start_time = time.time()
        successful_cycles = 0
        failed_cycles = 0

        for i in range(num_cycles):
            print(f"\n--- Cycle {i+1}/{num_cycles} ---")

            # Swap 1: USDC -> USDT
            usdc_balance = self.get_token_balance(self.usdc_mint)

            if usdc_balance < 0.1:
                print(f"❌ Insufficient USDC balance: {usdc_balance:.2f}")
                failed_cycles += 1
                continue

            swap_amount = usdc_balance if use_full_balance else min(fixed_amount, usdc_balance)

            print(f"💱 Swapping {swap_amount:.2f} USDC -> USDT...")
            result = self.swap_tokens_jupiter(USDC_MINT, USDT_MINT, swap_amount)

            if result is None:
                print("❌ Swap 1 failed!")
                failed_cycles += 1
                continue

            sig1, amount_out1, fee1 = result
            print(f"✅ Received {amount_out1:.2f} USDT (Fee: {fee1:.6f} SOL)")
            print(f"   TX: {sig1}")

            time.sleep(2)  # Brief delay between swaps

            # Swap 2: USDT -> USDC
            usdt_balance = self.get_token_balance(self.usdt_mint)

            # Use 99% of balance to account for any rounding
            swap_amount = usdt_balance * 0.99

            print(f"💱 Swapping {swap_amount:.2f} USDT -> USDC...")
            result = self.swap_tokens_jupiter(USDT_MINT, USDC_MINT, swap_amount)

            if result is None:
                print("❌ Swap 2 failed!")
                failed_cycles += 1
                continue

            sig2, amount_out2, fee2 = result
            print(f"✅ Received {amount_out2:.2f} USDC (Fee: {fee2:.6f} SOL)")
            print(f"   TX: {sig2}")

            successful_cycles += 1

            # Progress update every 10 cycles
            if (i + 1) % 10 == 0:
                elapsed = time.time() - self.start_time
                rate = self.transaction_count / elapsed * 60
                print(f"\n📊 Progress: {successful_cycles} cycles, {self.transaction_count} tx, {rate:.1f} tx/min")

            time.sleep(1)  # Brief delay before next cycle

        # Generate final report
        self._generate_report(successful_cycles, failed_cycles)

    def _generate_report(self, successful_cycles: int, failed_cycles: int):
        """Generate and display final statistics report."""
        duration = time.time() - self.start_time

        final_usdc = self.get_token_balance(self.usdc_mint)
        final_usdt = self.get_token_balance(self.usdt_mint)
        final_sol = self.get_sol_balance()

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
        print(f"   Total gas fees: {self.total_fees_paid:.6f} SOL (≈${self.total_fees_paid * 150:.2f})")
        sol_price_estimate = 150  # Rough estimate
        estimated_trading_fees = capital_lost - (self.total_fees_paid * sol_price_estimate)
        print(f"   Trading fees (estimated): ${estimated_trading_fees:.2f}")
        print(f"   Final SOL balance: {final_sol:.4f}")

        print("\n" + "="*60)
        print(f"✅ Run complete! Generated ${self.total_volume:.2f} volume from ${self.initial_usdc_balance:.2f}")
        print("="*60 + "\n")

        # Save detailed results to JSON
        results = {
            'summary': {
                'network': 'Solana',
                'version': 'Original',
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

        filename = f"solana_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"📄 Detailed results saved to: {filename}\n")


def main():
    """Main entry point."""
    print("\n🔬 Solana Volume Inflation Bot (Original Version)")
    print("Educational demonstration of DeFi metric manipulation\n")

    # Get private key from environment
    private_key = os.getenv('PRIVATE_KEY')
    if not private_key:
        print("❌ Error: PRIVATE_KEY environment variable not set")
        print("\nUsage:")
        print("  export PRIVATE_KEY='your_private_key_here'")
        print("  python volume_bot.py")
        print("\nPrivate key formats supported:")
        print("  - Base58 string")
        print("  - JSON array: '[1,2,3,...]'")
        sys.exit(1)

    # Optional: Custom RPC endpoint
    rpc_url = os.getenv('SOLANA_RPC_URL')

    try:
        # Initialize bot
        bot = SolanaVolumeBot(private_key, rpc_url)

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
