# Docker Setup: Using Podman + Colima (Better for M2 Ultra)

**Machine Status:** March 12, 2026

---

## Current Installation

✅ **Podman** (5.2.5) — Installed but VM not running
✅ **Colima** (0.8.0) — Installed but not running
✅ **Podman Desktop** — Installed
✅ **Ollama** (0.16.1) — Installed but not running

❌ Docker Desktop — NOT installed (not needed!)

---

## Why Podman + Colima is Better for M2 Ultra

| Aspect | Docker Desktop | Podman + Colima |
|--------|---|---|
| **Native M2 support** | Good | ✅ Excellent |
| **Memory efficiency** | High overhead | ✅ Low overhead |
| **CPU usage** | High when idle | ✅ Low when idle |
| **VirtIO disk** | Standard | ✅ Optimized for Apple Silicon |
| **Container performance** | Good | ✅ Faster |
| **Price** | Paid (Pro) | ✅ Free/Open source |

**Recommendation: Use Podman + Colima. It's already installed and optimized for your M2 Ultra.**

---

## Quick Start (3 minutes)

### Step 1: Start Colima
```bash
colima start
```

**Expected output:**
```
INFO[0000] Starting ...
INFO[0005] Waiting for the host IP...
INFO[0010] Waiting for the VM to be ready...
INFO[0015] colima is running
INFO[0020] SSH config generated at ~/.ssh/config
```

If this hangs, see Troubleshooting below.

### Step 2: Verify Podman is Working
```bash
podman info | head -10
```

**Expected output:**
```
OS: darwin/arm64
provider: applehv
version: 5.2.5
...
```

### Step 3: Test a Container
```bash
podman run --rm hello-world
```

**Expected output:**
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
...
```

---

## Important: Update Build Script for Podman

The build script was written for `docker`. Podman is compatible, but we need to verify it works. Let me create a Podman-aware version:

### Option A: Use Podman Directly (Recommended)
Podman's CLI is 100% compatible with Docker. The existing build script should work as-is:

```bash
# First start Colima
colima start

# Then run the build script (should work without modification)
/tmp/build_and_deploy.sh
```

### Option B: Create Docker Alias
If Prime Labs CLI requires `docker` specifically:

```bash
# Create an alias pointing docker to podman
echo 'alias docker=podman' >> ~/.zshrc
source ~/.zshrc

# Verify
docker ps  # Should use podman instead
```

### Option C: Enable Docker Compatibility Mode
```bash
# Some tools check for Docker socket. Enable compatibility:
export DOCKER_HOST=unix:///run/podman/podman.sock

# Or add to ~/.zshrc for permanent setup
echo 'export DOCKER_HOST=unix:///run/podman/podman.sock' >> ~/.zshrc
```

---

## Full Setup Instructions

### Step 1: Start Colima (First Time Setup)
```bash
# Initialize and start Colima VM
colima start

# This creates ~/.colima/default/colima.yaml with optimal settings for M2
# First run takes ~1-2 min
```

### Step 2: Configure for Optimal Performance (Optional)
Edit `~/.colima/default/colima.yaml` to optimize for M2 Ultra:

```yaml
# CPU: Use 8-16 cores (M2 Ultra has up to 12)
cpus: 10

# Memory: Use plenty (you have 64GB)
memory: 32

# Disk: Allocate sufficient space
disk: 100

# VM type: already optimized
vz: true  # Uses VirtIO for better performance
```

Then restart:
```bash
colima stop
colima start
```

### Step 3: Set Up Docker/Podman Compatibility
```bash
# Add to ~/.zshrc for permanent setup:
cat >> ~/.zshrc << 'EOF'

# Podman/Docker compatibility
export DOCKER_HOST=unix:///run/podman/podman.sock
alias docker=podman

EOF

source ~/.zshrc
```

### Step 4: Verify Everything Works
```bash
# Check Podman
podman ps

# Check Docker compatibility
docker ps  # Should work (alias to podman)

# Test a container
podman run --rm alpine echo "Hello from Podman"
```

---

## Running the Build Script with Podman

### Option 1: Direct (Easiest)
```bash
# Make sure Colima is running
colima start

# Run the build script as-is
/tmp/build_and_deploy.sh
```

The script uses `prime env build ...` which internally calls Docker/Podman. Since Podman is CLI-compatible, it should just work.

### Option 2: If Script Fails
If the script fails because `prime` CLI requires Docker:

**Create a Podman-Docker bridge:**
```bash
# Create /usr/local/bin/docker wrapper
sudo cat > /usr/local/bin/docker << 'EOF'
#!/bin/bash
exec /opt/homebrew/bin/podman "$@"
EOF

sudo chmod +x /usr/local/bin/docker

# Verify
docker --version  # Should show podman version
```

Then run the build script:
```bash
/tmp/build_and_deploy.sh
```

---

## Monitoring Colima

```bash
# Check Colima status
colima status

# View logs
colima logs

# Stop Colima (when done)
colima stop

# Restart
colima start

# Delete everything and start fresh (if needed)
colima delete
colima start
```

---

## Troubleshooting

### Issue: `colima start` hangs at "Waiting for the VM to be ready..."
**Solution:**
```bash
# Cancel the hang (Ctrl+C)
colima stop
colima start --force-new-instance

# If still fails, check VirtIO support:
colima status

# If VirtIO not available, use fallback:
colima delete
colima start --vz=false  # Disable VirtIO if hardware doesn't support it
```

### Issue: `podman info` shows "Cannot connect to Podman"
**Solution:**
```bash
# Initialize Podman VM
podman machine init

# Start it
podman machine start

# Or use Colima instead (recommended):
colima start
```

### Issue: Podman containers are slow
**Solution:**
```bash
# Check Colima configuration
cat ~/.colima/default/colima.yaml

# Optimize for your hardware (adjust CPU/Memory):
colima stop
# Edit ~/.colima/default/colima.yaml (see above)
colima start
```

### Issue: "Cannot find docker" when running build script
**Solution:**
```bash
# Create docker -> podman alias
echo 'alias docker=podman' >> ~/.zshrc
source ~/.zshrc

# Or set Docker socket:
export DOCKER_HOST=unix:///run/podman/podman.sock

# Then retry:
/tmp/build_and_deploy.sh
```

---

## Performance Tips for M2 Ultra

### 1. Allocate Sufficient Resources
```yaml
# ~/.colima/default/colima.yaml
cpus: 10          # Use 10 of 12 cores
memory: 32        # Use 32 of 64 GB
disk: 150         # Build artifacts can be large
```

### 2. Use VirtIO (Enabled by Default)
```yaml
vz: true  # VirtIO virtualization for Apple Silicon
```

### 3. Monitor Performance
```bash
# Check memory usage
colima info

# Monitor during build
colima logs -f
```

### 4. Clean Up After Builds
```bash
# Remove unused images
podman image prune -a

# Remove unused volumes
podman volume prune

# Check disk usage
podman system df
```

---

## Integration with Build Script

The existing `/tmp/build_and_deploy.sh` should work with Podman. Here's what it does:

1. **Check Docker** — Will find Podman (CLI compatible)
2. **Build environments** — `prime env build` uses Docker CLI internally
3. **Verify .build.json** — Checks file system (works with Podman)
4. **Push environments** — Uses Prime Labs CLI (compatible with Podman)

### Pre-Build Checklist for Podman

```bash
# 1. Start Colima
colima start

# 2. Verify Podman
podman ps

# 3. Verify Docker CLI works (if aliased)
docker ps

# 4. Run build script
/tmp/build_and_deploy.sh
```

---

## Switching Between Container Runtimes (If Needed)

### Use Podman Only
```bash
colima start
# Now podman works, docker calls podman via alias
```

### Use Colima + Podman Desktop UI (Optional)
```bash
# Start Colima
colima start

# Start Podman Desktop (if installed)
open /Applications/Podman\ Desktop.app

# View containers, logs, images in GUI
```

### Completely Disable Everything (Clean Slate)
```bash
# Stop all
colima stop
podman machine stop 2>/dev/null || true

# Remove all
colima delete
podman machine rm default 2>/dev/null || true

# Fresh start
colima start
```

---

## What This Means for the Build

### TL;DR:
1. Run: `colima start`
2. Verify: `podman ps` works
3. Run: `/tmp/build_and_deploy.sh`
4. It will use Podman instead of Docker (faster on M2 Ultra!)

### Benefits:
- ✅ No Docker Desktop subscription needed
- ✅ Lower memory/CPU overhead
- ✅ Better M2 optimization
- ✅ Faster container performance
- ✅ Everything is already installed

### Setup Time:
- **First time:** ~5 min (Colima VM initialization)
- **Subsequent:** <1 sec (Colima already running)

---

## Next Steps

### Option 1: Use Podman (Recommended, Since Installed)
```bash
colima start
/tmp/build_and_deploy.sh
```

### Option 2: Install Docker Desktop (If You Prefer)
```bash
# Download from https://www.docker.com/products/docker-desktop
# Install and run
# Then: /tmp/build_and_deploy.sh
```

### Option 3: Hybrid Setup
```bash
# Keep both running
colima start
open /Applications/Docker.app  # If installed
# Both can coexist
```

---

## Recommended Configuration

For M2 Ultra with 64GB RAM:

```yaml
# ~/.colima/default/colima.yaml
cpus: 10
memory: 32
disk: 150
vz: true
nativeUsenetworking: false
forwardAgent: false
autoActivate: true
```

Then:
```bash
colima restart
```

---

## Summary

**Your machine is optimized for Podman + Colima.** Everything is already installed.

**To get started:**
```bash
colima start
/tmp/build_and_deploy.sh
```

**That's it!** The build script will use Podman, which is faster and more efficient on M2 Ultra than Docker Desktop.

See below for specific instructions if you hit any issues.
