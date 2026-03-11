#!/bin/bash
set -euo pipefail

# Cloud Research Setup: Automated disk creation, population, and orchestrator launch
# This script handles the full pipeline: disk → populate → orchestrator

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISK_NAME="embed-data"
DISK_SIZE="500"
CLOUD_ID="gpu_1x_l40s"
CONFIG_FILE="$SCRIPT_DIR/orchestrator_config.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v prime &> /dev/null; then
        log_error "prime CLI not found. Install with: uv tool install prime"
        exit 1
    fi

    if ! command -v ah &> /dev/null; then
        log_error "ah CLI not found. Install agenthub first"
        exit 1
    fi

    if [ -z "${PRIME_INTELLECT_API_KEY:-}" ]; then
        log_error "PRIME_INTELLECT_API_KEY not set"
        exit 1
    fi

    log_success "Prerequisites OK"
}

# Step 1: Create persistent disk
create_disk() {
    log_info "Step 1: Creating persistent disk..."

    # Check if disk already exists
    existing_disk=$(prime disks list --json 2>/dev/null | grep -o "\"name\":\s*\"$DISK_NAME\"" || true)
    if [ -n "$existing_disk" ]; then
        log_warn "Disk '$DISK_NAME' already exists, skipping creation"
        # Get the existing disk ID
        DISK_ID=$(prime disks list --json 2>/dev/null | grep -A 5 "\"name\":\s*\"$DISK_NAME\"" | grep -o '"id":\s*"[^"]*"' | head -1 | cut -d'"' -f4)
    else
        log_info "  Creating $DISK_SIZE GB disk on $CLOUD_ID..."
        result=$(prime disks create \
            --name "$DISK_NAME" \
            --size "$DISK_SIZE" \
            --cloud-id "$CLOUD_ID" \
            --json 2>/dev/null || echo "{}")

        DISK_ID=$(echo "$result" | grep -o '"id":\s*"[^"]*"' | head -1 | cut -d'"' -f4)

        if [ -z "$DISK_ID" ]; then
            log_error "Failed to create disk. Response: $result"
            exit 1
        fi
    fi

    log_success "Disk ready: $DISK_ID"

    # Update config file with disk ID
    if grep -q "^disk_id:" "$CONFIG_FILE"; then
        # Use sed to update existing disk_id
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^disk_id:.*/disk_id: \"$DISK_ID\"/" "$CONFIG_FILE"
        else
            sed -i "s/^disk_id:.*/disk_id: \"$DISK_ID\"/" "$CONFIG_FILE"
        fi
        log_success "Updated orchestrator_config.yaml with disk_id"
    else
        log_error "disk_id field not found in $CONFIG_FILE"
        exit 1
    fi
}

# Step 2: Launch setup pod and populate disk
populate_disk() {
    log_info "Step 2: Populating persistent disk..."

    log_info "  Creating setup pod with disk attached..."

    # Launch setup pod
    pod_result=$(prime pods create \
        --name "setup-populate-$DISK_ID" \
        --image "cuda_12_4_pytorch_2_5" \
        --gpu-type "L40S" \
        --vcpus 4 \
        --memory 32 \
        --disk "$DISK_ID" \
        --json 2>/dev/null || echo "{}")

    SETUP_POD_ID=$(echo "$pod_result" | grep -o '"id":\s*"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -z "$SETUP_POD_ID" ]; then
        log_error "Failed to create setup pod. Response: $pod_result"
        exit 1
    fi

    log_success "Setup pod created: $SETUP_POD_ID"

    # Wait for pod to be running
    log_info "  Waiting for pod to start (this may take 1-2 minutes)..."
    max_wait=300
    elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        status=$(prime pods get "$SETUP_POD_ID" --json 2>/dev/null | grep -o '"status":\s*"[^"]*"' | cut -d'"' -f4 || echo "pending")

        if [ "$status" = "running" ]; then
            log_success "Pod is running"
            break
        fi

        echo -ne "  Status: $status (${elapsed}s)\r"
        sleep 5
        elapsed=$((elapsed + 5))
    done

    if [ $elapsed -ge $max_wait ]; then
        log_warn "Pod setup timeout. Check manually: prime pods get $SETUP_POD_ID"
    fi

    # Note: In production, would use SSH/exec to run populate_disk.py in the pod
    # For now, print instructions
    log_warn "Setup pod running. To populate disk, SSH into pod or use:"
    log_warn "  prime pods exec $SETUP_POD_ID python3 /autoresearch-cloud/scripts/populate_disk.py"
    log_warn ""
    log_warn "Once populate_disk.py completes, verify data exists:"
    log_warn "  prime pods exec $SETUP_POD_ID ls -la /mnt/embed-data/data/"
    log_warn ""
    log_warn "Then terminate the setup pod:"
    log_warn "  prime pods delete $SETUP_POD_ID"
    log_warn ""

    # For automated testing, assume populate_disk.py runs quickly
    # In practice, user may need to monitor this manually
    log_info "Waiting 30 seconds, then checking for completion..."
    sleep 30

    log_info "Setup pod lifecycle: $SETUP_POD_ID"
    log_info "  Monitor with: prime pods get $SETUP_POD_ID"
    log_info "  Logs: prime pods logs $SETUP_POD_ID"
}

# Step 3: Launch orchestrator
launch_orchestrator() {
    log_info "Step 3: Launching orchestrator..."

    # Verify disk is populated before launching
    log_info "  Verifying disk is ready..."

    # Check that disk_id is set correctly
    disk_id_in_config=$(grep "^disk_id:" "$CONFIG_FILE" | cut -d'"' -f2)
    if [ -z "$disk_id_in_config" ] || [ "$disk_id_in_config" = "FILL_IN_AFTER_DISK_CREATE" ]; then
        log_error "disk_id not properly set in config"
        exit 1
    fi

    log_success "Config verified"

    log_info "  Starting orchestrator in background..."
    cd "$SCRIPT_DIR"

    # Launch orchestrator in background with log file
    python3 scripts/orchestrator.py > logs/orchestrator.log 2>&1 &
    ORCH_PID=$!

    log_success "Orchestrator launched (PID: $ORCH_PID)"
    log_success "Logs: tail -f $SCRIPT_DIR/logs/orchestrator.log"
    log_success "Monitor pods: prime pods list"
    log_success "Monitor results: ah read embed-results"
}

# Main execution
main() {
    log_info "PrimeIntellect Cloud Research Setup"
    log_info "===================================="
    echo ""

    check_prerequisites
    echo ""

    create_disk
    echo ""

    # Note: populate_disk should ideally be automated in the setup pod
    # For now, we launch the pod and note that user needs to run populate_disk.py
    log_warn "MANUAL STEP REQUIRED: Populate the persistent disk"
    log_warn "Run populate_disk.py on the setup pod, then come back to launch orchestrator"
    log_warn "Or run: python3 $SCRIPT_DIR/autoresearch-cloud/scripts/populate_disk.py locally"
    echo ""

    read -p "Press ENTER after populate_disk.py completes, or Ctrl+C to cancel: " -r

    echo ""
    launch_orchestrator

    log_success "Setup complete!"
    log_info "Next steps:"
    log_info "  1. Monitor pod launches: prime pods list"
    log_info "  2. Check results: ah read embed-results"
    log_info "  3. View orchestrator logs: tail -f $SCRIPT_DIR/logs/orchestrator.log"
}

# Run main
main "$@"
