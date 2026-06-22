"""Convert URL or local file to clean Markdown via markitdown.

Usage:
    python markitdown_convert.py <source> [--type url|file]

Output (JSON to stdout):
    {"title": "...", "markdown": "...", "source": "...", "source_type": "url|file"}

If --type is omitted, guesses based on source:
    - starts with http:// or https:// → url
    - otherwise → file
"""

import json
import os
import sys
from pathlib import Path

try:
    from markitdown import MarkItDown
except ImportError:
    print(
        json.dumps({
            "error": "markitdown not installed.",
            "fix": "pip install markitdown",
        })
    )
    sys.exit(1)


def convert(source: str, source_type: str) -> dict:
    md = MarkItDown()
    result = md.convert(source)
    title = (
        result.title
        or _extract_title_from_text(result.text_content)
        or _title_from_source(source, source_type)
    )
    return {
        "title": title.strip(),
        "markdown": result.text_content.strip(),
        "source": source,
        "source_type": source_type,
    }


def _extract_title_from_text(text: str) -> str | None:
    lines = text.strip().split("\n")
    for line in lines[:10]:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped and not stripped.startswith("http") and len(stripped) < 200:
            return stripped
    return None


def _title_from_source(source: str, source_type: str) -> str:
    if source_type == "file":
        return Path(source).stem
    # URL: fallback to domain or full url
    try:
        from urllib.parse import urlparse
        return urlparse(source).netloc or source
    except Exception:
        return source


def _guess_type(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        return "url"
    return "file"


def _parse_args(argv: list[str]) -> tuple[str, str]:
    source_type = ""
    source = ""
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--type":
            i += 1
            if i < len(argv):
                source_type = argv[i]
        elif not a.startswith("--"):
            source = a
        i += 1

    if not source_type:
        source_type = _guess_type(source)

    return source, source_type


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: python markitdown_convert.py <source> [--type url|file]",
        }))
        sys.exit(1)

    source, source_type = _parse_args(sys.argv[1:])
    result = convert(source, source_type)
    print(json.dumps(result, ensure_ascii=False))
