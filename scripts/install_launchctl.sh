#!/bin/bash
# Install and configure cloud orchestrator as launchctl daemon
# Usage: bash scripts/install_launchctl.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_SOURCE="$REPO_DIR/launchctl/com.agenthub.cloud-orchestrator.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist"
LOG_DIR="$HOME/.local/var/log/agenthub"
SERVICE_NAME="com.agenthub.cloud-orchestrator"

echo "=== Cloud Orchestrator Launchctl Setup ==="
echo ""

# Step 1: Create log directory
echo "[1/5] Creating log directory..."
mkdir -p "$LOG_DIR"
echo "✓ Logs will be written to: $LOG_DIR"
echo ""

# Step 2: Verify environment variables
echo "[2/5] Verifying environment variables..."
if [ -z "$PRIME_INTELLECT_API_KEY" ]; then
    echo "⚠️  PRIME_INTELLECT_API_KEY not set in environment"
    echo "   Will attempt to read from Keychain..."
    PRIME_INTELLECT_API_KEY=$(security find-generic-password -s "primeintellect-api" -w 2>/dev/null || echo "MISSING")
fi

if [ "$PRIME_INTELLECT_API_KEY" = "MISSING" ]; then
    echo "❌ PRIME_INTELLECT_API_KEY not found in environment or Keychain"
    echo "   Please run: security add-generic-password -s 'primeintellect-api' -a 'pierre' -w 'pit_...'"
    exit 1
fi

echo "✓ PRIME_INTELLECT_API_KEY: ${PRIME_INTELLECT_API_KEY:0:20}..."

if [ -z "$WANDB_API_KEY" ]; then
    echo "⚠️  WANDB_API_KEY not set (will use placeholder)"
fi

if [ -z "$HF_TOKEN" ]; then
    echo "⚠️  HF_TOKEN not set (will use placeholder)"
fi

if [ -z "$AGENTHUB_API_KEY" ]; then
    echo "⚠️  AGENTHUB_API_KEY not set (will use placeholder)"
fi

echo ""

# Step 3: Check if plist source exists
echo "[3/5] Locating plist template..."
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "ℹ️  Plist template not found at $PLIST_SOURCE"
    echo "    Creating from scratch..."
    mkdir -p "$(dirname "$PLIST_SOURCE")"
fi

echo "✓ Using plist: $PLIST_SOURCE"
echo ""

# Step 4: Create or update plist with actual values
echo "[4/5] Installing plist to $PLIST_DEST..."

# Create a temporary plist with environment variables substituted
cat > "$PLIST_DEST" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>com.agenthub.cloud-orchestrator</string>

	<key>ProgramArguments</key>
	<array>
		<string>/usr/bin/env</string>
		<string>python3</string>
		<string>{{REPO_DIR}}/scripts/orchestrator.py</string>
	</array>

	<key>WorkingDirectory</key>
	<string>{{REPO_DIR}}</string>

	<key>StandardOutPath</key>
	<string>{{LOG_DIR}}/orchestrator.stdout.log</string>

	<key>StandardErrorPath</key>
	<string>{{LOG_DIR}}/orchestrator.stderr.log</string>

	<key>KeepAlive</key>
	<dict>
		<key>SuccessfulExit</key>
		<false/>
	</dict>

	<key>ThrottleInterval</key>
	<integer>60</integer>

	<key>EnvironmentVariables</key>
	<dict>
		<key>PRIME_INTELLECT_API_KEY</key>
		<string>{{PRIME_INTELLECT_API_KEY}}</string>

		<key>WANDB_API_KEY</key>
		<string>{{WANDB_API_KEY}}</string>

		<key>HF_TOKEN</key>
		<string>{{HF_TOKEN}}</string>

		<key>AGENTHUB_API_KEY</key>
		<string>{{AGENTHUB_API_KEY}}</string>

		<key>AGENTHUB_ADDR</key>
		<string>http://localhost:8000</string>

		<key>PATH</key>
		<string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>

		<key>HOME</key>
		<string>{{HOME}}</string>
	</dict>

	<key>RunAtLoad</key>
	<true/>

	<key>ProcessType</key>
	<string>Standard</string>

	<key>SoftResourceLimits</key>
	<dict>
		<key>NumberOfFiles</key>
		<integer>65536</integer>
	</dict>
</dict>
</plist>
EOF

# Replace placeholders
sed -i '' "s|{{REPO_DIR}}|$REPO_DIR|g" "$PLIST_DEST"
sed -i '' "s|{{LOG_DIR}}|$LOG_DIR|g" "$PLIST_DEST"
sed -i '' "s|{{PRIME_INTELLECT_API_KEY}}|$PRIME_INTELLECT_API_KEY|g" "$PLIST_DEST"
sed -i '' "s|{{WANDB_API_KEY}}|${WANDB_API_KEY:-PLACEHOLDER}|g" "$PLIST_DEST"
sed -i '' "s|{{HF_TOKEN}}|${HF_TOKEN:-PLACEHOLDER}|g" "$PLIST_DEST"
sed -i '' "s|{{AGENTHUB_API_KEY}}|${AGENTHUB_API_KEY:-PLACEHOLDER}|g" "$PLIST_DEST"
sed -i '' "s|{{HOME}}|$HOME|g" "$PLIST_DEST"

chmod 644 "$PLIST_DEST"
echo "✓ Plist installed to: $PLIST_DEST"
echo ""

# Step 5: Load the service
echo "[5/5] Loading launchctl service..."

# Unload if already loaded
if launchctl list "$SERVICE_NAME" &>/dev/null; then
    echo "  Unloading existing service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    sleep 1
fi

# Load
launchctl load "$PLIST_DEST"
echo "✓ Service loaded"
echo ""

# Verify
if launchctl list "$SERVICE_NAME" &>/dev/null; then
    echo "✅ Setup complete! Cloud orchestrator is now running as a daemon."
else
    echo "⚠️  Warning: service may not be running yet. Check with: launchctl list $SERVICE_NAME"
fi

echo ""
echo "=== Summary ==="
echo "Service: $SERVICE_NAME"
echo "Plist: $PLIST_DEST"
echo "Logs: $LOG_DIR"
echo ""
echo "=== Usage ==="
echo "Start:   launchctl start $SERVICE_NAME"
echo "Stop:    launchctl stop $SERVICE_NAME"
echo "Reload:  launchctl unload $PLIST_DEST && launchctl load $PLIST_DEST"
echo "Logs:    tail -f $LOG_DIR/orchestrator.stderr.log"
echo "Status:  launchctl list $SERVICE_NAME"
echo ""
echo "=== Next Steps ==="
echo "1. Update WANDB_API_KEY, HF_TOKEN, AGENTHUB_API_KEY in plist:"
echo "   vim $PLIST_DEST"
echo "2. Reload: launchctl unload $PLIST_DEST && launchctl load $PLIST_DEST"
echo "3. Monitor: tail -f $LOG_DIR/orchestrator.*.log"
