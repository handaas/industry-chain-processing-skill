# Security Policy

## Sensitive configuration

Never commit Remote MCP tokens, `.env` files, `secret_id`, `secret_key`, API
signatures, signed requests, customer lists, or raw enterprise evidence.

Use `industry-chain-processing/assets/config.example.json` only as a
placeholder template. Store real configuration under
`~/.industry-chain-processing/handaas.config.json` or environment variables.

## Reporting

Report vulnerabilities privately to the repository maintainers. Do not post
credentials or customer data in public issues.

Security fixes target the latest default branch. Reinstall or refresh the
local skill after updating.
