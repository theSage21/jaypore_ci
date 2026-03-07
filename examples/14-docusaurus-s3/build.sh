#!/bin/bash
# Simple build script that converts Markdown docs to static HTML.
# This simulates what Docusaurus (or any static-site generator) would produce.
#
# Usage: ./build.sh [source_dir] [output_dir]
#   source_dir  — directory containing .md files (default: docs)
#   output_dir  — where to write HTML output  (default: build)

set -euo pipefail

SRC_DIR="${1:-docs}"
OUT_DIR="${2:-build}"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# ── helper: wrap markdown in a minimal HTML page ──────────────────────────
md_to_html() {
    local md_file="$1"
    local title
    # Pull the first H1 as the page title, fall back to the filename.
    title=$(grep -m1 '^# ' "$md_file" | sed 's/^# //' || basename "$md_file" .md)

    cat <<-HEADER
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${title}</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; max-width: 48rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #1a1a1a; }
    h1,h2,h3 { margin-top: 1.5em; }
    code { background: #f4f4f4; padding: .15em .3em; border-radius: 3px; }
    pre  { background: #f4f4f4; padding: 1em; overflow-x: auto; border-radius: 4px; }
    a { color: #0969da; }
  </style>
</head>
<body>
HEADER

    if command -v pandoc &>/dev/null; then
        pandoc --from=markdown --to=html "$md_file"
    else
        # Bare-bones Markdown → HTML using sed (handles headings, bold,
        # inline code, links, list items, and paragraphs).
        sed -E \
            -e 's|^### (.+)|<h3>\1</h3>|' \
            -e 's|^## (.+)|<h2>\1</h2>|' \
            -e 's|^# (.+)|<h1>\1</h1>|' \
            -e 's|\*\*([^*]+)\*\*|<strong>\1</strong>|g' \
            -e 's|`([^`]+)`|<code>\1</code>|g' \
            -e 's|\[([^]]+)\]\(([^)]+)\)|<a href="\2">\1</a>|g' \
            -e 's|^- (.+)|<li>\1</li>|' \
            -e 's|^[0-9]+\. (.+)|<li>\1</li>|' \
            -e '/^$/s|.*|<br>|' \
            "$md_file"
    fi

    cat <<-FOOTER
</body>
</html>
FOOTER
}

# ── convert every .md file ────────────────────────────────────────────────
count=0
while IFS= read -r -d '' md; do
    rel="${md#"$SRC_DIR"/}"
    html_path="$OUT_DIR/${rel%.md}.html"
    mkdir -p "$(dirname "$html_path")"
    md_to_html "$md" > "$html_path"
    echo "  ✓ $md → $html_path"
    count=$((count + 1))
done < <(find "$SRC_DIR" -name '*.md' -print0 | sort -z)

echo ""
echo "Build complete: $count page(s) written to $OUT_DIR/"
