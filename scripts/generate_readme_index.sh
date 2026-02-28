#!/usr/bin/env bash
set -euo pipefail

README_FILE="${1:-README.md}"

if [[ ! -f "${README_FILE}" ]]; then
  echo "README file not found: ${README_FILE}" >&2
  exit 1
fi

python3 - "$README_FILE" <<'PY'
import sys
import re
from pathlib import Path

readme_path = Path(sys.argv[1])
text = readme_path.read_text(encoding="utf-8")

lines = text.splitlines()
dash_lines = [idx for idx, line in enumerate(lines) if line.strip() == '---']
if len(dash_lines) < 2:
    raise SystemExit("Expected at least two lines containing only '---' in README")

heading_pattern = re.compile(r'^(#{2,3})\s+(.*)$', re.MULTILINE)
headings = []
for match in heading_pattern.finditer(text):
    level = len(match.group(1))
    title = match.group(2).strip()
    if not title:
        continue
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug).strip('-')
    slug = re.sub(r'-+', '-', slug)
    if not slug:
        continue
    headings.append((level, title, f"#{slug}"))

index_lines = []
for level, title, anchor in headings:
    indent = '' if level == 2 else '    '
    index_lines.append(f"{indent}- [{title}]({anchor})")

first, second = dash_lines[:2]
result_lines = []
result_lines.extend(lines[:first + 1])
result_lines.append('')
if index_lines:
    result_lines.extend(index_lines)
result_lines.append('')
result_lines.extend(lines[second:])

new_text = "\n".join(result_lines)
if not new_text.endswith("\n"):
    new_text += "\n"

readme_path.write_text(new_text, encoding="utf-8")
PY
