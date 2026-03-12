# miracl-retrieval

### Overview
- **Environment ID**: `miracl-retrieval`
- **Short description**: OpenEnv-backed environment using `vf.OpenEnvEnv`.
- **Tags**: openenv, tools, multi-turn

### Structure
This template enforces:
- `proj/` contains the OpenEnv project
- `proj/.build.json` contains the built image/runtime metadata

### Quickstart
Build and register the image:

```bash
uv run vf-build miracl-retrieval
```

Run eval:

```bash
prime eval run miracl-retrieval
```
