# MCP and Enterprise Data Config

## Recommended mode: MCP data access

The skill treats `industry-chain-mcp-server` as a data-access MCP service. The MCP service exposes HandaaS existing interface wrappers only; the skill keeps industry-chain decomposition, keyword strategy, evidence scoring, and link recommendations in local scripts.

### Option A: official Remote MCP

After creating the `industry-chain-mcp-server` service on the platform, set either the token or the full URL:

```bash
export INDUSTRY_CHAIN_MCP_TOKEN="your_remote_mcp_token"
# or
export INDUSTRY_CHAIN_MCP_URL="https://mcp.handaas.com/industry-chain/industry_chain?token=${INDUSTRY_CHAIN_MCP_TOKEN}"
```

### Option B: local streamable-http MCP

Run the MCP server locally, then point the skill to the local endpoint:

```bash
git clone https://github.com/handaas/industry-chain-mcp-server
cd industry-chain-mcp-server
python -m venv mcp_env && source mcp_env/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: INTEGRATOR_ID / SECRET_ID / SECRET_KEY
python server/mcp_server.py streamable-http
```

In the skill shell:

```bash
export INDUSTRY_CHAIN_MCP_URL="http://127.0.0.1:8000/mcp"
```

### Skill-side checks

```bash
python scripts/validate_config.py
python scripts/mcp_client.py ping
python scripts/mcp_client.py list-tools
```

If `list-tools` works, the skill can use the MCP service without separately configuring local `handaas` credentials. Reports, policy analysis, enterprise positioning, evidence review, and keyword candidate recall work in this mode. Precise condition-group ES acceptance still requires an opened `high_screen` interface when the Remote MCP does not expose an equivalent product.

## MCP tools the skill may use

Use only the HandaaS interface-wrapper tools exposed by `industry-chain-mcp-server`:

- Enterprise discovery: `enterprise_get_keyword_search`, `advanced_filter_get_enterprise_count`, `advanced_filter_get_enterprise_list`
- Enterprise details: `enterprise_get_enterprise_base_info`, `enterprise_get_enterprise_profile`, `enterprise_get_enterprise_business_info`, `enterprise_get_enterprise_tags`, `enterprise_get_enterprise_holder_info`, `enterprise_get_enterprise_invest_info`, `enterprise_get_enterprise_branch_info`, `enterprise_get_enterprise_main_person_info`
- Supply-chain leads: `supply_get_down_stream_products`, `supply_get_down_stream_enterprises`
- Patent evidence: `patent_bigdata_patent_search`, `patent_bigdata_patent_stats`
- Bid evidence: `bid_bigdata_bid_win_stats`, `bid_bigdata_bidding_info`, `bid_bigdata_tender_stats`, `bid_bigdata_procurement_stats`, `bid_bigdata_bid_search`, `bid_bigdata_planned_projects`

Do not expect MCP tools for “build condition”, “search by skill condition”, or “link enterprises”. Those are skill workflows implemented locally by `build_condition.py`, `enterprise_search_preview.py`, `evidence_call.py`, and `link_enterprises.py`.

## Legacy local config discovery order

Use this only when no MCP endpoint is available or when explicitly passing `--local`.

Scripts read JSON config from:

1. `--config <path>` CLI argument
2. `INDUSTRY_CHAIN_CONFIG` environment variable
3. `HANDAAS_CONFIG` environment variable
4. `~/.industry-chain-processing/handaas.config.json`
5. `assets/config.example.json` only for dry-run examples

## Config shape

```json
{
  "mcp": {
    "url": "https://mcp.handaas.com/industry-chain/industry_chain?token={token}",
    "token": "your_remote_mcp_token_optional_if_url_has_no_token"
  },
  "handaas": {
    "base_url": "https://console.handaas.com",
    "integrator_id": "your_integrator_id",
    "secret_id": "your_secret_id",
    "secret_key": "your_secret_key",
    "products": {
      "工商照面": {"product_id": "your_real_product_id_for_business_profile"},
      "企业简介": {"product_id": "your_real_product_id_for_enterprise_profile"},
      "企业业务": {"product_id": "your_real_product_id_for_enterprise_business_info"},
      "企业标签": {"product_id": "your_real_product_id_for_enterprise_tags"},
      "招聘明细": {"product_id": "your_real_product_id_for_recruiting_detail"},
      "知识产权统计": {"product_id": "your_real_product_id_for_ip_stats"},
      "企业招投标信息": {"product_id": "your_real_product_id_for_bidding"}
    }
  },
  "high_screen": {
    "url": "https://example.com/enterprise-search-endpoint",
    "product_id": "your_real_product_id_for_enterprise_search",
    "secret_id": "your_high_screen_secret_id",
    "secret_key": "your_high_screen_secret_key",
    "default_page_size": 20
  }
}
```

If `mcp.url`/`mcp.token` or the MCP environment variables are valid, local `handaas` is optional. `high_screen` is also optional unless the workflow uses `--require-es` for precise node-linking acceptance.

`products` values may be strings or objects with `product_id`. Fill every `product_id` with the real product/商品 ID from the user's data-product console. Keep credentials local and do not commit account-specific config.

## Safety

- Never commit real config.
- Never print secrets, tokens, signatures, or signed request payloads.
- Use `--dry-run` to verify request shape safely.
- Use `scripts/validate_config.py --allow-placeholders` for example config validation.


## Error reporting rules

- If an upstream response says `产品不存在`, report the exact product alias or MCP tool that triggered it.
- If MCP parameter validation fails, report the tool name and invalid field, then retry with the minimal documented parameters when safe.
- If `list-tools` does not show HandaaS wrapper tools, update/restart `industry-chain-mcp-server` before testing the skill again.
- Do not hide interface warnings inside generic “查询失败”; separate missing product, parameter error, empty result, and upstream `请求异常`.
