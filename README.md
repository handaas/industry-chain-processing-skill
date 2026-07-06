# industry-chain-processing-skill

A local Codex Skill for Chinese industry-chain processing: generate L1-L5 industry-chain ontology, build high-screen/Handaas enterprise filters for L5 nodes, query candidate companies with user-owned credentials, and return evidence-based enterprise-linking recommendations.

This repository is **not a hosted platform**. Users install the Skill locally and configure their own Handaas/high-screen credentials.

## Install

```bash
git clone https://github.com/your-name/industry-chain-processing-skill.git
mkdir -p ~/.codex/skills
cp -R industry-chain-processing-skill/industry-chain-processing ~/.codex/skills/
```

Restart Codex after installation if your client does not auto-refresh skills.

## Configure Handaas / high-screen

```bash
mkdir -p ~/.industry-chain-processing
cp ~/.codex/skills/industry-chain-processing/assets/config.example.json \
  ~/.industry-chain-processing/handaas.config.json
```

Edit `~/.industry-chain-processing/handaas.config.json` and fill in your own Handaas/high-screen credentials and product IDs.

The scripts discover config in this order:

1. `--config <path>`
2. `INDUSTRY_CHAIN_CONFIG`
3. `HANDAAS_CONFIG`
4. `~/.industry-chain-processing/handaas.config.json`

## Validate

```bash
python ~/.codex/skills/industry-chain-processing/scripts/validate_config.py
```

To validate the bundled example without real credentials:

```bash
python ~/.codex/skills/industry-chain-processing/scripts/validate_config.py \
  --config ~/.codex/skills/industry-chain-processing/assets/config.example.json \
  --allow-placeholders
```

## Dry-run examples

Build a condition group:

```bash
python ~/.codex/skills/industry-chain-processing/scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --output /tmp/evtol-condition.json
```

Preview a high-screen request shape without calling the network:

```bash
python ~/.codex/skills/industry-chain-processing/scripts/high_screen_preview.py \
  --filter-file /tmp/evtol-condition.json \
  --dry-run
```

Run a one-node enterprise-linking dry-run:

```bash
python ~/.codex/skills/industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --dry-run
```

## Real API usage

After filling real config, remove `--dry-run`.

```bash
python ~/.codex/skills/industry-chain-processing/scripts/high_screen_preview.py \
  --filter-file /tmp/evtol-condition.json \
  --page-size 10

python ~/.codex/skills/industry-chain-processing/scripts/handaas_call.py \
  --product 工商照面 \
  --keyword '<企业ID>' \
  --key-type nameId
```

Use evidence calls carefully because Handaas products may incur cost.

```bash
python ~/.codex/skills/industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --with-evidence
```

## Security

- Do not commit real `handaas.config.json`.
- Do not print or log `secret_id`, `secret_key`, signatures, tokens, or raw signed requests.
- Use `--dry-run` for request-shape debugging.
