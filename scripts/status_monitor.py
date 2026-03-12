#!/usr/bin/env python3
"""
Real-time monitoring dashboard for autonomous researcher.

Shows:
- Current run status
- Latest scores
- Contamination status
- Time until next scheduled run
- Recommendations

Usage:
  python3 scripts/status_monitor.py              # Show once
  python3 scripts/status_monitor.py --watch 30   # Update every 30 seconds
"""

import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

RESULTS_FILE = Path("results.jsonl")
LEADERBOARD_FILE = Path("leaderboard.tsv")


def get_latest_result() -> Optional[Dict]:
    """Get the most recent result from results.jsonl."""
    if not RESULTS_FILE.exists():
        return None

    with open(RESULTS_FILE) as f:
        lines = f.readlines()

    if not lines:
        return None

    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def get_running_runs() -> list:
    """Get list of currently running training runs."""
    try:
        result = subprocess.run(
            ["prime", "rl", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Parse output to find RUNNING runs
            running = []
            for line in result.stdout.split("\n"):
                if "RUNNING" in line:
                    parts = line.split()
                    if parts:
                        running.append(parts[0])
            return running
        return []
    except Exception:
        return []


def format_timestamp(iso_string: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return iso_string


def print_dashboard():
    """Print formatted status dashboard."""
    latest = get_latest_result()
    running = get_running_runs()

    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "AUTONOMOUS RESEARCHER STATUS" + " " * 26 + "║")
    print("╚" + "═" * 68 + "╝\n")

    # Latest result
    if latest:
        print("📊 Latest Result:")
        print(f"  Dataset: {latest.get('dataset', {}).get('name', '?')}")
        score = latest.get("evaluation", {}).get("mteb_scores", {}).get("primary_score", 0)
        print(f"  Primary Score: {score:.2f}")
        sts = latest.get("evaluation", {}).get("mteb_scores", {}).get("sts_mean", 0)
        retrieval = latest.get("evaluation", {}).get("mteb_scores", {}).get("retrieval_mean", 0)
        print(f"  STS Mean: {sts:.2f} | Retrieval Mean: {retrieval:.2f}")

        contam = latest.get("evaluation", {}).get("contamination", {})
        status = "✓ PASSED" if contam.get("passed") else "✗ FAILED"
        rate = contam.get("overall_rate", 0)
        print(f"  Contamination: {status} ({rate:.4f} overlap)")
        print()
    else:
        print("📊 Latest Result: None yet\n")

    # Running runs
    if running:
        print(f"🟢 Currently Running: {len(running)} run(s)")
        for run_id in running[:3]:  # Show top 3
            print(f"   - {run_id}")
        print()
    else:
        print("🔴 Currently Running: None\n")

    # Leaderboard summary
    if LEADERBOARD_FILE.exists():
        with open(LEADERBOARD_FILE) as f:
            lines = f.readlines()

        if len(lines) > 2:  # Header + separator + data
            print(f"📈 Leaderboard Summary ({len(lines) - 2} runs):")
            scores = []
            for line in lines[2:]:  # Skip header and separator
                parts = line.split("\t")
                if len(parts) >= 3:
                    try:
                        score = float(parts[2])
                        scores.append(score)
                    except ValueError:
                        pass

            if scores:
                print(f"  Best Score: {max(scores):.2f}")
                print(f"  Latest Score: {scores[-1]:.2f}")
                if len(scores) > 1:
                    improvement = scores[-1] - scores[0]
                    rate = improvement / (len(scores) - 1)
                    print(f"  Improvement: {improvement:+.2f} ({rate:.4f}/run)")
            print()

    # Next scheduled run (for cron: every 2 hours)
    print("⏱️  Schedule:")
    print("  Frequency: Every 2 hours")
    print("  Next run: Check with `crontab -l` (if deployed)")
    print()

    # Quick stats
    if latest:
        results_count = sum(1 for _ in open(RESULTS_FILE)) if RESULTS_FILE.exists() else 0
        print(f"📋 Statistics:")
        print(f"  Total Runs: {results_count}")
        print(f"  Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    print("=" * 70 + "\n")


def watch_mode(interval: int = 30):
    """Continuously show dashboard with updates."""
    try:
        while True:
            print("\033[2J\033[H")  # Clear screen
            print_dashboard()
            print(f"⏳ Updating in {interval}s (Ctrl+C to stop)\n")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")


def main():
    """Main entry point."""
    import sys

    watch = False
    interval = 30

    if "--watch" in sys.argv:
        watch = True
        idx = sys.argv.index("--watch")
        if idx + 1 < len(sys.argv):
            try:
                interval = int(sys.argv[idx + 1])
            except ValueError:
                pass

    if watch:
        watch_mode(interval)
    else:
        print_dashboard()


if __name__ == "__main__":
    main()
