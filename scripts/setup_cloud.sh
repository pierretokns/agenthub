#!/bin/bash
set -euo pipefail

# Cloud Research Setup: Fully automated, polls for GPU availability
# Once GPUs available, creates disk → populates → launches orchestrator

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLOUD_ROOT="$SCRIPT_DIR/.."
DISK_NAME="embed-data"
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
        log_error "ah CLI not found. Install agenthub first"
        exit 1
    fi

    if [ -z "${PRIME_INTELLECT_API_KEY:-}" ]; then
        log_error "PRIME_INTELLECT_API_KEY not set"
        log_info "Set from Keychain: export PRIME_INTELLECT_API_KEY=\$(security find-generic-password -s primeintellect-api -w)"
        exit 1
    fi

    log_success "Prerequisites OK"
}

# Poll until GPU resources available
wait_for_gpu() {
    log_info "Polling for GPU availability..."
    echo ""

    poll_interval=30
    max_wait=86400  # 24 hours

    elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        # Check for any GPU availability
        gpu_count=$(prime availability list 2>/dev/null | grep -cE '\bL40|\bH100|\bA100|\bV100' || echo 0)

        if [ "$gpu_count" -gt 0 ]; then
            log_success "GPU resources available!"
            echo ""
            prime availability list 2>/dev/null | grep -E 'L40|H100|A100|V100' | head -5
            echo ""
            return 0
        fi

        elapsed_min=$((elapsed / 60))
        elapsed_hours=$((elapsed / 3600))

        if [ $elapsed_hours -gt 0 ]; then
            echo -ne "${YELLOW}✗${NC} No GPUs available (${elapsed_hours}h ${elapsed_min}m elapsed). Retrying in ${poll_interval}s...\r"
        else
            echo -ne "${YELLOW}✗${NC} No GPUs available (${elapsed_min}m elapsed). Retrying in ${poll_interval}s...\r"
        fi

        sleep "$poll_interval"
        elapsed=$((elapsed + poll_interval))
    done

    log_error "Timeout waiting for GPU resources (24h exceeded)"
    exit 1
}

# Create disk on cloud
create_disk() {
    log_info "Step 1: Creating persistent disk..."

    # Check if disk already exists
    log_info "  Checking for existing disk '$DISK_NAME'..."
    if prime disks list 2>/dev/null | grep -q "$DISK_NAME"; then
        log_warn "Disk '$DISK_NAME' already exists"
        DISK_ID=$(prime disks list 2>/dev/null | grep "$DISK_NAME" | head -1 | awk '{print $1}')
        log_success "Using existing disk: $DISK_ID"
    else
        log_info "  Creating 500 GB disk on massedcompute..."
        if prime disks create --name "$DISK_NAME" --size 500 -y 2>&1 | tee /tmp/disk_create.log; then
            sleep 2
            DISK_ID=$(prime disks list 2>/dev/null | grep "$DISK_NAME" | head -1 | awk '{print $1}')

            if [ -z "$DISK_ID" ]; then
                log_error "Disk created but could not retrieve ID"
                exit 1
            fi

            log_success "Disk created: $DISK_ID"
        else
            log_error "Failed to create disk"
            cat /tmp/disk_create.log
            exit 1
        fi
    fi

    # Update config
    if grep -q "^disk_id:" "$CONFIG_FILE"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^disk_id:.*|disk_id: \"$DISK_ID\"|" "$CONFIG_FILE"
        else
            sed -i "s|^disk_id:.*|disk_id: \"$DISK_ID\"|" "$CONFIG_FILE"
        fi
        log_success "Config updated"
    fi
}

# Populate disk with data
populate_disk_data() {
    log_info "Step 2: Populating disk with training data..."

    cd "$CLOUD_ROOT"

    if [ ! -f "autoresearch-cloud/scripts/populate_disk.py" ]; then
        log_error "populate_disk.py not found"
        exit 1
    fi

    log_info "  Downloading datasets (BRIGHT, FollowIR, CodeSearchNet, mMARCO)..."
    log_info "  Building contamination hashes from MTEB eval..."
    log_info "  Caching model weights..."
    log_info "  This may take 10-30 minutes..."
    echo ""

    # Run populate_disk.py with progress
    EMBED_DATA_DIR="/mnt/embed-data" python3 autoresearch-cloud/scripts/populate_disk.py 2>&1 | tee /tmp/populate.log | grep -E "Downloading|Saving|Disk population|error|Error" || true

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        log_error "populate_disk.py failed"
        tail -30 /tmp/populate.log
        exit 1
    fi

    log_success "Disk populated"

    if [ -f "/mnt/embed-data/contamination_report.json" ]; then
        log_success "Contamination report generated"
    fi

    echo ""
}

# Launch orchestrator
launch_orchestrator() {
    log_info "Step 3: Launching orchestrator..."

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

    # Save PID for easy management
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

# Display final status
show_status() {
    echo ""
    log_success "✓✓✓ Setup Complete! ✓✓✓"
    echo ""
    log_success "Cloud research system is now running:"
    echo ""
    log_info "Real-time monitoring:"
    log_info "  prime pods list                    # View active training pods"
    log_info "  ah read embed-results              # View experiment results"
    log_info "  tail -f logs/orchestrator.log      # Orchestrator logs"
    echo ""
    log_info "Management:"
    log_info "  kill \$(cat logs/orchestrator.pid) # Stop orchestrator"
    log_info "  prime pods list -k                 # Kill a specific pod"
    echo ""
    log_info "Metrics:"
    log_info "  wandb.ai/pierretokns/autoresearch-embed  # WandB dashboard"
    echo ""
}

# Main
main() {
    log_info "PrimeIntellect Cloud Research Setup"
    log_info "===================================="
    echo ""

    check_prerequisites
    echo ""

    wait_for_gpu
    echo ""

    create_disk
    echo ""

    populate_disk_data

    launch_orchestrator
    echo ""

    show_status
}

main "$@"
