#!/usr/bin/env python3
"""Merge YES + NO conditional tokens back into USDC.e.

Usage:
    polyclaw merge <market_id> [amount]

Looks up the market, checks on-chain balances for the actual CLOB token IDs,
and merges the overlapping YES + NO tokens back into USDC.e.
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path

# Add parent to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file from skill root directory
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from web3 import Web3

from lib.wallet_manager import WalletManager
from lib.gamma_client import GammaClient
from lib.contracts import CONTRACTS, CTF_ABI, NEG_RISK_ADAPTER_ABI, POLYGON_CHAIN_ID


async def cmd_merge(args):
    """Execute merge command."""
    wallet = WalletManager()
    if not wallet.is_unlocked:
        print(json.dumps({"error": "No wallet configured. Set POLYCLAW_PRIVATE_KEY."}))
        return 1

    # Look up market to get token IDs and neg_risk status
    gamma = GammaClient()
    try:
        market = await gamma.get_market(args.market_id)
    except Exception as e:
        print(json.dumps({"error": f"Market not found: {e}"}))
        return 1

    print(f"Market: {market.question}")
    print(f"Neg-risk: {market.neg_risk}")

    yes_token_id = int(market.yes_token_id)
    no_token_id = int(market.no_token_id)

    # Check on-chain balances using actual CLOB token IDs
    w3 = Web3(
        Web3.HTTPProvider(
            wallet.rpc_url, request_kwargs={"timeout": 60, "proxies": {"http": None, "https": None}}
        )
    )
    address = Web3.to_checksum_address(wallet.address)
    account = w3.eth.account.from_key(wallet.get_unlocked_key())

    ctf = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["CTF"]),
        abi=CTF_ABI,
    )

    yes_bal = ctf.functions.balanceOf(address, yes_token_id).call()
    no_bal = ctf.functions.balanceOf(address, no_token_id).call()

    print(f"YES tokens: {yes_bal / 1e6:.6f}")
    print(f"NO tokens:  {no_bal / 1e6:.6f}")

    mergeable = min(yes_bal, no_bal)

    if args.amount is not None:
        if args.amount <= 0:
            print(json.dumps({"error": "Amount must be greater than 0"}))
            return 1
        amount_wei = int(round(args.amount * 1e6))
        if amount_wei > mergeable:
            print(
                json.dumps(
                    {
                        "error": f"Requested ${args.amount:.6f} but max mergeable is ${mergeable / 1e6:.6f}"
                    }
                )
            )
            return 1
    else:
        amount_wei = mergeable

    if amount_wei == 0:
        if yes_bal == 0 and no_bal == 0:
            print("No tokens held for this market.")
        elif yes_bal == 0:
            print(f"Only NO tokens held ({no_bal / 1e6:.6f}). Nothing to merge — need both sides.")
        else:
            print(f"Only YES tokens held ({yes_bal / 1e6:.6f}). Nothing to merge — need both sides.")
        return 1

    print(f"Merging: ${amount_wei / 1e6:.6f}")

    condition_bytes = bytes.fromhex(
        market.condition_id[2:]
        if market.condition_id.startswith("0x")
        else market.condition_id
    )

    # Route to correct contract
    if market.neg_risk:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACTS["NEG_RISK_ADAPTER"]),
            abi=NEG_RISK_ADAPTER_ABI,
        )
    else:
        contract = ctf

    tx = contract.functions.mergePositions(
        Web3.to_checksum_address(CONTRACTS["USDC_E"]),
        bytes(32),
        condition_bytes,
        [1, 2],
        amount_wei,
    ).build_transaction(
        {
            "from": address,
            "nonce": w3.eth.get_transaction_count(address, "pending"),
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
            "chainId": POLYGON_CHAIN_ID,
        }
    )

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TX sent: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt["status"] != 1:
        print(json.dumps({"error": f"Merge TX failed: {tx_hash.hex()}"}))
        return 1

    gas_cost = receipt["gasUsed"] * receipt.get(
        "effectiveGasPrice", w3.eth.gas_price
    )
    gas_cost_pol = float(w3.from_wei(gas_cost, "ether"))

    # Check remaining balances
    remaining_yes = ctf.functions.balanceOf(address, yes_token_id).call() / 1e6
    remaining_no = ctf.functions.balanceOf(address, no_token_id).call() / 1e6

    result = {
        "market": market.question,
        "amount_merged": amount_wei / 1e6,
        "usdc_e_received": amount_wei / 1e6,
        "tx_hash": tx_hash.hex(),
        "gas_cost_pol": gas_cost_pol,
        "neg_risk": market.neg_risk,
        "remaining_yes": remaining_yes,
        "remaining_no": remaining_no,
    }
    print(json.dumps(result, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Merge YES+NO tokens back to USDC.e"
    )
    parser.add_argument("market_id", help="Market ID (numeric)")
    parser.add_argument(
        "amount",
        type=float,
        nargs="?",
        default=None,
        help="USD amount to merge (default: all overlapping)",
    )

    args = parser.parse_args()
    return asyncio.run(cmd_merge(args))


if __name__ == "__main__":
    sys.exit(main() or 0)
