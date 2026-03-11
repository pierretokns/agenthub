#!/usr/bin/env python3
"""
Cloud Orchestrator: launches, monitors, and coordinates cloud researchers on PrimeIntellect.

Responsibilities:
1. Launch L40 pods via prime CLI (free tier)
2. Assign experiments to nodes via embed-jobs channel
3. Monitor results via embed-results channel + wandb
4. Aggregate leaderboard from all nodes
5. Terminate idle pods

Configuration: orchestrator_config.yaml (in agenthub root)
Free tier: 4 parallel L40 pods, 8 total experiments, ~60-90 min per experiment
"""

import os
import json
import time
import yaml
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PodConfig:
    """Cloud pod configuration."""
    name: str
    image: str = "pytorch:2.5-cuda12.1-runtime-ubuntu22.04"
    gpu_type: str = "L40"  # Free tier: L40 (48GB VRAM)
    cpu_count: int = 14    # Free tier defaults
    memory_gb: int = 128
    disk_gb: int = 625     # Free tier disk size
    timeout_minutes: int = 90  # Shorter for free tier


class PrimeIntellectAPI:
    """Wrapper around prime CLI."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PRIME_INTELLECT_API_KEY", "")
        if not self.api_key:
            logger.warning("PRIME_INTELLECT_API_KEY not set; pod operations will fail")

    def run_prime_command(self, cmd_list: List[str]) -> Dict:
        """Execute prime CLI command, return result."""
        try:
            result = subprocess.run(
                ["prime"] + cmd_list,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.error(f"prime command failed: {result.stderr}")
                return {}

            # Return stdout as-is (could be table, JSON, or text)
            return {"output": result.stdout} if result.stdout else {}
        except Exception as e:
            logger.error(f"Error running prime command: {e}")
            return {}

    def launch_pod(self, pod_config: PodConfig, env_vars: Dict[str, str]) -> Optional[str]:
        """
        Launch a pod on PrimeIntellect.
        Returns: pod_id or None
        """
        logger.info(f"Launching pod: {pod_config.name}")

        env_args = []
        for key, val in env_vars.items():
            env_args.extend(["--env", f"{key}={val}"])

        cmd = [
            "pods", "create",
            "--name", pod_config.name,
            "--image", pod_config.image,
            "--gpu-type", pod_config.gpu_type,
            "--vcpus", str(pod_config.cpu_count),
            "--memory", str(pod_config.memory_gb),
            "--disk-size", str(pod_config.disk_gb),
            *env_args,
            "--yes",
        ]

        result = self.run_prime_command(cmd)

        # Check if successful (will have output)
        if result.get("output"):
            # Generate synthetic pod_id from pod name (prime returns it in output)
            import uuid
            pod_id = str(uuid.uuid4())[:8]
            logger.info(f"Pod launched: {pod_config.name} (tracking as {pod_id})")
            return pod_id
        else:
            logger.error("Failed to launch pod")
            return None

    def get_pod_status(self, pod_id: str) -> Optional[Dict]:
        """Get pod status."""
        result = self.run_prime_command(["pods", "describe", pod_id])
        return result

    def terminate_pod(self, pod_id: str):
        """Terminate a pod."""
        logger.info(f"Terminating pod: {pod_id}")
        self.run_prime_command(["pods", "delete", pod_id])


class Orchestrator:
    """Main orchestration logic."""

    def __init__(self, config_path: str = "scripts/orchestrator_config.yaml"):
        self.config = self._load_config(config_path)
        self.pi = PrimeIntellectAPI()
        self.active_pods: Dict[str, str] = {}  # {node_id: pod_id}
        self.completed_experiments: List[str] = []

    def _load_config(self, config_path: str) -> Dict:
        """Load orchestrator configuration."""
        if not Path(config_path).exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {
                "max_pods": 3,
                "experiment_queue": [
                    {
                        "name": "baseline-bright-h100",
                        "config_key": "baseline_bright",
                    }
                ],
            }

        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}

    def run(self):
        """Main orchestration loop."""
        logger.info("Orchestrator started")

        max_pods = self.config.get("max_pods", 3)
        experiments = self.config.get("experiment_queue", [])

        exp_idx = 0

        while exp_idx < len(experiments):
            # Check active pods
            num_active = len(self.active_pods)

            if num_active < max_pods:
                # Launch new pod
                exp = experiments[exp_idx]
                node_id = f"node-{num_active + 1}"

                if self._launch_experiment(node_id, exp):
                    exp_idx += 1
                else:
                    logger.warning(f"Failed to launch experiment, retrying in 30s")
                    time.sleep(30)
                    continue

            # Monitor active pods
            self._monitor_results()
            self._cleanup_idle_pods()

            time.sleep(30)

        logger.info("All experiments queued. Waiting for completion...")
        while self.active_pods:
            self._monitor_results()
            self._cleanup_idle_pods()
            time.sleep(60)

        logger.info("Orchestration complete")
        self._finalize_leaderboard()

    def _launch_experiment(self, node_id: str, exp: Dict) -> bool:
        """Launch an experiment on a new pod."""
        logger.info(f"Launching experiment: {exp['name']} on {node_id}")

        # Environment variables to inject
        env_vars = {
            "NODE_ID": node_id,
            "PRIME_INTELLECT_API_KEY": os.getenv("PRIME_INTELLECT_API_KEY", ""),
            "AGENTHUB_API_KEY": os.getenv("AGENTHUB_API_KEY", ""),
            "AGENTHUB_ADDR": os.getenv("AGENTHUB_ADDR", "http://localhost:8000"),
            "WANDB_API_KEY": os.getenv("WANDB_API_KEY", ""),
            "HF_TOKEN": os.getenv("HF_TOKEN", ""),
        }

        pod_config = PodConfig(
            name=f"researcher-{node_id}",
            gpu_type=self.config.get("gpu_type", "H100_80GB"),
            timeout_minutes=self.config.get("timeout_minutes", 120),
        )

        pod_id = self.pi.launch_pod(pod_config, env_vars)

        if pod_id:
            self.active_pods[node_id] = pod_id

            # Post job assignment to embed-jobs channel
            job = {
                "node": node_id,
                "experiment": exp["name"],
                "config": exp.get("config", {}),
            }

            self._post_job(job)
            return True

        return False

    def _post_job(self, job: Dict):
        """Post job assignment to embed-jobs channel."""
        try:
            result = subprocess.run(
                [
                    "ah", "post", "embed-jobs",
                    json.dumps(job)
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                logger.info(f"Posted job for {job['node']}")
            else:
                logger.warning(f"Failed to post job: {result.stderr}")
        except Exception as e:
            logger.error(f"Error posting job: {e}")

    def _monitor_results(self):
        """Check embed-results channel for new results."""
        try:
            result = subprocess.run(
                ["ah", "read", "embed-results"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        try:
                            res = json.loads(line)
                            if res.get("name") not in self.completed_experiments:
                                logger.info(f"New result: {res.get('name')} from {res.get('node')}")
                                self.completed_experiments.append(res.get("name"))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"Error reading results: {e}")

    def _cleanup_idle_pods(self):
        """Remove pods that have completed their experiments."""
        nodes_to_remove = []

        for node_id, pod_id in self.active_pods.items():
            status = self.pi.get_pod_status(pod_id)

            if not status:
                nodes_to_remove.append(node_id)
                continue

            pod_status = status.get("status", "")

            # If pod exited with code 0, terminate it
            if pod_status in ["succeeded", "completed"]:
                logger.info(f"Pod {pod_id} completed, terminating")
                self.pi.terminate_pod(pod_id)
                nodes_to_remove.append(node_id)
            elif pod_status in ["failed", "error"]:
                logger.warning(f"Pod {pod_id} failed")
                nodes_to_remove.append(node_id)

        for node_id in nodes_to_remove:
            del self.active_pods[node_id]

    def _finalize_leaderboard(self):
        """Aggregate results from all nodes into unified leaderboard."""
        logger.info("Finalizing leaderboard...")

        all_results = []

        # Pull results from each node's branch via git DAG
        try:
            result = subprocess.run(
                ["ah", "leaves"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        try:
                            leaf = json.loads(line)
                            # Fetch node's results.jsonl
                            node_id = leaf.get("node")
                            # (In a real system, would git fetch + read results.jsonl)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"Error finalizing leaderboard: {e}")

        # Write leaderboard.jsonl
        leaderboard_path = Path("leaderboard.jsonl")
        with open(leaderboard_path, "a") as f:
            for res in all_results:
                f.write(json.dumps(res) + "\n")

        logger.info(f"Leaderboard saved to {leaderboard_path}")


if __name__ == "__main__":
    orchestrator = Orchestrator()
    try:
        orchestrator.run()
    except KeyboardInterrupt:
        logger.info("Orchestrator interrupted by user")
