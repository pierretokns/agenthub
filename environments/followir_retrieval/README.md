# followir-retrieval

### Overview
- **Environment ID**: `followir-retrieval`
- **Short description**: OpenEnv-backed environment using `vf.OpenEnvEnv`.
- **Tags**: openenv, tools, multi-turn

### Structure
This template enforces:
- `proj/` contains the OpenEnv project
- `proj/.build.json` contains the built image/runtime metadata

### Quickstart
Build and register the image:

```bash
uv run vf-build followir-retrieval
```

Run eval:

```bash
prime eval run followir-retrieval
```
