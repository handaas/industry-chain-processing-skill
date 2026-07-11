# Contributing

Codex and other coding agents must read [AGENTS.md](AGENTS.md) before changing ontology rules, MCP integration, ES conditions, evidence scoring, reports, or documentation.

## Development setup

Most scripts use only the Python standard library. Install optional MCP
dependencies when testing a local or remote MCP connection:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Checks

```bash
python -m unittest discover -s tests -v
python -m py_compile industry-chain-processing/scripts/*.py
python -m json.tool industry-chain-processing/assets/config.example.json >/dev/null
git diff --check
```

## Contribution boundaries

- Keep pure industry-chain reports separate from enterprise linking reports.
- Reuse project L1/L2/L3/L5 graph records before generating fallback ontology.
- Keep enterprises as link records, never graph children.
- MCP tools must remain wrappers around existing HandaaS interfaces.
- Web-collected facts must retain source, URL, and date.
- Never commit credentials, tokens, signatures, or customer data.

Add or update regression tests for behavior changes. Generated reports should
remain readable without agent context and should not expose debug fields.
