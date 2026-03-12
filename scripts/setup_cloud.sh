#!/bin/bash
set -euo pipefail

# Cloud Research Setup: Uses prime sandbox for online execution
# Polls availability → creates sandbox → populates data → launches training

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLOUD_ROOT="$SCRIPT_DIR/.."
CONFIG_FILE="$SCRIPT_DIR/orchestrator_config.yaml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v prime &> /dev/null; then
        log_error "prime CLI not found"
        exit 1
    fi

    if ! command -v ah &> /dev/null; then
        log_error "ah CLI not found"
        exit 1
    fi

    if [ -z "${PRIME_INTELLECT_API_KEY:-}" ]; then
        log_error "PRIME_INTELLECT_API_KEY not set"
        exit 1
    fi

    log_success "Prerequisites OK"
}

# Wait for GPU availability
wait_for_gpu() {
    log_info "Polling for GPU availability..."

    poll_interval=30
    max_wait=86400  # 24 hours
    elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        gpu_count=$(prime availability 2>/dev/null | grep -cE 'L40|H100|A100|V100|RTX' || echo 0)

        if [ "$gpu_count" -gt 0 ]; then
            log_success "GPU resources available!"
            echo ""
            prime availability 2>/dev/null | head -15
            echo ""
            return 0
        fi

        elapsed_min=$((elapsed / 60))
        elapsed_hours=$((elapsed / 3600))

        if [ $elapsed_hours -gt 0 ]; then
            echo -ne "${YELLOW}✗${NC} No GPUs (${elapsed_hours}h ${elapsed_min}m). Retry in ${poll_interval}s...\r"
        else
            echo -ne "${YELLOW}✗${NC} No GPUs (${elapsed_min}m). Retry in ${poll_interval}s...\r"
        fi

        sleep "$poll_interval"
        elapsed=$((elapsed + poll_interval))
    done

    log_error "GPU timeout (24h exceeded)"
    exit 1
}

# Create sandbox for data population
populate_via_sandbox() {
    log_info "Step 1: Creating sandbox for data population..."

    # Create sandbox
    sandbox_output=$(prime sandbox create 2>&1)
    SANDBOX_ID=$(echo "$sandbox_output" | grep -oE 'sb-[a-z0-9]+' | head -1)

    if [ -z "$SANDBOX_ID" ]; then
        log_error "Failed to create sandbox"
        echo "$sandbox_output"
        exit 1
    fi

    log_success "Sandbox created: $SANDBOX_ID"

    # Upload populate_disk.py
    log_info "  Uploading populate_disk.py..."
    prime sandbox upload "$SANDBOX_ID" "$CLOUD_ROOT/autoresearch-cloud/scripts/populate_disk.py" /tmp/populate_disk.py

    # Install dependencies
    log_info "  Installing dependencies..."
    prime sandbox run "$SANDBOX_ID" "pip install -q datasets transformers huggingface-hub mteb pyyaml" || true

    # Run populate_disk.py
    log_info "  Populating disk with training data..."
    log_info "  (downloading datasets, building contamination hashes, caching model)"
    prime sandbox run "$SANDBOX_ID" "EMBED_DATA_DIR=/tmp/embed-data python3 /tmp/populate_disk.py"

    if [ $? -ne 0 ]; then
        log_error "populate_disk.py failed in sandbox"
        prime sandbox logs "$SANDBOX_ID" | tail -20
        prime sandbox delete "$SANDBOX_ID" || true
        exit 1
    fi

    # Download contamination report
    log_info "  Downloading results..."
    mkdir -p /tmp/cloud-data
    prime sandbox download "$SANDBOX_ID" /tmp/embed-data/contamination_report.json /tmp/cloud-data/ || true

    log_success "Data population complete"

    # Update config with dataset info
    if [ -f "/tmp/cloud-data/contamination_report.json" ]; then
        log_success "Contamination report downloaded"
    fi

    # Cleanup
    log_info "  Cleaning up sandbox..."
    prime sandbox delete "$SANDBOX_ID"

    log_success "Sandbox data population done"
}

# Create persistent sandbox for orchestrator
launch_orchestrator_sandbox() {
    log_info "Step 2: Creating sandbox for orchestrator..."

    # Create persistent sandbox
    orch_output=$(prime sandbox create 2>&1)
    ORCH_SANDBOX=$(echo "$orch_output" | grep -oE 'sb-[a-z0-9]+' | head -1)

    if [ -z "$ORCH_SANDBOX" ]; then
        log_error "Failed to create orchestrator sandbox"
        echo "$orch_output"
        exit 1
    fi

    log_success "Orchestrator sandbox: $ORCH_SANDBOX"

    # Save sandbox ID for monitoring
    mkdir -p "$SCRIPT_DIR/logs"
    echo "$ORCH_SANDBOX" > "$SCRIPT_DIR/logs/orch_sandbox.id"

    # Upload orchestrator code
    log_info "  Uploading orchestrator.py..."
    prime sandbox upload "$ORCH_SANDBOX" "$SCRIPT_DIR/scripts/orchestrator.py" /tmp/orchestrator.py

    # Install dependencies
    log_info "  Installing dependencies..."
    prime sandbox run "$ORCH_SANDBOX" "pip install -q pyyaml wandb" || true

    # Start orchestrator (background)
    log_info "  Starting orchestrator (background)..."
    prime sandbox run "$ORCH_SANDBOX" "nohup python3 /tmp/orchestrator.py > /tmp/orchestrator.log 2>&1 &"

    sleep 2

    # Verify running
    log_success "Orchestrator sandbox started: $ORCH_SANDBOX"
    log_info "  Monitor with: prime sandbox logs $ORCH_SANDBOX"
    log_info "  SSH access: prime sandbox ssh $ORCH_SANDBOX"
}

# Display final status
show_status() {
    echo ""
    log_success "✓✓✓ Setup Complete! ✓✓✓"
    echo ""
    log_success "Using prime sandbox for online execution:"
    log_info "  • prime sandbox create    → ephemeral VM for tasks"
    log_info "  • prime sandbox run       → execute code online"
    log_info "  • prime sandbox upload    → upload files"
    log_info "  • prime sandbox download  → download results"
    log_info "  • prime sandbox logs      → view execution logs"
    log_info "  • prime sandbox ssh       → direct access"
    echo ""
    log_info "Workflow:"
    log_info "  1. Data population sandbox (created & deleted)"
    log_info "  2. Persistent orchestrator sandbox"
    log_info "  3. Experiment pods (via orchestrator)"
    echo ""
    log_info "Monitor online research:"

    if [ -f "$SCRIPT_DIR/logs/orch_sandbox.id" ]; then
        ORCH_SANDBOX=$(cat "$SCRIPT_DIR/logs/orch_sandbox.id")
        log_info "  prime sandbox logs $ORCH_SANDBOX          # Orchestrator logs"
        log_info "  prime sandbox ssh $ORCH_SANDBOX           # SSH into sandbox"
    fi

    log_info "  ah read embed-results                    # Experiment results"
    log_info "  wandb.ai/pierretokns/autoresearch-embed  # Live metrics"
    echo ""
}

# Main
main() {
    log_info "PrimeIntellect Cloud Research"
    log_info "(Using prime sandbox for online)"
    log_info "=================================="
    echo ""

    check_prerequisites
    echo ""

    wait_for_gpu
    echo ""

    populate_via_sandbox
    echo ""

    launch_orchestrator_sandbox
    echo ""

    show_status
}

main "$@"
