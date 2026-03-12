#!/usr/bin/env python3
"""
Health check HTTP server for monitoring autonomous researcher.

Provides simple REST endpoints for checking system status:
  GET /health      → Returns {"status": "ok"} if system running
  GET /metrics     → Latest metrics and scores
  GET /leaderboard → Formatted leaderboard
  GET /status      → Full system status

Usage:
  python3 scripts/health_server.py              # Start on port 5000
  python3 scripts/health_server.py --port 8080  # Custom port

Then check:
  curl http://localhost:5000/health
  curl http://localhost:5000/metrics | jq
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import sys

try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler


RESULTS_FILE = Path("results.jsonl")
LEADERBOARD_FILE = Path("leaderboard.tsv")
LOG_FILE = Path("autonomous_researcher.log")


def get_latest_result() -> Optional[Dict]:
    """Get the most recent result."""
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


def get_metrics() -> Dict:
    """Get latest metrics."""
    latest = get_latest_result()

    if not latest:
        return {"status": "no_results", "message": "No training results yet"}

    eval_data = latest.get("evaluation", {})
    mteb = eval_data.get("mteb_scores", {})
    contam = eval_data.get("contamination", {})

    return {
        "status": "ok",
        "dataset": latest.get("dataset", {}).get("name", "?"),
        "primary_score": mteb.get("primary_score", 0),
        "sts_mean": mteb.get("sts_mean", 0),
        "retrieval_mean": mteb.get("retrieval_mean", 0),
        "contamination_passed": contam.get("passed", False),
        "contamination_rate": contam.get("overall_rate", 0),
    }


def get_leaderboard() -> Dict:
    """Get formatted leaderboard."""
    if not LEADERBOARD_FILE.exists():
        return {"status": "no_leaderboard"}

    with open(LEADERBOARD_FILE) as f:
        lines = f.readlines()

    leaderboard = []
    for i, line in enumerate(lines):
        if i < 2:  # Skip header and separator
            continue

        parts = line.strip().split("\t")
        if len(parts) >= 3:
            try:
                leaderboard.append({
                    "iteration": int(parts[0]),
                    "dataset": parts[1].strip(),
                    "primary_score": float(parts[2]),
                    "sts": float(parts[3]) if len(parts) > 3 else 0,
                    "retrieval": float(parts[4]) if len(parts) > 4 else 0,
                    "status": parts[5] if len(parts) > 5 else "?",
                })
            except (ValueError, IndexError):
                pass

    return {
        "status": "ok" if leaderboard else "empty",
        "count": len(leaderboard),
        "leaderboard": leaderboard,
    }


def is_running() -> bool:
    """Check if agent appears to be running."""
    if not LOG_FILE.exists():
        return False

    # Check if log was updated in last 5 minutes
    import time
    mtime = LOG_FILE.stat().st_mtime
    age = time.time() - mtime
    return age < 300  # 5 minutes


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health checks."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "running": is_running(),
            }
            self.wfile.write(json.dumps(response, indent=2).encode())

        elif self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            metrics = get_metrics()
            metrics["timestamp"] = datetime.now().isoformat()
            self.wfile.write(json.dumps(metrics, indent=2).encode())

        elif self.path == "/leaderboard":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            lb = get_leaderboard()
            lb["timestamp"] = datetime.now().isoformat()
            self.wfile.write(json.dumps(lb, indent=2).encode())

        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status = {
                "timestamp": datetime.now().isoformat(),
                "health": {"status": "ok", "running": is_running()},
                "latest_metrics": get_metrics(),
                "leaderboard_summary": {
                    "count": get_leaderboard().get("count", 0),
                    "status": get_leaderboard().get("status", "unknown"),
                },
            }
            self.wfile.write(json.dumps(status, indent=2).encode())

        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "status": "not_found",
                "path": self.path,
                "available": ["/health", "/metrics", "/leaderboard", "/status"],
            }
            self.wfile.write(json.dumps(response, indent=2).encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass  # Quiet mode


def main():
    """Start the health check server."""
    port = 5000

    # Parse arguments
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            try:
                port = int(sys.argv[idx + 1])
            except ValueError:
                print("Invalid port number")
                return

    server = HTTPServer(("localhost", port), HealthHandler)
    print(f"✅ Health check server running on http://localhost:{port}")
    print(f"   GET /health      → System status")
    print(f"   GET /metrics     → Latest scores")
    print(f"   GET /leaderboard → Formatted leaderboard")
    print(f"   GET /status      → Full status")
    print(f"\nPress Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")


if __name__ == "__main__":
    main()
