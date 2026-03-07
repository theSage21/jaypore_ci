#!/bin/bash
set -euo pipefail

# Install a git pre-commit hook that runs Jaypore CI before each commit.
#
# Usage:
#   ./install-hook.sh          # install in the current repo
#   ./install-hook.sh /path    # install in a specific repo

REPO_ROOT="${1:-$(git rev-parse --show-toplevel)}"
HOOK="${REPO_ROOT}/.git/hooks/pre-commit"

if [ -f "$HOOK" ]; then
    echo "A pre-commit hook already exists at $HOOK"
    echo "Back it up or remove it, then re-run this script."
    exit 1
fi

mkdir -p "$(dirname "$HOOK")"

cat > "$HOOK" << 'EOF'
#!/bin/bash
# Pre-commit hook installed by install-hook.sh
# Runs Jaypore CI lint checks before allowing a commit.

echo "Running Jaypore CI lint checks..."
if ! git jci run; then
    echo ""
    echo "Commit blocked: lint checks failed."
    echo "Fix the issues above, stage your changes, and try again."
    exit 1
fi
EOF

chmod +x "$HOOK"
echo "Installed pre-commit hook at $HOOK"
