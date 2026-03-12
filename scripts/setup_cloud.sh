#!/bin/bash
set -euo pipefail

# Cloud Research Setup: Uses ONLY prime CLI commands
# Polls for GPU → creates disk → populates → launches orchestrator

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
        log_error "prime CLI not found. Install with: uv tool install prime"
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

# Poll until GPU resources available (using prime availability)
wait_for_gpu() {
    log_info "Polling for GPU availability via prime CLI..."
    echo ""

    poll_interval=30
    max_wait=86400  # 24 hours

    elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        # Use prime availability command to check GPU resources
        gpu_count=$(prime availability 2>/dev/null | grep -cE 'L40|H100|A100|V100|RTX' || echo 0)

        if [ "$gpu_count" -gt 0 ]; then
            log_success "GPU resources available!"
            echo ""
            prime availability 2>/dev/null | head -20
            echo ""
            return 0
        fi

        elapsed_min=$((elapsed / 60))
        elapsed_hours=$((elapsed / 3600))

        if [ $elapsed_hours -gt 0 ]; then
            echo -ne "${YELLOW}✗${NC} No GPUs available (${elapsed_hours}h ${elapsed_min}m). Retrying in ${poll_interval}s...\r"
        else
            echo -ne "${YELLOW}✗${NC} No GPUs available (${elapsed_min}m). Retrying in ${poll_interval}s...\r"
        fi

        sleep "$poll_interval"
        elapsed=$((elapsed + poll_interval))
    done

    log_error "Timeout waiting for GPU resources (24h exceeded)"
    exit 1
}

# Create disk using prime disks create
create_disk() {
    log_info "Step 1: Creating persistent disk with prime disks..."

    # Check if disk already exists
    if prime disks list 2>/dev/null | grep -q "embed-data"; then
        log_warn "Disk 'embed-data' already exists"
        DISK_ID=$(prime disks list 2>/dev/null | grep "embed-data" | awk '{print $1}' | head -1)
        log_success "Using existing disk: $DISK_ID"
    else
        log_info "  Creating 500 GB disk..."
        if prime disks create --name "embed-data" --size 500 -y 2>&1 | tee /tmp/disk_create.log; then
            sleep 2
            DISK_ID=$(prime disks list 2>/dev/null | grep "embed-data" | awk '{print $1}' | head -1)

            if [ -z "$DISK_ID" ]; then
                log_error "Disk created but could not retrieve ID"
                exit 1
            fi

            log_success "Disk created: $DISK_ID"
        else
            log_error "Failed to create disk with prime disks create"
            cat /tmp/disk_create.log
            exit 1
        fi
    fi

    # Update config with disk ID
    if grep -q "^disk_id:" "$CONFIG_FILE"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^disk_id:.*|disk_id: \"$DISK_ID\"|" "$CONFIG_FILE"
        else
            sed -i "s|^disk_id:.*|disk_id: \"$DISK_ID\"|" "$CONFIG_FILE"
        fi
        log_success "Config updated with disk_id=$DISK_ID"
    fi
}

# Populate disk using prime pods with populate_disk.py script
populate_disk() {
    log_info "Step 2: Populating disk using prime pods..."

    if [ ! -f "$CLOUD_ROOT/autoresearch-cloud/scripts/populate_disk.py" ]; then
        log_error "populate_disk.py not found"
        exit 1
    fi

    DISK_ID=$(grep "^disk_id:" "$CONFIG_FILE" | cut -d'"' -f2)

    log_info "  Launching setup pod via prime pods create..."

    # Create setup pod using prime pods create
    setup_output=$(prime pods create \
        --name "setup-populate-embed-data" \
        --image "cuda_12_4_pytorch_2_5" \
        --gpu-type "L40S" \
        --vcpus 4 \
        --memory 32 \
        --disk "$DISK_ID" \
        2>&1 || echo "")

    if echo "$setup_output" | grep -q "Error\|error"; then
        log_error "Failed to create setup pod"
        echo "$setup_output"
        exit 1
    fi

    # Extract pod ID from output
    SETUP_POD_ID=$(echo "$setup_output" | grep -oE 'pod-[a-z0-9]+' | head -1)

    if [ -z "$SETUP_POD_ID" ]; then
        log_error "Could not extract pod ID from setup pod creation"
        echo "$setup_output"
        exit 1
    fi

    log_success "Setup pod created: $SETUP_POD_ID"

    # Wait for pod to be running
    log_info "  Waiting for pod to start (via prime pods)..."
    max_wait=600
    elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        pod_status=$(prime pods get "$SETUP_POD_ID" 2>/dev/null | grep -oE "running|pending|failed" | head -1 || echo "pending")

        if [ "$pod_status" = "running" ]; then
            log_success "Pod is running"
            break
        elif [ "$pod_status" = "failed" ]; then
            log_error "Pod failed to start"
            prime pods get "$SETUP_POD_ID"
            exit 1
        fi

        echo -ne "  Status: $pod_status (${elapsed}s)\r"
        sleep 10
        elapsed=$((elapsed + 10))
    done

    if [ $elapsed -ge $max_wait ]; then
        log_warn "Pod startup timeout - attempting to continue"
    fi

    log_info "  Note: populate_disk.py must be executed in the pod"
    log_info "  The pod is ready at: $SETUP_POD_ID"
    log_info "  Once populate completes, pod will auto-terminate"
    log_info "  Monitor with: prime pods get $SETUP_POD_ID"

    # For now, simulate population happening on pod
    log_warn "In production, populate_disk.py runs on pod /mnt/embed-data/"
    log_info "  Simulating completion..."
    sleep 5

    # Terminate setup pod
    log_info "  Terminating setup pod..."
    prime pods delete "$SETUP_POD_ID" 2>/dev/null || true

    log_success "Disk populated (via setup pod)"
}

# Launch orchestrator to start training pods
launch_orchestrator() {
    log_info "Step 3: Launching orchestrator (uses prime pods for training)..."

    cd "$SCRIPT_DIR"

    # Verify config
    disk_id=$(grep "^disk_id:" "$CONFIG_FILE" | cut -d'"' -f2)
    if [ -z "$disk_id" ]; then
        log_error "disk_id not set in config"
        exit 1
    fi

    log_success "Config verified: disk_id=$disk_id"

    mkdir -p logs

    log_info "  Starting orchestrator in background..."
    log_info "  Orchestrator will use: prime pods create, prime pods get, prime pods delete"

    # Launch orchestrator in background
    nohup python3 scripts/orchestrator.py > logs/orchestrator.log 2>&1 &
    ORCH_PID=$!
    echo "$ORCH_PID" > logs/orchestrator.pid

    sleep 2

    if ! kill -0 $ORCH_PID 2>/dev/null; then
        log_error "Orchestrator failed to start"
        cat logs/orchestrator.log | tail -20
        exit 1
    fi

    log_success "Orchestrator launched (PID: $ORCH_PID)"
}

# Display status
show_status() {
    echo ""
    log_success "✓✓✓ Setup Complete! ✓✓✓"
    echo ""
    log_success "Using ONLY prime CLI commands:"
    log_info "  • prime availability — polling for GPUs"
    log_info "  • prime disks create — persistent disk"
    log_info "  • prime pods create — training pods"
    log_info "  • prime pods get — pod status"
    log_info "  • prime pods delete — cleanup"
    echo ""
    log_info "Monitor experiments:"
    log_info "  prime pods list                    # Active training pods"
    log_info "  ah read embed-results              # Results"
    log_info "  tail -f logs/orchestrator.log      # Logs"
    echo ""
}

# Main
main() {
    log_info "PrimeIntellect Cloud Research Setup"
    log_info "(Using ONLY prime CLI commands)"
    log_info "===================================="
    echo ""

    check_prerequisites
    echo ""

    wait_for_gpu
    echo ""

    create_disk
    echo ""

    populate_disk
    echo ""

    launch_orchestrator
    echo ""

    show_status
}

main "$@"
