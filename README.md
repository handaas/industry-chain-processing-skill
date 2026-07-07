# 旷湖产业链分析 Skill

一个可被本地智能体使用的产业链分析 Skill / 工具包。用户只需要说“使用旷湖产业链分析，分析某个行业 / 赛道 / 企业名单”，智能体会自动完成产业链拆解、企业线索挖掘、证据核验、挂链建议和报告生成。

> 这不是 SaaS 平台，也不会托管用户数据或凭证。仓库安装到本机后，只读取用户自己的本地配置和接口权限。

## 目录

- [你可以直接怎么说](#你可以直接怎么说)
- [一句话安装调试](#一句话安装调试)
- [安装到本地智能体](#安装到本地智能体)
- [配置本地企业数据接口](#配置本地企业数据接口)
- [快速验证](#快速验证)
- [它会自动做什么](#它会自动做什么)
- [输出结果怎么看](#输出结果怎么看)
- [生成静态报告](#生成静态报告)
- [高级命令行用法](#高级命令行用法)
- [仓库结构](#仓库结构)
- [故障排查](#故障排查)
- [安全边界](#安全边界)
- [开发与发布](#开发与发布)

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

你不需要理解内部层级、接口字段、数据产品或搜索参数；这些都由 Skill 在内部完成。

## 一句话安装调试

给普通用户最省事的方式：复制下面这段话到任意支持 Git / Shell / Python 的智能体工具里。Codex 只是例子，Claude Code、Gemini CLI、Cursor、Windsurf、Cline、OpenHands 等智能体也可以按同一段指令执行。

```text
请帮我安装并调试“旷湖产业链分析”：先完整读取 https://github.com/sunjackson/industry-chain-processing-skill 这个项目的 README.md，再克隆仓库并按 README 自动完成安装、配置文件创建、校验、模拟分析验证和示例 HTML 报告生成。若当前工具支持 Codex-compatible Skill，就把 industry-chain-processing/ 安装到对应 skills 目录；若不支持，就把该仓库作为本地工具包使用，并记住后续通过仓库脚本和 README 工作流来完成“使用旷湖产业链分析，...”类请求。请提醒我只在本地配置自己的企业数据接口参数，不要提交凭证；除非需要真实接口密钥，否则不要中断询问。
```

如果你使用 SSH 拉取仓库，也可以把地址换成：

```text
git@github.com:sunjackson/industry-chain-processing-skill.git
```

智能体读取 README 后应自动完成：

1. 克隆仓库。
2. 判断当前工具是否支持 Skill 目录安装。
3. 支持 Skill 时安装 `industry-chain-processing/`；不支持时保留仓库作为本地工具包。
4. 创建 `~/.industry-chain-processing/handaas.config.json`。
5. 提醒用户填入自己的本地接口参数，并避免提交凭证。
6. 运行校验、模拟分析和示例报告生成。
7. 告诉用户后续如何在当前智能体里说“使用旷湖产业链分析，...”。

## 安装到本地智能体

### 通用安装逻辑

```bash
git clone https://github.com/sunjackson/industry-chain-processing-skill.git
cd industry-chain-processing-skill
```

如果你的智能体支持 Codex-compatible Skill 目录，例如 `~/.codex/skills`，安装 Skill 包：

```bash
mkdir -p ~/.codex/skills
cp -R industry-chain-processing ~/.codex/skills/
```

如果你的智能体没有 Skill 目录，也可以直接把仓库作为本地工具包使用：让智能体读取本 README、`industry-chain-processing/SKILL.md` 和 `industry-chain-processing/references/`，并调用 `industry-chain-processing/scripts/` 下的脚本。

### Codex 复制安装

```bash
git clone https://github.com/sunjackson/industry-chain-processing-skill.git
mkdir -p ~/.codex/skills
cp -R industry-chain-processing-skill/industry-chain-processing ~/.codex/skills/
```

更新时重新复制：

```bash
cd industry-chain-processing-skill
git pull
rm -rf ~/.codex/skills/industry-chain-processing
cp -R industry-chain-processing ~/.codex/skills/
```

### Codex 软链接安装，推荐给开发者

```bash
git clone https://github.com/sunjackson/industry-chain-processing-skill.git
mkdir -p ~/.codex/skills
ln -sfn "$(pwd)/industry-chain-processing-skill/industry-chain-processing" \
  ~/.codex/skills/industry-chain-processing
```

安装后重启对应智能体，或在支持热加载的客户端中刷新 Skill / 工具列表。

## 配置本地企业数据接口

如果只做产业链分析和模拟运行，可以先不填真实接口参数。若要真实查询企业，需要创建本地配置文件：

```bash
mkdir -p ~/.industry-chain-processing
cp ~/.codex/skills/industry-chain-processing/assets/config.example.json \
  ~/.industry-chain-processing/handaas.config.json
vim ~/.industry-chain-processing/handaas.config.json
```

如果不是安装在 `~/.codex/skills`，把上面的源路径替换为仓库中的：

```bash
industry-chain-processing/assets/config.example.json
```

配置文件示例：

```json
{
  "handaas": {
    "base_url": "https://console.handaas.com",
    "integrator_id": "your_integrator_id",
    "secret_id": "your_secret_id",
    "secret_key": "your_secret_key",
    "products": {
      "工商照面": "product_id_for_business_profile",
      "工商年报": "product_id_for_annual_report",
      "招聘统计": "product_id_for_recruiting_stats",
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

脚本按以下顺序读取配置：

1. 命令行 `--config <path>`
2. 环境变量 `INDUSTRY_CHAIN_CONFIG`
3. 环境变量 `HANDAAS_CONFIG`
4. 默认路径 `~/.industry-chain-processing/handaas.config.json`
5. 示例配置，仅用于模拟运行

可选环境变量：

```bash
export INDUSTRY_CHAIN_CONFIG=~/.industry-chain-processing/handaas.config.json
# 或
export HANDAAS_CONFIG=~/.industry-chain-processing/handaas.config.json
```

## 快速验证

验证真实配置：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/validate_config.py
```

只验证示例配置，不要求真实凭证：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/validate_config.py \
  --config ~/.codex/skills/industry-chain-processing/assets/config.example.json \
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

1. **理解目标**：判断用户要做产业链研究、企业线索挖掘、企业归位、招商筛选，还是证据核验。
2. **拆解产业链**：把行业主题拆成“产业主题 -> 价值环节 -> 细分模块 -> 可匹配企业的产品 / 技术 / 服务 / 能力”。
3. **选择分析重点**：自动挑出最适合找企业、招商或核验的细分环节。
4. **生成搜索策略**：自动扩展业务词、同义词、场景词、岗位词、专利词、招投标词和排除词。
5. **查询企业线索**：如果本地接口配置可用，查询候选企业；如果没有配置，则输出模拟请求和后续配置提示。
6. **核验证据**：结合工商、招聘、知识产权、招投标等证据判断企业是否真的匹配。
7. **输出建议**：给出确认、待复核、剔除，以及下一步补充关键词或排除噪声的建议。
8. **生成报告**：用户需要交付或展示时，可直接生成离线 HTML 或 Markdown 报告。

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
| `search_strategy` | 企业搜索思路，默认用自然语言解释 |
| `candidates` | 候选企业样本和数量 |
| `evidence` | 工商、招聘、专利、招投标等证据摘要 |
| `decision` | `confirmed`、`uncertain`、`rejected` |
| `next_actions` | 后续建议，例如补充排除词、人工复核、真实接口查询 |

决策含义：

| decision | 含义 | 建议动作 |
| --- | --- | --- |
| `confirmed` | 有较强证据表明企业匹配该细分环节 | 可确认挂链 |
| `uncertain` | 有相关迹象但证据不足或边界不清 | 人工复核 |
| `rejected` | 明显不相关或被噪声召回 | 剔除并补充排除词 |


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

高级用户也可以直接使用脚本生成报告：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/render_report.py \
  --input ~/.codex/skills/industry-chain-processing/assets/report.example.json \
  --output /tmp/industry-report.html
```

生成 Markdown：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/render_report.py \
  --input ~/.codex/skills/industry-chain-processing/assets/report.example.json \
  --output /tmp/industry-report.md
```

## 高级命令行用法

一般用户不需要使用本节。下面命令主要用于开发、调试或排查接口问题。

### 1. 配置校验

```bash
python ~/.codex/skills/industry-chain-processing/scripts/validate_config.py
```

### 2. 生成企业搜索策略

```bash
python ~/.codex/skills/industry-chain-processing/scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --output /tmp/evtol-search.json
```

追加业务词、行业边界和排除词：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --keyword "适航认证" \
  --keyword "飞行器总装" \
  --industry "制造业/铁路、船舶、航空航天和其他运输设备制造业" \
  --exclude "航空培训" \
  --output /tmp/evtol-search.json
```

### 3. 模拟查询企业

只检查请求结构，不调用网络：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/enterprise_search_preview.py \
  --filter-file /tmp/evtol-search.json \
  --dry-run
```

### 4. 真实查询企业

```bash
python ~/.codex/skills/industry-chain-processing/scripts/enterprise_search_preview.py \
  --filter-file /tmp/evtol-search.json \
  --page-index 1 \
  --page-size 10
```

### 5. 单个细分环节端到端分析

模拟运行：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --dry-run
```

真实查询候选企业：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --page-size 10
```

同时做证据核验：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --page-size 5 \
  --with-evidence
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
    ├── references/
    │   ├── analysis-playbook.md
    │   ├── ontology-contract.md
    │   ├── local-enterprise-config.md
    │   ├── enterprise-search-rules.md
    │   └── evidence-scoring.md
    └── scripts/
        ├── common.py
        ├── validate_config.py
        ├── build_condition.py
        ├── enterprise_search_preview.py
        ├── evidence_call.py
        ├── link_enterprises.py
        └── render_report.py
```

运行脚本只依赖 Python 标准库，建议 Python 3.10+。

## 故障排查

### 1. 找不到配置文件

创建默认配置：

```bash
mkdir -p ~/.industry-chain-processing
cp ~/.codex/skills/industry-chain-processing/assets/config.example.json \
  ~/.industry-chain-processing/handaas.config.json
```

或显式指定：

```bash
python scripts/validate_config.py --config /path/to/handaas.config.json
```

### 2. 仍是占位值

说明配置中还有 `your_...` 或 `product_id_for_...`。真实查询前必须替换成自己的接口参数。

### 3. 查询太宽或噪声太多

让智能体补充更具体的业务词和排除词：

```text
使用旷湖产业链分析，刚才结果里培训、维修和旅游观光企业太多，请补充排除词后重新模拟运行。
```

### 4. 真实接口调用超时

先降低返回数量，或先只做模拟运行：

```bash
python scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --page-size 5
```

## 安全边界

- 不提交真实配置文件。
- 不在 Git、日志、Issue、截图中暴露 `secret_id`、`secret_key`、signature、token。
- 模拟运行会脱敏敏感字段。
- 本仓库不托管用户数据，不保存调用结果。
- 真实接口调用可能产生费用；不确定时先模拟运行。

## 开发与发布

本地校验：

```bash
cd industry-chain-processing-skill/industry-chain-processing
python /Users/sunjackson/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python3 -m py_compile scripts/*.py
python3 scripts/validate_config.py --config assets/config.example.json --allow-placeholders
python3 scripts/link_enterprises.py \
  --config assets/config.example.json \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --dry-run
python3 scripts/render_report.py --input assets/report.example.json --output /tmp/industry-report.html
```

推送到 GitHub：

```bash
cd /Users/sunjackson/Project/industry-chain-processing-skill
git push
```

发布前检查：

```bash
git status --short
git grep -n "secret_key\|secret_id\|signature\|token" -- . ':!README.md' ':!industry-chain-processing/assets/config.example.json'
```

如果 grep 命中真实凭证，必须删除后再提交。
