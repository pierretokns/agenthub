# Quick Reference: Build, Push, and Relaunch

## Build all three environments locally

```bash
cd /Users/pierre/gourmand/agenthub

# Build and create .build.json artifacts
prime env build bright-retrieval --path environments
prime env build followir-retrieval --path environments
prime env build miracl-retrieval --path environments

# Verify .build.json was created
ls -la environments/*/proj/.build.json
```

**Expected output:**
```
Successfully built image for bright-retrieval
Successfully built image for followir-retrieval
Successfully built image for miracl-retrieval
```

---

## Push updated versions (0.1.0 → 0.1.1)

```bash
# Push each environment
cd /Users/pierre/gourmand/agenthub/environments/bright_retrieval && prime env push
cd /Users/pierre/gourmand/agenthub/environments/followir_retrieval && prime env push
cd /Users/pierre/gourmand/agenthub/environments/miracl_retrieval && prime env push
```

**Expected:** Each push should upload Docker image and increment version.

---

## Stop failed/running training runs

```bash
# Check status of all runs
prime rl status

# Stop specific failed/running runs
prime rl stop wg6mko1s5l1fok3ij57l3h96   # BRIGHT (failed)
prime rl stop b1k2g2sxenp3jyrxsbylj06b   # FollowIR (failed)
prime rl stop ve61qxdrpex7285m6y18cemm   # MIRACL (running, will fail)
```

---

## Relaunch training runs

```bash
# Relaunch all three with fixed environments
prime rl run configs/bright_baseline.toml
prime rl run configs/followir_baseline.toml
prime rl run configs/miracl_baseline.toml
```

Or use monitor script:
```bash
bash monitor_and_launch.sh
```

---

## Monitor training

```bash
# Get run IDs
prime rl status

# Stream logs for a specific run
prime rl logs <run-id> -f

# Check metrics after ~1000 steps
prime rl metrics <run-id>
```

---

## Troubleshooting

If you still see:
```
RuntimeError: OpenEnv project is missing .build.json
```

1. Check `.build.json` exists: `ls environments/bright_retrieval/proj/.build.json`
2. Verify `prime env build` exit code was 0: `echo $?`
3. Check Docker is running: `docker ps`
4. Rebuild and push again if needed

---

## Verification Checklist

- [ ] `prime env build bright-retrieval` exits 0 and creates `.build.json`
- [ ] `prime env build followir-retrieval` exits 0 and creates `.build.json`
- [ ] `prime env build miracl-retrieval` exits 0 and creates `.build.json`
- [ ] `prime env push` in each dir succeeds (no auth errors)
- [ ] Old failed runs stopped with `prime rl stop`
- [ ] `prime rl run configs/{bright,followir,miracl}_baseline.toml` all launched
- [ ] Log shows "Successfully installed environment" (not .build.json error)
- [ ] After 1000 steps, `prime rl metrics <id>` shows reward > 0 (not NaN)
