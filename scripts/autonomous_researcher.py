#!/usr/bin/env python3
"""
Autonomous embedding researcher agent.

Runs a continuous loop that:
1. Reads latest results from results.jsonl
2. Analyzes gradient (is score improving?)
3. Selects next dataset based on decision logic
4. Sets environment variables
5. Launches prime rl run
6. Monitors for completion
7. Validates contamination check
8. Commits results to git
9. Repeats every 2-4 hours

Designed for 24/7 unattended operation with human review every 24h.

See: AUTONOMOUS_RESEARCH_PROTOCOL.md for detailed documentation.
See: DATASET_INVENTORY.md for dataset selection logic.
See: CLAUDE.md for agent guidelines.
"""

import json
import os
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Configuration
RESULTS_FILE = Path("results.jsonl")
LEADERBOARD_FILE = Path("leaderboard.tsv")
LOG_FILE = Path("autonomous_researcher.log")
POLL_INTERVAL = 300  # 5 min between status checks
MAX_WAIT_HOURS = 24  # Max wait for run to complete

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


def read_latest_result() -> Optional[Dict]:
    """Read most recent result from results.jsonl."""
    if not RESULTS_FILE.exists():
        logger.info("results.jsonl not found, starting fresh")
        return None

    with open(RESULTS_FILE) as f:
        lines = f.readlines()

    if not lines:
        return None

    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse last result: {e}")
        return None


def compute_gradient(results_history: List[Dict], window_size: int = 5) -> float:
    """
    Compute gradient of primary_score over last N runs.
    Returns: average improvement per run (points per run).
    """
    if len(results_history) < 2:
        return 0.0

    recent = results_history[-min(window_size, len(results_history)):]
    scores = [
        r.get("evaluation", {}).get("mteb_scores", {}).get("primary_score", 0)
        for r in recent
    ]

    if len(scores) < 2:
        return 0.0

    gradient = (scores[-1] - scores[0]) / (len(scores) - 1)
    return gradient


def check_contamination_passed(result: Dict) -> bool:
    """Check if result passed contamination check."""
    contamination = result.get("evaluation", {}).get("contamination", {})
    passed = contamination.get("passed", False)
    rate = contamination.get("overall_rate", 1.0)

    if not passed:
        logger.warning(
            f"Result contaminated: {rate:.4f} overlap with MTEB test sets"
        )
        return False

    logger.info(f"Contamination check passed: {rate:.4f} overlap (safe)")
    return True


def load_results_history() -> List[Dict]:
    """Load all valid results from results.jsonl."""
    if not RESULTS_FILE.exists():
        return []

    results = []
    with open(RESULTS_FILE) as f:
        for line in f:
            try:
                result = json.loads(line)
                # Only include results that passed contamination
                if check_contamination_passed(result):
                    results.append(result)
            except json.JSONDecodeError:
                pass

    return results


def select_next_dataset(results_history: List[Dict], iteration: int) -> Dict:
    """
    Select next dataset based on current performance.

    Decision logic (from DATASET_INVENTORY.md):
    - score < 50: BRIGHT (baseline)
    - score < 60: FollowIR (instruction signal)
    - score < 70: MIRACL-en (multilingual)
    - score >= 70: alternate languages or synthetic
    """
    if not results_history:
        logger.info("No results yet, starting with BRIGHT baseline")
        return {
            "name": "BRIGHT",
            "env": "BRIGHT",
            "dataset": "google-research-datasets/BRIGHT",
            "config": "gpt4_reason",
            "reason": "First run - baseline",
        }

    latest = results_history[-1]
    score = latest.get("evaluation", {}).get("mteb_scores", {}).get("primary_score", 0)

    # Compute gradient to detect plateau
    gradient = compute_gradient(results_history, window_size=5)
    logger.info(f"Current score: {score:.2f}, gradient: {gradient:.4f} points/run")

    # Decision tree
    if score < 50:
        logger.info("Score < 50: Continue BRIGHT baseline")
        return {
            "name": "BRIGHT",
            "env": "BRIGHT",
            "dataset": "google-research-datasets/BRIGHT",
            "config": "gpt4_reason",
            "reason": "Below 50 threshold - optimize baseline",
        }

    elif score < 60:
        logger.info("Score < 60: Try FollowIR for instruction signal")
        return {
            "name": "FollowIR",
            "env": "FOLLOWIR",
            "dataset": "jhu-clsp/FollowIR-train",
            "split": "train",
            "reason": "Below 60 threshold - add instruction signal",
        }

    elif score < 70:
        logger.info("Score < 70: Try MIRACL-en for multilingual signal")
        return {
            "name": "MIRACL-en",
            "env": "MIRACL",
            "dataset": "miracl/miracl",
            "language": "en",
            "split": "train",
            "reason": "Below 70 threshold - add multilingual signal",
        }

    else:
        # Plateau detection: if gradient < 0.1, try new language
        if gradient < 0.1:
            languages = ["es", "fr", "de", "pt", "zh"]
            lang = languages[iteration % len(languages)]
            logger.info(f"Plateau detected: trying MIRACL-{lang}")
            return {
                "name": f"MIRACL-{lang}",
                "env": "MIRACL",
                "dataset": "miracl/miracl",
                "language": lang,
                "split": "train",
                "reason": f"Score plateau at {score:.2f} - explore multilingually",
            }

        else:
            logger.info("Score improving: continue current dataset")
            # Continue current dataset
            current = latest.get("dataset", {})
            return {
                "name": current.get("name", "BRIGHT"),
                "env": "BRIGHT",  # Default to BRIGHT
                "reason": f"Score improving ({gradient:.4f}/run) - continue",
            }


def set_environment_variables(dataset_config: Dict):
    """Set environment variables for dataset selection."""
    env_prefix = dataset_config.get("env", "BRIGHT").upper()

    if env_prefix == "BRIGHT":
        os.environ["BRIGHT_DATASET"] = dataset_config.get(
            "dataset", "google-research-datasets/BRIGHT"
        )
        os.environ["BRIGHT_CONFIG"] = dataset_config.get("config", "gpt4_reason")
        logger.info(f"Set: BRIGHT_DATASET={os.environ['BRIGHT_DATASET']}")

    elif env_prefix == "FOLLOWIR":
        os.environ["FOLLOWIR_DATASET"] = dataset_config.get(
            "dataset", "jhu-clsp/FollowIR-train"
        )
        os.environ["FOLLOWIR_SPLIT"] = dataset_config.get("split", "train")
        logger.info(f"Set: FOLLOWIR_DATASET={os.environ['FOLLOWIR_DATASET']}")

    elif env_prefix == "MIRACL":
        os.environ["MIRACL_DATASET"] = dataset_config.get(
            "dataset", "miracl/miracl"
        )
        os.environ["MIRACL_LANGUAGE"] = dataset_config.get("language", "en")
        os.environ["MIRACL_SPLIT"] = dataset_config.get("split", "train")
        logger.info(f"Set: MIRACL_DATASET={os.environ['MIRACL_DATASET']}, "
                   f"MIRACL_LANGUAGE={os.environ['MIRACL_LANGUAGE']}")


def launch_training() -> Optional[str]:
    """Launch prime rl run and return run ID."""
    cmd = ["prime", "rl", "run", "configs/bright_baseline.toml"]
    logger.info(f"Launching: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            logger.error(f"prime rl run failed: {result.stderr}")
            return None

        # Parse run ID from output
        for line in result.stdout.split("\n"):
            if "run_id" in line.lower() or "id:" in line.lower():
                # Extract run ID (format varies)
                parts = line.split()
                for part in parts:
                    if len(part) > 20 and part.isalnum():  # Likely a run ID
                        logger.info(f"Run ID: {part}")
                        return part

        logger.warning("Could not extract run ID from output, using fallback")
        return None

    except subprocess.TimeoutExpired:
        logger.error("prime rl run timed out after 60 seconds")
        return None
    except Exception as e:
        logger.error(f"Error launching training: {e}")
        return None


def wait_for_completion(run_id: str, max_wait: int = MAX_WAIT_HOURS) -> bool:
    """Poll for training completion."""
    max_wait_sec = max_wait * 3600
    start_time = time.time()

    while time.time() - start_time < max_wait_sec:
        try:
            result = subprocess.run(
                ["prime", "rl", "status", run_id],
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout.lower()

            if "completed" in output:
                logger.info(f"Run {run_id} COMPLETED")
                return True

            if "failed" in output:
                logger.error(f"Run {run_id} FAILED")
                return False

            elapsed_hours = (time.time() - start_time) / 3600
            logger.info(
                f"Run {run_id} still running... ({elapsed_hours:.1f}h elapsed)"
            )

        except subprocess.TimeoutExpired:
            logger.warning("Status check timed out")
        except Exception as e:
            logger.error(f"Error checking status: {e}")

        time.sleep(POLL_INTERVAL)

    logger.error(f"Run {run_id} did not complete within {max_wait}h")
    return False


def extract_metrics(run_id: str) -> Optional[Dict]:
    """Extract metrics from completed run."""
    try:
        result = subprocess.run(
            ["prime", "rl", "metrics", run_id],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.error(f"Failed to extract metrics: {result.stderr}")
            return None

        # Try to parse as JSON
        metrics = json.loads(result.stdout)
        return metrics

    except json.JSONDecodeError:
        logger.error("Metrics output was not valid JSON")
        return None
    except Exception as e:
        logger.error(f"Error extracting metrics: {e}")
        return None


def update_leaderboard():
    """Generate human-readable leaderboard from results."""
    results = load_results_history()

    if not results:
        logger.info("No valid results yet")
        return

    with open(LEADERBOARD_FILE, "w") as f:
        # Header
        f.write("Iteration\tDataset\t\tPrimary Score\tSTS\tRetrieval\tStatus\n")
        f.write("=" * 80 + "\n")

        # Data
        for i, result in enumerate(results, 1):
            dataset = result.get("dataset", {}).get("name", "?")
            score = result.get("evaluation", {}).get("mteb_scores", {}).get("primary_score", 0)
            sts = result.get("evaluation", {}).get("mteb_scores", {}).get("sts_mean", 0)
            retrieval = result.get("evaluation", {}).get("mteb_scores", {}).get("retrieval_mean", 0)
            status = "✓" if result.get("evaluation", {}).get("contamination", {}).get("passed") else "✗"

            f.write(f"{i}\t{dataset:16s}\t{score:6.2f}\t\t{sts:5.2f}\t{retrieval:5.2f}\t{status}\n")

    logger.info(f"Updated leaderboard.tsv ({len(results)} runs)")


def commit_results():
    """Commit results to git."""
    try:
        subprocess.run(["git", "add", "results.jsonl"], check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "result: autonomous run completed"],
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "push"], check=True, capture_output=True)
        logger.info("Results committed and pushed to git")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git commit failed: {e}")


def main():
    """Main autonomous researcher loop."""
    iteration = 0

    logger.info("=" * 70)
    logger.info("Autonomous Embedding Researcher Starting")
    logger.info("=" * 70)

    while True:
        iteration += 1
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"Iteration {iteration} — {datetime.now().isoformat()}")
        logger.info("=" * 70)

        try:
            # 1. Load results history
            results = load_results_history()
            logger.info(f"Loaded {len(results)} valid results")

            # 2. Select next dataset
            next_dataset = select_next_dataset(results, iteration)
            logger.info(f"Selected: {next_dataset['name']} ({next_dataset['reason']})")

            # 3. Set env vars
            set_environment_variables(next_dataset)

            # 4. Launch training
            run_id = launch_training()
            if not run_id:
                logger.error("Failed to launch training, retrying in 60s...")
                time.sleep(60)
                continue

            # 5. Wait for completion
            logger.info(f"Waiting for run {run_id} to complete...")
            completed = wait_for_completion(run_id)

            if not completed:
                logger.error(f"Run {run_id} did not complete")
                # Continue to next iteration anyway
                time.sleep(60)
                continue

            # 6. Extract metrics (optional, for logging)
            metrics = extract_metrics(run_id)
            if metrics:
                logger.info(f"Run metrics extracted")

            # 7. Update leaderboard
            update_leaderboard()

            # 8. Commit results
            commit_results()

            logger.info(f"Iteration {iteration} complete")

        except KeyboardInterrupt:
            logger.info("Interrupted by user, exiting")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            time.sleep(60)
            continue

        # Wait before next iteration (30 sec)
        logger.info(f"Sleeping 30s before next iteration...")
        time.sleep(30)


if __name__ == "__main__":
    main()
