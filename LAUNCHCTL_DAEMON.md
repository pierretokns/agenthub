# Cloud Orchestrator Launchctl Daemon

Run the cloud orchestrator continuously as a background daemon on your Mac.

---

## Overview

The orchestrator can run as a macOS **launchctl** service that:
- Starts automatically on boot
- Restarts if it crashes
- Runs continuously in the background
- Logs to `~/.local/var/log/agenthub/`

This means your cloud experiments will keep running even if you close the terminal or restart your Mac.

---

## Installation

### Step 1: Update Environment Variables

Edit the plist to include your actual API keys:

```bash
# First, verify your keys are set
echo $PRIME_INTELLECT_API_KEY  # Should be pit_...
echo $WANDB_API_KEY
echo $HF_TOKEN
echo $AGENTHUB_API_KEY
```

### Step 2: Install the Daemon

```bash
cd /Users/pierre/gourmand/agenthub
bash scripts/install_launchctl.sh
```

This will:
1. Create log directory
2. Generate plist file with your environment
3. Load the service into launchctl
4. Verify it's running

### Step 3: Verify Installation

```bash
launchctl list com.agenthub.cloud-orchestrator
# Should show the service PID and status
```

---

## Usage

### Start the Daemon

```bash
bash scripts/manage_orchestrator.sh start
# or
launchctl start com.agenthub.cloud-orchestrator
```

### Stop the Daemon

```bash
bash scripts/manage_orchestrator.sh stop
# or
launchctl stop com.agenthub.cloud-orchestrator
```

### Restart the Daemon

```bash
bash scripts/manage_orchestrator.sh restart
```

### Check Status

```bash
bash scripts/manage_orchestrator.sh status
```

Output:
```
✓ com.agenthub.cloud-orchestrator is RUNNING

Details:
{
  "Label" = "com.agenthub.cloud-orchestrator";
  "PID" = 12345;
  "LastExitStatus" = 0;
}
```

### View Logs

```bash
# Stream all logs in real-time
bash scripts/manage_orchestrator.sh logs

# View error log only
bash scripts/manage_orchestrator.sh logs-error

# View output log only
bash scripts/manage_orchestrator.sh logs-out
```

### View Config

```bash
bash scripts/manage_orchestrator.sh config
# Shows plist location and how to edit it
```

---

## Configuration

The plist file is located at:
```
~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
```

To edit:
```bash
vim ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
```

After editing, reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
launchctl load ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
```

Or use the management script:
```bash
bash scripts/manage_orchestrator.sh restart
```

### Key Configuration Options

| Key | Value | Description |
|-----|-------|-------------|
| `ProgramArguments` | path to orchestrator.py | What to run |
| `WorkingDirectory` | agenthub root | Where to run it |
| `StandardOutPath` | stdout.log | Normal output |
| `StandardErrorPath` | stderr.log | Error output |
| `RunAtLoad` | true | Start on boot |
| `KeepAlive.SuccessfulExit` | false | Restart on exit |
| `ThrottleInterval` | 60 | Wait 60s before restart |

---

## Log Files

Logs are written to:
```
~/.local/var/log/agenthub/orchestrator.stdout.log
~/.local/var/log/agenthub/orchestrator.stderr.log
```

### Monitor in Real-Time

```bash
# All logs
tail -f ~/.local/var/log/agenthub/orchestrator.*.log

# Error log only
tail -f ~/.local/var/log/agenthub/orchestrator.stderr.log

# Follow for specific count of lines
tail -100f ~/.local/var/log/agenthub/orchestrator.stderr.log
```

### Log Rotation

Logs can grow large. You can rotate them manually:

```bash
# Archive and clear
mv ~/.local/var/log/agenthub/orchestrator.stdout.log ~/.local/var/log/agenthub/orchestrator.stdout.$(date +%s).log
mv ~/.local/var/log/agenthub/orchestrator.stderr.log ~/.local/var/log/agenthub/orchestrator.stderr.$(date +%s).log
```

Or use logrotate (if installed):
```bash
# Create ~/.local/var/log/agenthub/.logrotate
size 100M
rotate 5
compress
```

---

## Troubleshooting

### Daemon Won't Start

```bash
# Check plist syntax
plutil -lint ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
# Should output: "OK"

# Check if service is loading errors
launchctl load ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
```

### Daemon Keeps Crashing

Check logs for the error:
```bash
tail -50f ~/.local/var/log/agenthub/orchestrator.stderr.log
```

Common issues:
- **Missing API keys** — update plist with actual keys
- **Python path wrong** — verify Python installation
- **Directory permissions** — ensure `~/.local/var/log/agenthub/` is writable

### Python Not Found

Edit the plist to use absolute path to Python:

```bash
# Find Python path
which python3
# Output: /usr/local/bin/python3

# Edit plist and change <string>/usr/bin/env</string> to the actual path
vim ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
```

### API Key Errors

Update the plist with your actual keys:

```bash
# Edit
vim ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist

# Find and replace PLACEHOLDER with actual values
# Reload
launchctl unload ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
launchctl load ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
```

### Check Service Status in System

```bash
# See all running services
launchctl list | grep agenthub

# Get detailed info
launchctl list com.agenthub.cloud-orchestrator

# See recent exit status
launchctl list com.agenthub.cloud-orchestrator | grep LastExitStatus
```

---

## Boot Behavior

### Auto-Start on Boot

The daemon is configured with `RunAtLoad = true`, so it will automatically start when you:
- Log in to your Mac
- Reboot your Mac
- Restart after power loss

To disable auto-start on boot:

```bash
# Edit the plist
vim ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist

# Change <key>RunAtLoad</key><true/> to <false/>
# Reload
launchctl unload ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
launchctl load ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
```

---

## Restart Behavior

If the orchestrator crashes or exits, launchctl will:
1. Wait 60 seconds (`ThrottleInterval`)
2. Restart the process
3. Log any errors to stderr

This ensures continuous operation even if there are transient failures.

To disable auto-restart:

```bash
# Edit plist
vim ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist

# Change <dict><key>SuccessfulExit</key><false/></dict> to <true/>
```

---

## Uninstall

Remove the daemon:

```bash
bash scripts/manage_orchestrator.sh uninstall
# or
launchctl unload ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
rm ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
```

---

## Integration with Orchestrator

The daemon runs:
```bash
python /Users/pierre/gourmand/agenthub/scripts/orchestrator.py
```

All orchestrator features work identically:
- Launches 4 L40 pods
- Assigns experiments
- Monitors results
- Logs to WandB
- Aggregates leaderboard

---

## Quick Commands Reference

```bash
# Install
bash scripts/install_launchctl.sh

# Start
bash scripts/manage_orchestrator.sh start

# Stop
bash scripts/manage_orchestrator.sh stop

# Restart
bash scripts/manage_orchestrator.sh restart

# Status
bash scripts/manage_orchestrator.sh status

# Logs (real-time)
bash scripts/manage_orchestrator.sh logs

# Logs (error only)
bash scripts/manage_orchestrator.sh logs-error

# Edit config
bash scripts/manage_orchestrator.sh config
# Then: vim ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist
# Then: bash scripts/manage_orchestrator.sh restart

# Uninstall
bash scripts/manage_orchestrator.sh uninstall
```

---

## Tips

1. **Keep a terminal watching logs** while debugging:
   ```bash
   # Terminal 1: Watch logs
   bash scripts/manage_orchestrator.sh logs

   # Terminal 2: Restart and observe
   bash scripts/manage_orchestrator.sh restart
   ```

2. **Monitor remote WandB** while daemon runs:
   ```bash
   open https://wandb.ai/pierretokns/autoresearch-embed
   ```

3. **Check disk space** for logs:
   ```bash
   du -sh ~/.local/var/log/agenthub/
   ```

4. **Verify pod status** while daemon runs:
   ```bash
   watch -n 10 'prime pods list'
   ```

---

## Support

For issues, check:
1. **Logs**: `bash scripts/manage_orchestrator.sh logs-error`
2. **Status**: `bash scripts/manage_orchestrator.sh status`
3. **Plist validity**: `plutil -lint ~/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist`
4. **Orchestrator**: `DEPLOY_FREE_TIER.md`
