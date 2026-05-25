"""Regenerate the PEP 503 simple-index for brink-contract.

Walks getbrink/brink releases filtered by the `contract-v*` tag prefix,
extracts wheel + sdist asset URLs and their SHA256 digests, and writes a
PEP 503-compliant simple-index to pages/simple/brink-contract/index.html
(and a root listing to pages/simple/index.html).

Auth: requires GITHUB_TOKEN env var with `Contents: Read` scope on getbrink/brink.

Run: python scripts/generate_simple_index.py
"""

from __future__ import annotations

import html
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO = "getbrink/brink"
TAG_PREFIX = "contract-v"
PACKAGE_NAME = "brink-contract"
NORMALIZED_NAME = "brink-contract"  # PEP 503 normalization: already lowercase, hyphens
OUT_ROOT = Path(__file__).resolve().parents[1] / "pages" / "simple"

# Match wheel (PEP 427) and sdist filenames. brink-contract releases produce
# brink_contract-<version>-py3-none-any.whl and brink_contract-<version>.tar.gz.
WHEEL_RE = re.compile(r"^brink_contract-(?P<ver>[^-]+)-py3-none-any\.whl$")
SDIST_RE = re.compile(r"^brink_contract-(?P<ver>[^/]+)\.tar\.gz$")
SHA256_RE = re.compile(r"^([a-f0-9]{64})\s+(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class Artifact:
    filename: str
    url: str
    sha256: str | None  # None if SHA256SUMS asset missing for this release


def github_api(path: str, token: str) -> bytes:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "brink-contract-index/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_text(url: str, token: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/octet-stream",
            "User-Agent": "brink-contract-index/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def list_releases(token: str) -> list[dict]:
    import json
    payload = github_api(f"/repos/{REPO}/releases?per_page=100", token)
    return json.loads(payload)


def parse_sha256sums(text: str) -> dict[str, str]:
    """Parse a `sha256sum`-style file into {filename: hex_digest}."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = SHA256_RE.match(line)
        if m:
            digest, fname = m.groups()
            out[Path(fname).name] = digest.lower()
    return out


def extract_artifacts(release: dict, token: str) -> list[Artifact]:
    """Pull wheel + sdist + their SHA256 from a release's assets."""
    sha_map: dict[str, str] = {}
    for asset in release.get("assets", []):
        if asset["name"] == "SHA256SUMS":
            try:
                sha_map = parse_sha256sums(fetch_text(asset["browser_download_url"], token))
            except Exception as e:  # noqa: BLE001
                print(f"  warn: failed to fetch SHA256SUMS for {release['tag_name']}: {e}", file=sys.stderr)
            break

    out: list[Artifact] = []
    for asset in release.get("assets", []):
        name = asset["name"]
        if WHEEL_RE.match(name) or SDIST_RE.match(name):
            out.append(Artifact(
                filename=name,
                url=asset["browser_download_url"],
                sha256=sha_map.get(name),
            ))
    return out


def build_package_index_html(artifacts: list[Artifact]) -> str:
    """Build the per-package simple-index HTML (PEP 503)."""
    lines = [
        "<!DOCTYPE html>",
        '<html><head><meta name="pypi:repository-version" content="1.0">',
        f"<title>Links for {PACKAGE_NAME}</title></head>",
        "<body>",
        f"<h1>Links for {PACKAGE_NAME}</h1>",
    ]
    for art in artifacts:
        href = art.url
        if art.sha256:
            href = f"{href}#sha256={art.sha256}"
        lines.append(f'<a href="{html.escape(href, quote=True)}">{html.escape(art.filename)}</a><br>')
    lines.extend(["</body>", "</html>", ""])
    return "\n".join(lines)


def build_root_index_html(packages: list[str]) -> str:
    """Build the root simple-index HTML (PEP 503) listing all packages."""
    lines = [
        "<!DOCTYPE html>",
        '<html><head><meta name="pypi:repository-version" content="1.0">',
        "<title>Simple index</title></head>",
        "<body>",
        "<h1>Simple index</h1>",
    ]
    for pkg in packages:
        lines.append(f'<a href="{html.escape(pkg)}/">{html.escape(pkg)}</a><br>')
    lines.extend(["</body>", "</html>", ""])
    return "\n".join(lines)


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: GITHUB_TOKEN env var required", file=sys.stderr)
        return 1

    print(f"Fetching releases from {REPO} ...", file=sys.stderr)
    releases = list_releases(token)
    print(f"  got {len(releases)} releases total", file=sys.stderr)

    contract_releases = [r for r in releases if r["tag_name"].startswith(TAG_PREFIX)]
    print(f"  {len(contract_releases)} are contract-v* releases", file=sys.stderr)

    all_artifacts: list[Artifact] = []
    for rel in contract_releases:
        if rel.get("draft"):
            continue
        print(f"  scanning {rel['tag_name']} ...", file=sys.stderr)
        all_artifacts.extend(extract_artifacts(rel, token))

    print(f"Writing index for {len(all_artifacts)} artifacts", file=sys.stderr)
    pkg_dir = OUT_ROOT / NORMALIZED_NAME
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "index.html").write_text(build_package_index_html(all_artifacts))
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "index.html").write_text(build_root_index_html([NORMALIZED_NAME]))
    print(f"Wrote {pkg_dir / 'index.html'}", file=sys.stderr)
    print(f"Wrote {OUT_ROOT / 'index.html'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
