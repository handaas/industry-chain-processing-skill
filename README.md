# 旷湖产业链分析 Skill

[![CI](https://github.com/handaas/industry-chain-processing-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/handaas/industry-chain-processing-skill/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个可被本地智能体使用的产业链分析 Skill / 工具包。用户只需要说“使用旷湖产业链分析，分析某个行业 / 赛道 / 企业名单”，智能体会自动完成产业链层级分析、企业线索挖掘、证据核验、挂链建议和报告生成。

> Skill 本身不托管用户数据或凭证。推荐通过平台创建 `industry-chain-mcp-server` Remote MCP 并使用 token；也支持连接本地部署的 `industry-chain-mcp-server`。MCP 服务只提供 HandaaS 已有接口封装，产业链拆解、企业挂链和证据评分由 Skill 本地完成。

## 目录

- [你可以直接怎么说](#你可以直接怎么说)
- [一句话安装调试](#一句话安装调试)
- [安装到本地智能体](#安装到本地智能体)
- [接入 MCP 服务（推荐）](#接入-mcp-服务推荐)
- [本地直连 HandaaS 数据接口（备用）](#本地直连-handaas-数据接口备用)
- [快速验证](#快速验证)
- [它会自动做什么](#它会自动做什么)
- [输出结果怎么看](#输出结果怎么看)
- [项目图谱联动（产业链分析报告）](#项目图谱联动产业链分析报告)
- [区域政策分析](#区域政策分析)
- [生成静态报告](#生成静态报告)
- [高级命令行用法](#高级命令行用法)
- [仓库结构](#仓库结构)
- [故障排查](#故障排查)

## 你可以直接怎么说

安装完成后，不需要记内部包名，也不需要输入专业接口术语。直接在你的智能体工具里说：

```text
使用旷湖产业链分析，分析低空经济产业链，输出重点环节、企业类型和招商线索。
```

更多例子：

```text
使用旷湖产业链分析，帮我找一批 eVTOL 整机制造相关企业，先模拟运行。
```

```text
使用旷湖产业链分析，围绕人形机器人产业链做企业线索挖掘，输出确认、待复核、剔除三类结果。
```

```text
使用旷湖产业链分析，判断下面这些企业分别适合挂到低空经济产业链的哪些细分环节：
1. xxx 公司
2. yyy 公司
```

```text
使用旷湖产业链分析，分析半导体设备产业链，先不要真实调用接口，只给我产业链结构和企业搜索策略。
```

```text
使用旷湖产业链分析，以智能汽车产业链为例，生成专业产业链分析报告；如需企业挂链，再单独生成自动驾驶节点企业挂链结果，并对“安徽中科星驰自动驾驶技术有限公司”做自动驾驶节点详细分析报告。
```

```text
使用旷湖产业链分析，分析“深圳市汇川技术股份有限公司”主要属于哪些产业链，并给出主归属与备选的 L2/L3/L5 环节及证据。
```

```text
使用旷湖产业链分析，分析智能汽车产业链在国家部委、广东、上海、江苏的政策情况；结合旷湖政策接口和联网搜索，对比各地政策重点。
```

你不需要理解内部层级、接口字段、数据产品或搜索参数；这些都由 Skill 在内部完成。

## 一句话安装调试

给普通用户最省事的方式：复制下面这段话到任意支持 Git / Shell / Python 的智能体工具里。Codex 只是例子，Claude Code、Gemini CLI、Cursor、Windsurf、Cline、OpenHands 等智能体也可以按同一段指令执行。

```text
请帮我安装并调试“旷湖产业链分析”：先完整读取 https://github.com/handaas/industry-chain-processing-skill 这个项目的 README.md，再克隆仓库并按 README 自动完成安装、配置文件创建、校验、模拟分析验证和示例 HTML 报告生成。若当前工具支持 Codex-compatible Skill，就把 industry-chain-processing/ 安装到对应 skills 目录；若不支持，就把该仓库作为本地工具包使用，并记住后续通过仓库脚本和 README 工作流来完成“使用旷湖产业链分析，...”类请求。请提醒我只在本地配置自己的企业数据接口参数，不要提交凭证；除非需要真实接口密钥，否则不要中断询问。
```

如果你使用 SSH 拉取仓库，也可以把地址换成：

```text
git@github.com:handaas/industry-chain-processing-skill.git
```

智能体读取 README 后应自动完成：

1. 克隆仓库。
2. 判断当前工具是否支持 Skill 目录安装。
3. 支持 Skill 时安装 `industry-chain-processing/`；不支持时保留仓库作为本地工具包。
4. 优先检查是否已有平台 Remote MCP token 或本地 MCP URL（`INDUSTRY_CHAIN_MCP_TOKEN` / `INDUSTRY_CHAIN_MCP_URL`）。
5. 没有 MCP 配置时再创建 `~/.industry-chain-processing/handaas.config.json` 作为本地直连备用配置。
6. 提醒用户 Remote MCP token、本地 MCP `.env` 或本地直连凭证都不要提交。
7. 运行校验、模拟分析和示例报告生成。
8. 告诉用户后续如何在当前智能体里说“使用旷湖产业链分析，...”。

## 安装到本地智能体

先克隆仓库，然后按操作系统执行对应命令。后续示例默认从仓库根目录运行，避免依赖固定安装路径。

### macOS / Linux

```bash
git clone https://github.com/handaas/industry-chain-processing-skill.git
cd industry-chain-processing-skill
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p "$HOME/.codex/skills"
rm -rf "$HOME/.codex/skills/industry-chain-processing"
cp -R industry-chain-processing "$HOME/.codex/skills/"
```

开发者希望代码修改后立即生效时，可以用软链接代替复制：

```bash
rm -rf "$HOME/.codex/skills/industry-chain-processing"
ln -sfn "$(pwd)/industry-chain-processing" \
  "$HOME/.codex/skills/industry-chain-processing"
```

### Windows PowerShell

```powershell
git clone https://github.com/handaas/industry-chain-processing-skill.git
Set-Location industry-chain-processing-skill
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$skillsRoot = Join-Path $HOME ".codex\skills"
$skillTarget = Join-Path $skillsRoot "industry-chain-processing"
New-Item -ItemType Directory -Force -Path $skillsRoot | Out-Null
Remove-Item -Recurse -Force $skillTarget -ErrorAction SilentlyContinue
Copy-Item -Recurse .\industry-chain-processing $skillTarget
```

开发者可以用目录联接代替复制：

```powershell
$source = (Resolve-Path .\industry-chain-processing).Path
Remove-Item -Recurse -Force $skillTarget -ErrorAction SilentlyContinue
New-Item -ItemType Junction -Path $skillTarget -Target $source | Out-Null
```

如果智能体不支持 Codex-compatible Skill 目录，也可以直接保留仓库作为本地工具包，让智能体读取本 README、`industry-chain-processing/SKILL.md` 和 `industry-chain-processing/references/`。

安装后重启对应智能体，或在支持热加载的客户端中刷新 Skill / 工具列表。

## 接入 MCP 服务（推荐）

`industry-chain-mcp-server` 是数据接入层。它的可用工具应当都是 HandaaS 已有接口封装，例如企业关键词搜索、企业基础信息、供应链下游企业、专利、招投标和高级筛选；产业链分析流程不放在 MCP 工具里，而由本 Skill 的脚本完成。

MCP 项目地址：**[handaas/industry-chain-mcp-server](https://github.com/handaas/industry-chain-mcp-server)**。本地部署、环境变量、客户端配置和完整工具说明请直接进入该项目查看 README。

如果你的 Python 环境还没有 MCP 客户端依赖，先安装：

macOS / Linux 使用 `python -m pip install -r requirements.txt`；Windows PowerShell 在虚拟环境激活后执行相同命令。

### 方式一：使用官方 Remote MCP

如果你已经在平台创建了 `industry-chain-mcp-server` 并拿到 token，不需要在本 Skill 中分别配置 `integrator_id`、`secret_id`、`secret_key`、企业搜索 URL 或各数据产品 ID。设置 token 即可：

macOS / Linux：

```bash
export INDUSTRY_CHAIN_MCP_TOKEN="<platform-token>"
```

Windows PowerShell：

```powershell
$env:INDUSTRY_CHAIN_MCP_TOKEN = "<platform-token>"
```

如果平台返回的是完整 Remote MCP URL：

macOS / Linux：

```bash
export INDUSTRY_CHAIN_MCP_URL="https://mcp.handaas.com/industry-chain/industry_chain?token=${INDUSTRY_CHAIN_MCP_TOKEN}"
```

Windows PowerShell：

```powershell
$env:INDUSTRY_CHAIN_MCP_URL = "https://mcp.handaas.com/industry-chain/industry_chain?token=$($env:INDUSTRY_CHAIN_MCP_TOKEN)"
```

### 方式二：连接本地部署的 MCP 服务

如果你希望本地部署 MCP 服务，再让 Skill 连接它：

macOS / Linux：

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

Windows PowerShell：

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

在 `.env` 中填入本地服务调用 HandaaS 所需的凭证：

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key
```

再在使用 Skill 的 shell 中指定本地 MCP 地址：

macOS / Linux：

```bash
export INDUSTRY_CHAIN_MCP_URL="http://127.0.0.1:8000/mcp"
```

Windows PowerShell：

```powershell
$env:INDUSTRY_CHAIN_MCP_URL = "http://127.0.0.1:8000/mcp"
```

本地 MCP 由你自己的 `.env` 持有凭证；Skill 侧只需要 `INDUSTRY_CHAIN_MCP_URL`。

### MCP 连接验证

无论使用官方 Remote MCP 还是本地 MCP，都用同一组命令验证：

macOS / Linux（仓库根目录）：

```bash
python industry-chain-processing/scripts/validate_config.py
python industry-chain-processing/scripts/mcp_client.py ping
python industry-chain-processing/scripts/mcp_client.py list-tools
```

Windows PowerShell（仓库根目录）：

```powershell
python .\industry-chain-processing\scripts\validate_config.py
python .\industry-chain-processing\scripts\mcp_client.py ping
python .\industry-chain-processing\scripts\mcp_client.py list-tools
```

`list-tools` 中应看到 HandaaS 接口封装类工具，例如：

- `enterprise_get_keyword_search`
- `enterprise_get_enterprise_base_info`
- `enterprise_get_enterprise_business_info`
- `enterprise_get_enterprise_tags`
- `supply_get_down_stream_products` / `supply_get_down_stream_enterprises`
- `advanced_filter_get_enterprise_count` / `advanced_filter_get_enterprise_list`
- `patent_bigdata_patent_search` / `patent_bigdata_patent_stats`
- `bid_bigdata_bidding_info` / `bid_bigdata_bid_search`
- `policy_bigdata_policy_search` / `policy_bigdata_policy_info` / `policy_bigdata_approved_project_stats`

之后正常使用：

```bash
python industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造"
```

脚本会自动优先使用 MCP。只有没有 MCP 配置，或显式传 `--local` 时，才走下面的本地直连接口配置。

仅配置 Remote MCP token 即可完成产业链报告、企业定位、企业证据复核、政策分析和关键词候选召回。如果发布的 Remote MCP 未提供完整高筛条件组接口，`link_enterprises.py` 会把候选召回标记为 `precision_limited`；需要严格 ES 挂链验收时使用 `--require-es`，并配置已开通的完整 `high_screen` 接口。

## 本地直连 HandaaS 数据接口（备用）

如果不使用官方 Remote MCP，也不启动本地 MCP，可以让 Skill 直接读取你本机的 HandaaS / high_screen 配置。只做产业链分析和模拟运行时可以先不填真实接口参数；要真实查询企业时再创建本地配置文件：

macOS / Linux（仓库根目录）：

```bash
mkdir -p "$HOME/.industry-chain-processing"
cp industry-chain-processing/assets/config.example.json \
  "$HOME/.industry-chain-processing/handaas.config.json"
${EDITOR:-nano} "$HOME/.industry-chain-processing/handaas.config.json"
export INDUSTRY_CHAIN_CONFIG="$HOME/.industry-chain-processing/handaas.config.json"
```

Windows PowerShell（仓库根目录）：

```powershell
$configRoot = Join-Path $HOME ".industry-chain-processing"
$configPath = Join-Path $configRoot "handaas.config.json"
New-Item -ItemType Directory -Force -Path $configRoot | Out-Null
Copy-Item .\industry-chain-processing\assets\config.example.json $configPath
notepad $configPath
$env:INDUSTRY_CHAIN_CONFIG = $configPath
```

配置文件示例：

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
      "企业招投标信息": {"product_id": "66bf124bf134a4c21b4fc2fa"}
    }
  },
  "high_screen": {
    "url": "https://example.com/enterprise-search-endpoint",
    "product_id": "690dcb1b9c9dc8d0ff3c40eb",
    "secret_id": "your_high_screen_secret_id",
    "secret_key": "your_high_screen_secret_key",
    "default_page_size": 20
  }
}
```

字段说明：

- `mcp.url` / `mcp.token` 是可选 MCP 入口；也可以完全通过 `INDUSTRY_CHAIN_MCP_TOKEN` / `INDUSTRY_CHAIN_MCP_URL` 配置。
- `handaas` 用于不经过 MCP 的本地证据接口备用模式；`high_screen` 用于需要完整 ES 条件组执行和 `--require-es` 验收的场景。
- 示例中的 `product_id` 是旷湖平台稳定公开产品 ID，不是账号凭证，用户无需替换。
- `handaas.products` 里的产品名是本地调用别名；Remote / 本地 MCP 模式不会读取这些商品 ID，而是使用 MCP 服务暴露的 HandaaS 接口封装工具。
- 如果你更喜欢简写，`products` 也支持 `"工商照面": "66dbccbec7a7e3460f5e613f"` 这种字符串形式。
- `secret_id`、`secret_key` 属于凭证，只放在本地配置文件里，不要提交到 Git。

脚本按以下顺序选择数据接入：

1. MCP 环境变量 `INDUSTRY_CHAIN_MCP_TOKEN` / `INDUSTRY_CHAIN_MCP_URL`
2. 命令行 `--config <path>` 中的 `mcp.url` / `mcp.token`
3. 本地直连配置：命令行 `--config <path>`、`INDUSTRY_CHAIN_CONFIG`、`HANDAAS_CONFIG`、`~/.industry-chain-processing/handaas.config.json`
4. 示例配置，仅用于 `--dry-run` / `--allow-placeholders`

可选环境变量：

macOS / Linux：

```bash
export INDUSTRY_CHAIN_CONFIG="$HOME/.industry-chain-processing/handaas.config.json"
# 或
export HANDAAS_CONFIG="$HOME/.industry-chain-processing/handaas.config.json"
```

Windows PowerShell：

```powershell
$configPath = Join-Path $HOME ".industry-chain-processing\handaas.config.json"
$env:INDUSTRY_CHAIN_CONFIG = $configPath
# 或
$env:HANDAAS_CONFIG = $configPath
```

如需强制不用 MCP、只测本地直连凭证，脚本支持 `--local`。

## 快速验证

验证真实配置：

```bash
python industry-chain-processing/scripts/validate_config.py
```

只验证示例配置，不要求真实凭证：

```bash
python industry-chain-processing/scripts/validate_config.py \
  --config industry-chain-processing/assets/config.example.json \
  --allow-placeholders
```

预期结果：

```json
{
  "ok": true,
  "errors": [],
  "warnings": ["...占位值提示..."]
}
```

如果 `ok` 为 `false`，先按 `errors` 修复配置。

## 它会自动做什么

当用户说“使用旷湖产业链分析...”时，Skill 会在内部完成以下步骤：

1. **理解业务场景**：判断用户要做产业链研究、企业线索挖掘、企业归位、招商筛选、证据核验还是报告生成。
2. **复用项目图谱**：如果当前存在 `industry-chain-map` 项目，优先读取 L1/L2/L3/L5 图谱、节点记录和高筛条件组；已有企业挂链记录只在单独挂链报告中使用。
3. **映射标准节点**：把“智能汽车 / 自动驾驶”这类自然表达映射到项目标准产业链和 L5 节点，例如“智能网联汽车 / 自动驾驶解决方案”。
4. **企业自动归位**：只有企业名称时，先解析企业主体，再以主营产品、业务标签、专利和招投标证据扫描全部项目 L5 节点，输出主归属及接近的备选产业链。
5. **联网增强报告摘要**：生成专业产业链分析报告时，可联网收集政策、市场、技术路线、商业化进展等权威背景，用于“报告摘要”和“产业背景与分析依据”。
6. **分析区域政策**：用户询问各地政策时，结合 `policy_bigdata_policy_search`、政策详情接口和联网搜索，对比国家部委、省市区政策重点、支持维度和代表性政策。
7. **拆解或补全产业链**：项目图谱没有覆盖时，再按“产业主题 -> 价值环节 -> 细分模块 -> 可匹配企业的产品 / 技术 / 服务 / 能力”生成补充结构。
8. **选择分析重点**：自动挑出最适合找企业、招商或核验的细分环节。
9. **生成搜索策略**：自动扩展业务词、同义词、场景词、岗位词、专利词、招投标词和排除词。
10. **查询企业线索**：如果 MCP 或本地接口配置可用，查询候选企业；如果没有配置，则输出模拟请求和后续配置提示。
11. **核验证据**：结合工商、招聘、知识产权、招投标等证据判断企业是否真的匹配。
12. **输出建议**：给出确认、待复核、剔除，以及下一步补充关键词或排除噪声的建议。
13. **生成报告**：用户需要交付或展示时，可直接生成离线 HTML 或 Markdown 报告；产业链分析报告、企业产业链定位报告、区域政策分析报告、企业挂链报告与指定企业节点报告分别生成。

默认原则：

- 用户只需要给行业、赛道、企业名单或业务目标。
- 不要求用户提供内部层级、接口字段、数据产品或搜索参数。
- 真实接口可能产生费用；不确定时先模拟运行。
- 企业只作为候选结果，不混入产业链结构。

## 输出结果怎么看

常见输出包括：

| 字段 | 含义 |
| --- | --- |
| `industry_map` | 产业链结构和重点细分环节 |
| `project_graph_summary` | 当前项目图谱口径、产业链 ID、L2/L3/L5 数量和候选企业缓存 |
| `node_mapping` | 用户输入的行业/节点映射到项目标准产业链和 L5 节点的结果 |
| `level_definitions` | L1/L2/L3/L4/L5 的详细解释口径 |
| `market_context` | 联网收集的政策、市场、技术或商业化背景，用于专业报告摘要和分析依据 |
| `project_graph_tree` | 用于静态 HTML 图谱展示的 L1/L2/L3/L5 树 |
| `project_node_records` | 项目节点 ID、路径、高筛条件来源和关键词 |
| `hierarchy_analysis` | L2/L3/L5 层级结构分析 |
| `analysis_framework` | 层级完整性、节点边界、价值传导等分析维度 |
| `regional_policy_analysis` | 各地区政策数量、重点方向、主要机构和区域政策解读 |
| `policy_dimensions` | 资金补贴、试点示范、技术研发、基础设施、监管规范等政策支持维度 |
| `policy_items` | 旷湖政策库和联网搜索归一后的代表性政策/依据 |
| `primary_position` | 单个企业的主归属产业链及 L2/L3/L5 路径、综合分、置信度和证据来源 |
| `chain_ranking` | 企业在全部项目产业链中的匹配排序及每条链的最佳节点 |
| `node_ranking` | 企业可能覆盖的 L5 节点、完整路径、匹配分和角色校准说明 |
| `evidence_summary` | 企业定位所用 HandaaS 数据产品的可用状态、错误、信号数量和代表性证据 |
| `search_strategy` | 企业搜索思路，仅企业挂链报告需要 |
| `candidates` | 候选企业样本和数量，仅企业挂链报告需要 |
| `evidence` | 工商、业务、标签、专利、招投标等证据，仅企业定位、企业挂链或指定企业节点报告需要 |
| `decision` | `confirmed`、`uncertain`、`rejected`，仅企业挂链或指定企业节点报告需要 |
| `next_actions` | 后续建议，例如补充排除词、人工复核、真实接口查询 |

决策含义：

| decision | 含义 | 建议动作 |
| --- | --- | --- |
| `confirmed` | 有较强证据表明企业匹配该细分环节 | 可确认挂链 |
| `uncertain` | 有相关迹象但证据不足或边界不清 | 人工复核 |
| `rejected` | 明显不相关或被噪声召回 | 剔除并补充排除词 |


## 项目图谱联动（产业链分析报告）

当你要生成专业产业链分析报告或图谱层级展示时，Skill 会优先复用当前可用的 `industry-chain-map` 项目数据，而不是重新编一套通用产业链结构。产业链分析报告只关注层级和分析，不输出企业挂链结果。

### 配置项目根目录

如果你的项目就在默认同级目录，通常不用配置；为了让其他环境也稳定复用，建议显式设置：

macOS / Linux（先进入图谱项目目录）：

```bash
cd ../industry-chain-map
export INDUSTRY_CHAIN_PROJECT_ROOT="$(pwd)"
cd -
```

Windows PowerShell（先进入图谱项目目录）：

```powershell
Push-Location ..\industry-chain-map
$env:INDUSTRY_CHAIN_PROJECT_ROOT = (Get-Location).Path
Pop-Location
```

### 会复用哪些项目数据

优先读取项目 SQLite 归档：

- `.data/industry-chain-archive.sqlite`
- `chain_definitions`：标准产业链名称、产业链 ID、节点数、候选企业缓存数、当前图谱 JSON。
- `canonical_nodes` / `chain_node_edges`：L1/L2/L3/L5 标准节点和路径。
- `high_screen_condition_groups`：节点高筛条件组、关键词和来源。
- `enterprise_node_links`：已有候选/确认企业挂链记录；只在企业挂链报告或指定企业节点报告中使用，产业链分析报告不展示。

如果 SQLite 不存在，再读取 `src/data/industries/*.json` 静态图谱。

### 固定口径

- 图谱层级使用 L1/L2/L3/L5。
- L5 是后续企业挂链目标，但产业链分析报告本身不做挂链。
- 企业不是图谱子节点，只作为挂链流程里的链接记录存在。
- 产业链分析报告必须展示 L1/L2/L3/L4/L5 解释口径、项目图谱口径、节点映射、项目风格 L2/L3/L5 图谱、产业链结构、层级结构分析和分析框架。

### 智能汽车示例

对“智能汽车产业链 / 自动驾驶”这类输入，Skill 会先映射到当前项目已有口径，例如：

- 标准产业链：`智能网联汽车`
- 示例标准节点：`自动驾驶解决方案`、`自动驾驶仿真平台`
- 示例报告字段：`project_graph_summary`、`level_definitions`、`node_mapping`、`project_graph_tree`、`project_value_chain`、`project_node_records`、`hierarchy_analysis`、`analysis_framework`

这样生成的专业产业链分析报告会沿用当前项目的产业链层级、图谱展示和节点数据记录，下次可以继续复用；企业挂链和企业证据核验另走独立报告。

## 区域政策分析

当你要分析某个产业链在不同地区的政策情况时，Skill 会同时使用：

- 旷湖/HandaaS 政策大数据 MCP：`policy_bigdata_policy_search`、`policy_bigdata_policy_info`、`policy_bigdata_approved_project_stats`
- 联网搜索：补充政府官网、主管部门、园区/示范区、申报指南、公示公告等最新公开信息

示例：

```bash
python industry-chain-processing/scripts/policy_analysis.py \
  --chain "智能汽车" \
  --keyword "智能网联汽车 自动驾驶" \
  --region "国家部委" \
  --region "广东省" \
  --region "上海" \
  --region "江苏省" \
  --policy-start "2025-01-01" \
  --web-context output/policy-web-context.json \
  --output output/policy-analysis.json

python industry-chain-processing/scripts/render_report.py \
  --input output/policy-analysis.json \
  --output output/policy-analysis.html
```

联网搜索结果可以保存为：

```json
{
  "policy_context": [
    {
      "region": "广东省",
      "topic": "智能网联汽车政策",
      "finding": "用一句话概括联网收集到的政策要点。",
      "source": "来源名称",
      "url": "https://example.com/source",
      "date": "2026-01-01"
    }
  ]
}
```

输出报告会包含：

- 各地区政策数量、旷湖政策库线索数、联网补充线索数
- 各地政策重点和主要发布机构/来源
- 资金补贴、试点示范、技术研发、基础设施、监管规范等政策支持维度
- 代表性政策与联网依据

## 生成静态报告

可以。Skill 默认在智能体对话里用结构化摘要和表格展示；如果你要发给同事、客户或沉淀为材料，可以让智能体直接生成报告：

```text
使用旷湖产业链分析，分析低空经济产业链，并生成一个可离线打开的 HTML 报告。
```

```text
使用旷湖产业链分析，基于刚才的企业线索结果，生成 Markdown 报告。
```

内置报告能力：

| 形式 | 适用场景 | 特点 |
| --- | --- | --- |
| 对话表格 | 快速查看结果 | 直接在智能体对话中阅读，适合迭代分析 |
| 静态 HTML | 对外展示、发给同事、沉淀材料 | 单文件、可离线打开、带样式和汇总卡片 |
| Markdown | 放入知识库、Wiki、PRD 或二次编辑 | 易复制、易版本管理 |
| JSON | 系统对接或二次加工 | 保留结构化字段，适合继续处理 |

### 专业产业链分析报告（不含挂链）

产业链分析报告是面向用户的专业交付件，专注封面摘要、L1-L5 口径、产业链图谱、层级解读和结构洞察；不展示结论与建议、原始 JSON、内部调试字段、企业召回或挂链。HTML 报告采用研报式版面：A4 白底页面、灰色横纹页眉、蓝色报告横幅、封面目录侧栏、深蓝标题和蓝色表格。报告摘要允许联网收集权威背景资料，以便摘要像产业链分析报告摘要，而不是脚本执行摘要。

联网收集建议：

- 优先使用政府部门、监管机构、行业协会、研究机构、上市公司/官方披露、权威财经或科技媒体。
- 收集 3-5 条即可，聚焦政策牵引、市场变化、技术路线、商业化阶段、监管边界。
- 每条保留 `topic`、`finding`、`source`、`url`、`date`。
- 没有网络或用户要求离线时，继续使用项目图谱生成报告，不编造外部事实。

若要复用当前项目图谱，按上文对应操作系统的方式设置 `INDUSTRY_CHAIN_PROJECT_ROOT`。

可选：把联网收集到的背景保存为 JSON：

```json
{
  "market_context": [
    {
      "topic": "政策背景",
      "finding": "用一句话概括联网收集到的权威产业背景。",
      "source": "来源名称",
      "url": "https://example.com/source",
      "date": "2026-01-01"
    }
  ]
}
```

生成报告 JSON：

```bash
python industry-chain-processing/scripts/compose_industry_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --market-context output/smart-car-market-context.json \
  --output output/smart-car-chain-analysis-report.json
```

也可以不用 JSON 文件，直接传多条摘要：

```bash
python industry-chain-processing/scripts/compose_industry_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --market-note "政策背景|智能网联汽车相关政策正在推动自动驾驶试点、车路云协同和规模化应用验证|权威来源|https://example.com|2026-01-01" \
  --output output/smart-car-chain-analysis-report.json
```

渲染为 HTML / Markdown：

```bash
python industry-chain-processing/scripts/render_report.py \
  --input output/smart-car-chain-analysis-report.json \
  --output output/smart-car-chain-analysis-report.html

python industry-chain-processing/scripts/render_report.py \
  --input output/smart-car-chain-analysis-report.json \
  --output output/smart-car-chain-analysis-report.md
```

### 企业挂链报告（单独生成）

如果你还需要企业挂链，再单独跑企业召回、证据核验和挂链结果。精准挂链分别组合 `industriesV2`、`businessKeywords`、`business/desc` 和招聘/专利/招投标强证据；最高精度路由同时要求业务关键词、经营范围/简介和强证据，其他路由负责补回字段缺失或行业错分企业。多路候选按路由优先级和共识度排序后，再按企业业务、简介/标签、专利申请人和招投标信息进行独立来源复核。代表企业和高筛命中本身都不会直接确认为挂链结果。

```bash
python industry-chain-processing/scripts/link_enterprises.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --path "智能汽车产业链>智能化系统>自动驾驶" \
  --page-size 5 \
  --max-candidates 20 \
  --with-evidence \
  --require-es \
  --output output/smart-car-enterprise-linking.json \
  --report-output output/smart-car-enterprise-linking.html
```

整条产业链逐节点挂链先生成全部 L5 节点的 ES 计划，再按批次真实执行：

```bash
python industry-chain-processing/scripts/link_chain_nodes.py \
  --chain "工业母机" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --max-nodes 0 \
  --dry-run \
  --output output/industrial-machine-linking-plan.json

python industry-chain-processing/scripts/link_chain_nodes.py \
  --chain "工业母机" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --max-nodes 20 \
  --with-evidence \
  --require-es \
  --resume \
  --output output/industrial-machine-linking.json \
  --report-output output/industrial-machine-linking.html
```

`--max-nodes 0` 表示处理所有匹配节点；真实调用建议分批设置 `--offset` 和 `--max-nodes`。Remote MCP 只提供关键词搜索时，结果会明确标记为 `precision_limited`，不能作为精准 ES 挂链验收结果。

### 只输入企业名称的产业链定位报告

不需要先指定产业链或节点。Skill 会解析企业主体，通过已配置的 MCP 查询企业画像、业务、标签、专利和招投标信息，并与项目全部 L5 节点比较：

```bash
python industry-chain-processing/scripts/enterprise_chain_positioning.py \
  --enterprise "深圳市汇川技术股份有限公司" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --output output/enterprise-chain-positioning.json \
  --report-output output/enterprise-chain-positioning.html
```

输出包含主归属产业链、L2/L3/L5 完整路径、候选产业链对比、候选节点、证据覆盖和定位边界。若企业横跨多个产业链且分数接近，报告会保留备选归属，不作排他性判断。

如果需要 Markdown，将报告输出路径改为 `.md`，或显式传入 `--report-format markdown`：

```bash
python industry-chain-processing/scripts/enterprise_chain_positioning.py \
  --enterprise "深圳市汇川技术股份有限公司" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --output output/enterprise-chain-positioning.json \
  --report-output output/enterprise-chain-positioning.md
```

### 指定企业节点详细分析报告

当你要判断某个企业应不应该挂到某个产业链节点时，直接生成企业节点分析：

```bash
python industry-chain-processing/scripts/enterprise_node_report.py \
  --chain "智能汽车" \
  --node "自动驾驶" \
  --path "智能汽车产业链>智能化系统>自动驾驶" \
  --enterprise "安徽中科星驰自动驾驶技术有限公司" \
  --key-type name \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --project-chain "智能网联汽车" \
  --project-node "自动驾驶" \
  --output output/enterprise-node-report.json \
  --report-output output/enterprise-node-report.html
```

命令会同时输出结构化 JSON 和可交付报告，不需要再次调用渲染脚本。

### 基础报告渲染

高级用户也可以直接使用脚本渲染任意结构化结果：

```bash
python industry-chain-processing/scripts/render_report.py \
  --input industry-chain-processing/assets/report.example.json \
  --output output/industry-report.html
```

生成 Markdown：

```bash
python industry-chain-processing/scripts/render_report.py \
  --input industry-chain-processing/assets/report.example.json \
  --output output/industry-report.md
```

## 高级命令行用法

一般用户不需要使用本节。下面命令主要用于开发、调试或排查接口问题。

多行示例使用 macOS/Linux 的反斜杠续行格式。Windows PowerShell 可将命令写成一行，或把行尾 `\` 改为反引号 `` ` ``；完整操作系统命令对照见 `industry-chain-processing/references/os-operations.md`。

### 1. 配置校验

```bash
python industry-chain-processing/scripts/validate_config.py
```

### 2. 生成企业搜索策略

```bash
python industry-chain-processing/scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --output output/evtol-search.json
```

追加业务词、行业边界和排除词：

```bash
python industry-chain-processing/scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --keyword "适航认证" \
  --keyword "飞行器总装" \
  --industry "制造业/铁路、船舶、航空航天和其他运输设备制造业" \
  --exclude "航空培训" \
  --output output/evtol-search.json
```

完整搜索计划包含字段拆分后的多条路由。使用 `--explain` 查看每条路由的工商条件、业务字段、强证据字段、优先级和校验结果：

```bash
python industry-chain-processing/scripts/build_condition.py \
  --chain "工业母机" \
  --node "伺服驱动器" \
  --path "工业母机>上游：核心零部件与基础材料>伺服系统>伺服驱动器" \
  --precision strict \
  --explain
```

排除条件必须把字段级 `nin/neq` 直接放入顶层 `must`。旷湖高筛不会执行顶层 `must_not`；Skill 会拒绝该格式，并迁移内部全部为 `nin/neq` 的历史条件。

### 3. ES 条件准确性调优

先根据 `assets/search-tuning-labels.example.json` 建立节点正样本、负样本或 0-3 级相关性标签，再执行真实高筛和证据复核：

```bash
python industry-chain-processing/scripts/tune_search_conditions.py \
  --config "$INDUSTRY_CHAIN_CONFIG" \
  --chain "工业母机" \
  --node "伺服驱动器" \
  --path "工业母机>上游：核心零部件与基础材料>伺服系统>伺服驱动器" \
  --project-root "$INDUSTRY_CHAIN_PROJECT_ROOT" \
  --labels industry-chain-processing/assets/search-tuning-labels.example.json \
  --page-size 20 \
  --pages 2 \
  --with-evidence \
  --output output/servo-search-evaluation.json
```

输出包括各路由候选总量、Precision@10、MRR、DCG@10、项目代表企业命中、证据确认率、噪声率、强证据覆盖、路由重叠和独有贡献。下一轮通过 `--baseline output/servo-search-evaluation.json` 比较条件修改前后变化。

### 4. HandaaS 企业业务证据组合探测

使用已知正样本和相邻负样本，对工商照面、企业简介、企业业务、企业标签、专利和招投标接口执行组合消融：

```bash
INDUSTRY_CHAIN_MCP_URL=http://127.0.0.1:8022/mcp \
python industry-chain-processing/scripts/probe_business_evidence.py \
  --cases industry-chain-processing/assets/business-evidence-cases.example.json \
  --max-combination-size 0 \
  --output output/business-evidence-probe.json
```

当前回归样本中，`企业标签 + 专利搜索 + 企业招投标信息` 是高精度三接口组合；需要提高多元化企业召回时，增加工商照面和企业简介。`企业业务` 有数据时属于强证据，但不得因该商品无数据而中止复核。输出分别报告企业业务判断与最终自动挂链的精确率、召回率、特异度和平衡准确率。

### 5. 模拟查询企业

只检查请求结构，不调用网络：

```bash
python industry-chain-processing/scripts/enterprise_search_preview.py \
  --filter-file output/evtol-search.json \
  --dry-run
```

### 6. 真实查询企业

```bash
python industry-chain-processing/scripts/enterprise_search_preview.py \
  --filter-file output/evtol-search.json \
  --page-index 1 \
  --page-size 10
```

### 7. 单个细分环节端到端分析

模拟运行：

```bash
python industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --dry-run
```

真实查询候选企业：

```bash
python industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --page-size 10
```

同时做证据核验：

```bash
python industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --page-size 5 \
  --with-evidence \
  --output output/evtol-enterprise-linking.json \
  --report-output output/evtol-enterprise-linking.html
```

### 8. 整条产业链逐节点挂链

```bash
python industry-chain-processing/scripts/link_chain_nodes.py \
  --chain "工业母机" \
  --role upstream \
  --max-nodes 20 \
  --with-evidence \
  --require-es \
  --resume \
  --output output/industrial-machine-upstream-linking.json \
  --report-output output/industrial-machine-upstream-linking.html
```

## 仓库结构

```text
industry-chain-processing-skill/
├── README.md
├── LICENSE
├── .gitignore
└── industry-chain-processing/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── assets/config.example.json
    ├── assets/report.example.json
    ├── assets/search-tuning-labels.example.json
    ├── assets/business-evidence-cases.example.json
    ├── references/
    │   ├── analysis-playbook.md
    │   ├── ontology-contract.md
    │   ├── local-enterprise-config.md
    │   ├── os-operations.md
    │   ├── enterprise-search-rules.md
    │   ├── es-relevance-tuning.md
    │   ├── business-evidence-probing.md
    │   ├── evidence-scoring.md
    │   ├── project-context.md
    │   └── report-output.md
    └── scripts/
        ├── common.py
        ├── validate_config.py
        ├── build_condition.py
        ├── enterprise_search_preview.py
        ├── evidence_call.py
        ├── link_enterprises.py
        ├── link_chain_nodes.py
        ├── tune_search_conditions.py
        ├── probe_business_evidence.py
        ├── compose_industry_report.py
        ├── enterprise_chain_positioning.py
        ├── enterprise_node_report.py
        ├── mcp_client.py
        ├── project_context.py
        └── render_report.py
```

脚本建议 Python 3.10+。模拟运行和本地直连签名只依赖标准库；连接 MCP 时需要额外安装 `mcp` 和 `httpx`。

## 故障排查

### 1. MCP 客户端依赖缺失

如果 `mcp_client.py list-tools` 提示缺少 `mcp` 或 `httpx`：

```bash
python -m pip install 'mcp>=1.12.0' httpx
```

### 2. Remote MCP token 不可用

检查环境变量是否在当前 shell 生效：

macOS / Linux：

```bash
echo "$INDUSTRY_CHAIN_MCP_TOKEN"
echo "$INDUSTRY_CHAIN_MCP_URL"
python industry-chain-processing/scripts/mcp_client.py ping
```

Windows PowerShell：

```powershell
$env:INDUSTRY_CHAIN_MCP_TOKEN
$env:INDUSTRY_CHAIN_MCP_URL
python .\industry-chain-processing\scripts\mcp_client.py ping
```

不要把 token 打进日志或提交到 Git。

### 3. 本地 MCP 连不上

确认服务已启动，并且 Skill 侧指向 `/mcp` 路径：

macOS / Linux：

终端 1：

```bash
cd ../industry-chain-mcp-server
./start_mcp_server.sh
```

终端 2：

```bash
export INDUSTRY_CHAIN_MCP_URL="http://127.0.0.1:8000/mcp"
cd ../industry-chain-processing-skill
python industry-chain-processing/scripts/mcp_client.py list-tools
```

Windows PowerShell：

PowerShell 窗口 1：

```powershell
Set-Location ..\industry-chain-mcp-server
python .\server\mcp_server.py streamable-http
```

PowerShell 窗口 2：

```powershell
$env:INDUSTRY_CHAIN_MCP_URL = "http://127.0.0.1:8000/mcp"
Set-Location ..\industry-chain-processing-skill
python .\industry-chain-processing\scripts\mcp_client.py list-tools
```

### 4. MCP 可用工具不符合预期

可用工具应该是 HandaaS 现有接口封装，例如 `enterprise_get_keyword_search`、`patent_bigdata_patent_stats`、`bid_bigdata_bidding_info`、`policy_bigdata_policy_search`。如果看到产业链工作流类工具，请更新 `industry-chain-mcp-server` 到最新版本后重启服务。

### 5. 找不到配置文件

创建默认配置：

macOS / Linux：

```bash
mkdir -p "$HOME/.industry-chain-processing"
cp industry-chain-processing/assets/config.example.json \
  "$HOME/.industry-chain-processing/handaas.config.json"
```

Windows PowerShell：

```powershell
$configRoot = Join-Path $HOME ".industry-chain-processing"
$configPath = Join-Path $configRoot "handaas.config.json"
New-Item -ItemType Directory -Force -Path $configRoot | Out-Null
Copy-Item .\industry-chain-processing\assets\config.example.json $configPath
python .\industry-chain-processing\scripts\validate_config.py --config $configPath
```

### 6. 仍是占位值

说明配置中仍有 `your_...` 凭证或接口地址占位值。产品 ID 已使用旷湖平台稳定公开 ID，不需要用户替换；真实查询前只需配置自己的 URL、对接器 ID 和密钥。

### 7. 查询太宽或噪声太多

让智能体补充更具体的业务词和排除词：

```text
使用旷湖产业链分析，刚才结果里培训、维修和旅游观光企业太多，请补充排除词后重新模拟运行。
```

### 8. 真实接口调用超时

先降低返回数量，或先只做模拟运行：

```bash
python industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --page-size 5
```

贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题处理方式见 [SECURITY.md](SECURITY.md)。
