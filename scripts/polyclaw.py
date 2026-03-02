#!/usr/bin/env python3
"""PolyClaw CLI - Polymarket trading skill for OpenClaw.

Usage:
    polyclaw markets trending
    polyclaw markets search "election"
    polyclaw market <id>
    polyclaw wallet status
    polyclaw wallet approve
    polyclaw buy <market_id> YES 50
    polyclaw positions
    polyclaw merge <condition_id>
    polyclaw redeem [--dry-run]
    polyclaw swap to-bridged [--amount N] [--dry-run]
    polyclaw portfolio status|rules|history|snapshot
    polyclaw performance summary|trades|chart
    polyclaw hedge scan
    polyclaw hedge analyze <id1> <id2>
"""

import sys
import subprocess
from pathlib import Path

# Load .env file from skill root directory (for OpenClaw env var injection)
from dotenv import load_dotenv
SKILL_DIR = Path(__file__).parent.parent
load_dotenv(SKILL_DIR / ".env")

# Script directory
SCRIPT_DIR = Path(__file__).parent


def run_script(script_name: str, args: list[str]) -> int:
    """Run a script with arguments."""
    script_path = SCRIPT_DIR / f"{script_name}.py"
    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        return 1

    cmd = [sys.executable, str(script_path)] + args
    result = subprocess.run(cmd)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1]
    args = sys.argv[2:]

    # Route commands to appropriate scripts
    if command == "markets":
        return run_script("markets", args)

    elif command == "market":
        # Shortcut: polyclaw market <id> -> polyclaw markets details <id>
        if not args:
            print("Usage: polyclaw market <market_id>")
            return 1
        return run_script("markets", ["details"] + args)

    elif command == "wallet":
        return run_script("wallet", args)

    elif command == "buy":
        # Shortcut: polyclaw buy <id> YES 50 -> trade buy <id> YES 50
        return run_script("trade", ["buy"] + args)

    elif command == "positions":
        return run_script("positions", args)

    elif command == "position":
        # Shortcut: polyclaw position <id> -> positions show <id>
        if args:
            return run_script("positions", ["show"] + args)
        else:
            return run_script("positions", ["list"])

    elif command == "merge":
        return run_script("merge_tokens", args)

    elif command == "redeem":
        return run_script("redeem", args)

    elif command == "swap":
        return run_script("swap_usdc", args)

    elif command == "portfolio":
        return run_script("portfolio", args)

    elif command == "performance":
        return run_script("performance", args)

    elif command == "hedge":
        return run_script("hedge", args)

    elif command == "help" or command == "--help" or command == "-h":
        print(__doc__)
        print("Commands:")
        print("  markets trending           Show trending markets by volume")
        print("  markets search <query>     Search markets by keyword")
        print("  markets events             Show events with multiple markets")
        print("  market <id>                Show market details")
        print("")
        print("  wallet status              Show wallet status and balances")
        print("  wallet approve             Set Polymarket contract approvals (one-time)")
        print("")
        print("  buy <market_id> YES <amt>  Buy YES position for $amt")
        print("  buy <market_id> NO <amt>   Buy NO position for $amt")
        print("")
        print("  positions                  List open positions with P&L")
        print("  positions --all            List all positions")
        print("  position <id>              Show position details")
        print("")
        print("  merge <condition_id>       Merge YES+NO tokens back to USDC.e")
        print("  redeem [--dry-run]         Auto-redeem resolved positions")
        print("  swap to-bridged|to-native  Swap USDC <-> USDC.e via QuickSwap")
        print("  swap balances              Show USDC and USDC.e balances")
        print("")
        print("  portfolio status           Portfolio overview with allocation check")
        print("  portfolio rules            Show portfolio rules")
        print("  portfolio history          Trade journal entries")
        print("  portfolio snapshot         Save portfolio snapshot")
        print("")
        print("  performance summary        Win rate, P&L, profit factor")
        print("  performance trades         Per-trade breakdown")
        print("  performance chart          ASCII portfolio value chart")
        print("")
        print("  hedge scan                 Scan trending markets for hedges")
        print("  hedge scan --query <q>     Scan markets matching query")
        print("  hedge analyze <id1> <id2>  Analyze pair for hedging relationship")
        print("")
        print("Environment Variables:")
        print("  POLYGON_RPC_URL            Polygon RPC URL (primary)")
        print("  CHAINSTACK_NODE            Polygon RPC URL (fallback)")
        print("  OPENROUTER_API_KEY         OpenRouter API key (required for hedge)")
        print("  POLYCLAW_PRIVATE_KEY       EVM private key (required for trading)")
        print("")
        print("Examples:")
        print("  polyclaw markets trending")
        print("  polyclaw markets search 'trump'")
        print("  polyclaw market will-trump-win-2028")
        print("  polyclaw wallet status")
        print("  polyclaw buy abc123 YES 50")
        print("  polyclaw positions")
        print("  polyclaw merge 0xabc123...")
        print("  polyclaw redeem --dry-run")
        print("  polyclaw swap to-bridged --amount 10")
        print("  polyclaw portfolio status")
        print("  polyclaw performance summary")
        print("  polyclaw hedge scan")
        return 0

    elif command == "version" or command == "--version" or command == "-v":
        print("PolyClaw v0.1.0")
        return 0

    else:
        print(f"Unknown command: {command}")
        print("Run 'polyclaw help' for usage")
        return 1


if __name__ == "__main__":
    sys.exit(main())
