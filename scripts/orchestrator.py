#!/usr/bin/env python3
"""
Cloud Orchestrator: launches, monitors, and coordinates cloud researchers on PrimeIntellect.

Responsibilities:
1. Launch L40/L40S pods via prime SDK (direct API calls, not CLI)
2. Assign experiments to nodes via embed-jobs channel
3. Monitor results via embed-results channel + wandb
4. Aggregate leaderboard from all nodes
5. Terminate completed pods with real IDs

Uses prime_cli SDK for direct API integration.
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
    image: str = "cuda_12_4_pytorch_2_5"  # Correct PrimeIntellect image name
    gpu_type: str = "L40"  # Free tier: L40/L40S (48GB VRAM)
    cpu_count: int = 14    # Free tier defaults
    memory_gb: int = 128
    disk_gb: int = 200     # Ephemeral OS disk (data on persistent disk)
    timeout_minutes: int = 90  # Shorter for free tier


class PrimeIntellectAPI:
    """Direct SDK wrapper for PrimeIntellect API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PRIME_INTELLECT_API_KEY", "")
        if not self.api_key:
            logger.warning("PRIME_INTELLECT_API_KEY not set; pod operations will fail")

        try:
            from prime_cli.core import APIClient
            from prime_cli.api.pods import PodsClient
            from prime_cli.api.disks import DisksClient

            self.client = APIClient(api_key=self.api_key)
            self.pods_client = PodsClient(self.client)
            self.disks_client = DisksClient(self.client)
            logger.info("Prime SDK initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import prime_cli SDK: {e}")
            logger.error("Install with: pip install prime_cli")
            raise

    def launch_pod(
        self,
        pod_config: PodConfig,
        env_vars: Dict[str, str],
        disk_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Launch a pod on PrimeIntellect using SDK.
        Returns: pod_id or None
        """
        logger.info(f"Launching pod: {pod_config.name}")

        # Build envVars array (required format by Prime API)
        env_array = [
            {"key": k, "value": v}
            for k, v in env_vars.items()
        ]

        # Build disks array
        disks_array = [disk_id] if disk_id else []

        # Construct pod payload (matches Prime API schema)
        pod_payload = {
            "pod": {
                "name": pod_config.name,
                "cloudId": "gpu_1x_l40s",  # massedcompute US L40S
                "gpuType": "L40S 48GB",
                "socket": "PCIe",
                "gpuCount": 1,
                "diskSize": pod_config.disk_gb,
                "vcpus": pod_config.cpu_count,
                "memory": pod_config.memory_gb,
                "image": pod_config.image,
                "dataCenterId": None,  # Let Prime pick optimal location
                "autoRestart": False,
                "envVars": env_array,
            },
            "provider": {"type": "massedcompute"},
            "disks": disks_array,
            "team": None,
        }

        try:
            result = self.pods_client.create(pod_payload)

            if result and result.get("id"):
                pod_id = result["id"]
                logger.info(f"Pod launched successfully: {pod_config.name} (ID: {pod_id})")
                return pod_id
            else:
                logger.error(f"Pod creation response missing ID: {result}")
                return None

        except Exception as e:
            logger.error(f"Failed to launch pod: {e}", exc_info=True)
            return None

    def get_pod_status(self, pod_id: str) -> Optional[Dict]:
        """
        Get pod status via SDK.
        Returns: {"status": "running"|"pending"|"completed"|"failed", ...}
        """
        try:
            result = self.pods_client.get(pod_id)
            if result:
                status = result.get("status", "unknown")
                logger.debug(f"Pod {pod_id} status: {status}")
                return {"status": status, **result}
            else:
                logger.warning(f"Pod {pod_id} not found")
                return None
        except Exception as e:
            logger.error(f"Failed to get pod status: {e}")
            return None

    def terminate_pod(self, pod_id: str) -> bool:
        """
        Terminate a pod via SDK.
        Returns: True if successful, False otherwise.
        """
        logger.info(f"Terminating pod: {pod_id}")
        try:
            result = self.pods_client.delete(pod_id)
            logger.info(f"Pod {pod_id} terminated")
            return True
        except Exception as e:
            logger.error(f"Failed to terminate pod {pod_id}: {e}")
            return False


class Orchestrator:
    """Main orchestration logic."""

    def __init__(self, config_path: Optional[str] = None):
        # Use provided path or compute relative to this script
        if not config_path:
            config_path = str(Path(__file__).parent.parent / "orchestrator_config.yaml")

        self.config = self._load_config(config_path)
        self.pi = PrimeIntellectAPI()
        self.active_pods: Dict[str, str] = {}  # {node_id: pod_id}
        self.completed_experiments: List[str] = []

        # Validate AGENTHUB_ADDR
        self.agenthub_addr = os.getenv("AGENTHUB_ADDR", "http://localhost:8000")
        if "localhost" in self.agenthub_addr or "127.0.0.1" in self.agenthub_addr:
            logger.warning(
                f"WARNING: AGENTHUB_ADDR is {self.agenthub_addr} — "
                "cloud pods cannot reach localhost. Set to a reachable address."
            )

    def _load_config(self, config_path: str) -> Dict:
        """Load orchestrator configuration."""
        if not Path(config_path).exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {
                "max_pods": 3,
                "disk_id": None,
                "experiment_queue": [
                    {
                        "name": "baseline-bright",
                        "config_key": "baseline_bright",
                    }
                ],
            }

        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}

    def run(self):
        """Main orchestration loop."""
        logger.info("Orchestrator started")

        disk_id = self.config.get("disk_id")
        if not disk_id:
            logger.warning("WARNING: No disk_id configured. Pods will not have persistent data.")
            logger.warning("Create a persistent disk first: prime disks create --name embed-data --size 500")

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

                if self._launch_experiment(node_id, exp, disk_id):
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

    def _launch_experiment(self, node_id: str, exp: Dict, disk_id: Optional[str]) -> bool:
        """Launch an experiment on a new pod."""
        logger.info(f"Launching experiment: {exp['name']} on {node_id}")

        # Environment variables to inject
        env_vars = {
            "NODE_ID": node_id,
            "PRIME_INTELLECT_API_KEY": os.getenv("PRIME_INTELLECT_API_KEY", ""),
            "AGENTHUB_API_KEY": os.getenv("AGENTHUB_API_KEY", ""),
            "AGENTHUB_ADDR": self.agenthub_addr,
            "WANDB_API_KEY": os.getenv("WANDB_API_KEY", ""),
            "HF_TOKEN": os.getenv("HF_TOKEN", ""),
            "EMBED_DATA_DIR": "/mnt/embed-data",  # Persistent disk mount point
            "HF_DATASETS_CACHE": "/mnt/embed-data/hf_cache",
            "TRANSFORMERS_CACHE": "/mnt/embed-data/hf_cache",
        }

        pod_config = PodConfig(
            name=f"researcher-{node_id}",
            gpu_type=self.config.get("gpu_type", "L40"),
            timeout_minutes=self.config.get("timeout_minutes", 90),
        )

        pod_id = self.pi.launch_pod(pod_config, env_vars, disk_id)

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
                logger.info(f"Posted job for {job['node']}: {job['experiment']}")
            else:
                # Fall back to local file if agenthub not available
                logger.warning(f"Failed to post to agenthub, storing locally: {result.stderr}")
                with open("jobs_pending.jsonl", "a") as f:
                    f.write(json.dumps(job) + "\n")
                logger.info(f"Stored job locally for {job['node']}: {job['experiment']}")
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
                            exp_name = res.get("name")
                            if exp_name and exp_name not in self.completed_experiments:
                                logger.info(f"New result: {exp_name} from {res.get('node')}")
                                logger.info(f"  nDCG@10: {res.get('nDCG@10', 'N/A')}")
                                self.completed_experiments.append(exp_name)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"Error reading results: {e}")

    def _cleanup_idle_pods(self):
        """Remove pods that have completed their experiments."""
        nodes_to_remove = []

        for node_id, pod_id in list(self.active_pods.items()):
            status = self.pi.get_pod_status(pod_id)

            if not status:
                logger.warning(f"Pod {pod_id} not found, removing from tracking")
                nodes_to_remove.append(node_id)
                continue

            pod_status = status.get("status", "")

            # If pod exited successfully, terminate it
            if pod_status in ["succeeded", "completed"]:
                logger.info(f"Pod {pod_id} completed, terminating")
                self.pi.terminate_pod(pod_id)
                nodes_to_remove.append(node_id)
            elif pod_status in ["failed", "error"]:
                logger.warning(f"Pod {pod_id} failed, terminating")
                self.pi.terminate_pod(pod_id)
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
