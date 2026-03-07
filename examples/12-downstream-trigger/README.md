# 12 — Downstream Trigger

After a shared library’s tests pass, push CI into every downstream repo
that depends on it.

## Repos

| Repo | Path | Role |
|------|------|------|
| **core-lib** | `/home/exedev/core-lib/` | Shared library (`corelib.py` — `validate_email`, `slugify`) |
| **consumer-svc** | `/home/exedev/consumer-svc/` | Service that imports core-lib |

## The symlink

```
core-lib/.jci/downstream-consumer  →  /home/exedev/consumer-svc
```

This symlink tells core-lib where to push CI signals.

## How it works

1. `core-lib/.jci/run.sh` runs core-lib’s own tests.
2. If they pass, it finds every `.jci/downstream-*` symlink.
3. For each one, it resolves the symlink and runs `git jci run` in that repo.
4. If any downstream CI fails, the overall run fails.

## Try it

```bash
cd /home/exedev/core-lib
git jci run
```

You’ll see core-lib tests run, then consumer-svc CI gets triggered
automatically.

## Adding more downstream repos

```bash
cd /home/exedev/core-lib/.jci
ln -s /path/to/billing-svc downstream-billing
ln -s /path/to/admin-app downstream-admin
```

The `run.sh` discovers all `downstream-*` symlinks automatically — no
config file to edit.
