# MCP and Enterprise Data Config

## Recommended mode: MCP data access

The skill treats `industry-chain-mcp-server` as a data-access MCP service. The MCP service exposes HandaaS existing interface wrappers only; the skill keeps industry-chain decomposition, keyword strategy, evidence scoring, and link recommendations in local scripts.

Official project and deployment guide: [handaas/industry-chain-mcp-server](https://github.com/handaas/industry-chain-mcp-server). Open that README for local installation, environment variables, MCP client examples, and the current tool inventory.

### Option A: official Remote MCP

After creating the `industry-chain-mcp-server` service on the platform, set either the token or the full URL:

macOS / Linux:

```bash
export INDUSTRY_CHAIN_MCP_TOKEN="your_remote_mcp_token"
# or
export INDUSTRY_CHAIN_MCP_URL="https://mcp.handaas.com/industry-chain/industry_chain?token=${INDUSTRY_CHAIN_MCP_TOKEN}"
```

Windows PowerShell:

```powershell
$env:INDUSTRY_CHAIN_MCP_TOKEN = "your_remote_mcp_token"
# or
$env:INDUSTRY_CHAIN_MCP_URL = "https://mcp.handaas.com/industry-chain/industry_chain?token=$($env:INDUSTRY_CHAIN_MCP_TOKEN)"
```

### Option B: local streamable-http MCP

Run the MCP server locally, then point the skill to the local endpoint:

macOS / Linux:

```bash
git clone https://github.com/handaas/industry-chain-mcp-server
cd industry-chain-mcp-server
python3 -m venv mcp_env
source mcp_env/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
${EDITOR:-nano} .env
./start_mcp_server.sh
```

Windows PowerShell:

```powershell
git clone https://github.com/handaas/industry-chain-mcp-server
Set-Location industry-chain-mcp-server
py -3 -m venv mcp_env
Set-ExecutionPolicy -Scope Process Bypass
.\mcp_env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python .\server\mcp_server.py streamable-http
```

In a separate Skill shell, set the endpoint.

macOS / Linux:

```bash
export INDUSTRY_CHAIN_MCP_URL="http://127.0.0.1:8000/mcp"
```

Windows PowerShell:

```powershell
$env:INDUSTRY_CHAIN_MCP_URL = "http://127.0.0.1:8000/mcp"
```

### Skill-side checks

Run checks from the repository root. macOS/Linux uses `python industry-chain-processing/scripts/...`; Windows PowerShell uses `python .\industry-chain-processing\scripts\...`. See `os-operations.md` for complete commands.

If `list-tools` works, the skill can use the MCP service without separately configuring local `handaas` credentials. The current official MCP exposes `advanced_filter_get_enterprise_list`, so reports, policy analysis, enterprise positioning, evidence review, and complete condition-group ES recall all work with the platform token alone. Keyword fallback is only for older MCP deployments that do not expose this tool.

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
4. The current user's `.industry-chain-processing/handaas.config.json` under `$HOME` (macOS/Linux or Windows)
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
      "工商照面": {"product_id": "66dbccbec7a7e3460f5e613f"},
      "企业简介": {"product_id": "6682b0b370f56cb7d77701e0"},
      "企业业务": {"product_id": "66e55613ae988a28c6db9259"},
      "企业标签": {"product_id": "669e531ce1fd7bff82321d8d"},
      "招聘明细": {"product_id": "66b338e274bf098447db7f09"},
      "知识产权统计": {"product_id": "66a0e1e7983134b5bb828503"},
      "企业招投标信息": {"product_id": "66bf124bf134a4c21b4fc2fa"},
      "高筛企业清单": {
        "product_id": "690dcb1b9c9dc8d0ff3c40eb",
        "default_page_size": 50
      }
    }
  }
}
```

If `mcp.url`/`mcp.token` or the MCP environment variables are valid, local `handaas` is optional, including for `--require-es`. In local-direct mode, high-screen uses `handaas.products.高筛企业清单` and reuses the same HandaaS credentials as every other product.

`products` values may be strings or objects with `product_id`. The example uses stable public HandaaS product IDs and users should not replace them. Only account-specific URLs, integrator IDs, secret IDs, secret keys, and Remote MCP tokens remain local configuration and must not be committed.

Legacy top-level `high_screen` remains readable for migration only. Do not create a second `secret_id` / `secret_key`; move its product ID under `handaas.products`.

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
