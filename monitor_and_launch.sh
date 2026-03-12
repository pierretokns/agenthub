#!/bin/bash
# Monitor training runs and auto-launch MIRACL when a slot opens

set -e

BRIGHT_RUN="wg6mko1s5l1fok3ij57l3h96"
FOLLOWIR_RUN="b1k2g2sxenp3jyrxsbylj06b"

echo "Monitoring training runs..."
echo "BRIGHT: $BRIGHT_RUN"
echo "FollowIR: $FOLLOWIR_RUN"
echo ""
echo "Waiting for a run to complete so MIRACL can launch..."
echo ""

while true; do
    # Check status of both runs
    bright_status=$(prime rl get $BRIGHT_RUN 2>/dev/null | grep -i status || echo "RUNNING")
    followir_status=$(prime rl get $FOLLOWIR_RUN 2>/dev/null | grep -i status || echo "RUNNING")

    running_count=$(prime rl list | grep -c "RUNNING\|PENDING" || echo "0")

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] BRIGHT: $(echo $bright_status | cut -d' ' -f2), FollowIR: $(echo $followir_status | cut -d' ' -f2), Active runs: $running_count"

    # If we have space for another run, launch MIRACL
    if [ "$running_count" -lt 2 ]; then
        echo "Space available! Launching MIRACL baseline..."
        cd /Users/pierre/gourmand/agenthub
        prime rl run configs/miracl_baseline.toml && echo "MIRACL launched successfully!"
        break
    fi

    sleep 30
done

echo ""
echo "All three baselines now training:"
prime rl list
