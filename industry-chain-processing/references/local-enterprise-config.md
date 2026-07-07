# Local Enterprise Data Config

## Config discovery order

Scripts read JSON config from:

1. `--config <path>` CLI argument
2. `INDUSTRY_CHAIN_CONFIG` environment variable
3. `HANDAAS_CONFIG` environment variable
4. `~/.industry-chain-processing/handaas.config.json`
5. `assets/config.example.json` only for dry-run examples

## Config shape

```json
{
  "handaas": {
    "base_url": "https://console.handaas.com",
    "integrator_id": "your_integrator_id",
    "secret_id": "your_secret_id",
    "secret_key": "your_secret_key",
    "products": {
      "工商照面": "product_id_for_business_profile",
      "招聘明细": "product_id_for_recruiting_detail",
      "知识产权统计": "product_id_for_ip_stats",
      "企业招投标信息": "product_id_for_bidding"
    }
  },
  "high_screen": {
    "url": "https://example.com/enterprise-search-endpoint",
    "product_id": "your_high_screen_product_id",
    "secret_id": "your_high_screen_secret_id",
    "secret_key": "your_high_screen_secret_key",
    "default_page_size": 20
  }
}
```

`products` values may be strings or objects with `product_id`.

## Safety

- Never commit real config.
- Never print secrets or signatures.
- Use `--dry-run` to verify request shape safely.
- Use `scripts/validate_config.py --allow-placeholders` for example config validation.
