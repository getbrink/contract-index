# contract-index

PEP 503 simple-index for the [brink-contract](https://github.com/getbrink/brink/tree/main/pkg/contract/python) Python package.

This repo hosts the `brink-contract` wheel index at https://getbrink.github.io/contract-index/simple/. Wheels themselves live as release assets on the private `getbrink/brink` repo; this index just points at them.

## How it works

1. A `contract-v*` tag pushed to `getbrink/brink` triggers `brink/.github/workflows/contract-release.yml`, which builds the wheel + sdist and creates a GitHub Release with them attached.
2. That workflow fires a `repository_dispatch` (event_type `contract-released`) at this repo.
3. `.github/workflows/regenerate-index.yml` re-runs `scripts/generate_simple_index.py`, which walks `getbrink/brink`'s releases via the GitHub API and writes a PEP 503-compliant simple-index to `docs/simple/brink-contract/index.html`.
4. GitHub Pages serves the index at https://getbrink.github.io/contract-index/simple/brink-contract/.

A daily cron also runs the regenerator as a self-heal.

## Install brink-contract

The simple-index is publicly readable. The wheel asset URLs it points at require a GitHub PAT with `Contents: Read` on `getbrink/brink`.

Configure the token (one-time):

```bash
# Add to ~/.netrc (chmod 600), or export inline per-shell:
cat >> ~/.netrc <<EOF
machine github.com
  login x-token
  password $BRINK_PYPI_TOKEN
EOF
chmod 600 ~/.netrc
```

Then install:

```bash
pip install \
    --index-url https://getbrink.github.io/contract-index/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    brink-contract
```

Or in `pyproject.toml` (uv):

```toml
[project]
dependencies = ["brink-contract>=0.1.2,<0.2.0"]

[[tool.uv.index]]
name = "getbrink"
url = "https://getbrink.github.io/contract-index/simple/"
explicit = true

[tool.uv.sources]
brink-contract = { index = "getbrink" }
```

## Token management

`BRINK_PYPI_TOKEN` is a fine-grained PAT scoped to `getbrink/brink` (`Contents: Read`). Rotated every 90 days. Brink design partners receive a per-customer scoped token via onboarding.

## Future

When `brink-contract` flips to public PyPI, consumer pyprojects drop the `[[tool.uv.index]]` block. This repo continues to serve historical wheels as a back-compat mirror, or is archived after ~6 months of no traffic.

## License

Apache-2.0.
