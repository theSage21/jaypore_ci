# 11 — Upstream Trigger

Re-run your app’s tests whenever an upstream library gets new commits.

## Repos

| Repo | Path | Role |
|------|------|------|
| **upstream-lib** | `/home/exedev/upstream-lib/` | Shared library (`mathlib.py` — `add`, `multiply`) |
| **downstream-app** | `/home/exedev/downstream-app/` | App that depends on the library |

## The symlink

```
downstream-app/.jci/upstream-lib  →  /home/exedev/upstream-lib
```

This symlink is how the app knows where its upstream dependency lives.

## How it works

1. `downstream-app/.jci/run.sh` resolves the `upstream-lib` symlink.
2. It reads the upstream repo’s `HEAD` commit.
3. It compares that against `.jci/upstream-last-commit` (saved from the previous run).
4. **If upstream has changed** — app tests run to verify compatibility.
5. **If upstream is unchanged** — CI exits early, nothing to do.

## Try it

```bash
# First run — upstream is "new", tests run
cd /home/exedev/downstream-app
git jci run

# Second run — upstream unchanged, skips
git jci run

# Simulate an upstream change
cd /home/exedev/upstream-lib
echo '# update' >> mathlib.py && git add mathlib.py && git commit -m 'update'

# Third run — detects upstream change, tests run again
cd /home/exedev/downstream-app
git jci run
```

## Adding more upstream repos

```bash
cd /home/exedev/downstream-app/.jci
ln -s /path/to/another-lib upstream-other
```

Extend `run.sh` to loop over all `upstream-*` symlinks if needed.
