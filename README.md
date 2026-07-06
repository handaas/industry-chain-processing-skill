# industry-chain-processing-skill

面向 Codex 的本地产业链加工 Skill。它把“产业链 L1-L5 本体生成、L5 节点高筛条件构造、Handaas/高筛企业查询、企业证据核验、挂链建议输出”封装成一个可安装的 Skill 和一组本地脚本。

> 这不是 SaaS 平台，也不会托管用户数据或凭证。用户从 GitHub 安装 Skill 后，配置自己的 Handaas / high-screen 凭证，即可在本地让 Codex 使用该技能和接口脚本。

## 目录

- [适用场景](#适用场景)
- [最小上手流程](#最小上手流程)
- [仓库结构](#仓库结构)
- [安装到 Codex](#安装到-codex)
- [配置 Handaas / high-screen](#配置-handaas--high-screen)
- [快速验证](#快速验证)
- [在 Codex 中使用](#在-codex-中使用)
- [命令行使用](#命令行使用)
- [脚本接口说明](#脚本接口说明)
- [输出与决策口径](#输出与决策口径)
- [故障排查](#故障排查)
- [安全边界](#安全边界)
- [开发与发布](#开发与发布)

## 适用场景

使用这个 Skill 可以完成：

1. **产业链本体生成**：把“低空经济 / 人形机器人 / 半导体”等主题拆成 L1-L5 产业链结构。
2. **L5 节点企业挂链**：为“eVTOL整机制造”“飞控系统”“动力电池PACK”等 L5 节点生成高筛条件。
3. **高筛企业召回**：调用用户本地配置的 high-screen 接口返回企业候选名单。
4. **Handaas 证据核验**：调用工商照面、招聘、知识产权、招投标等产品，辅助判断企业是否真正匹配节点。
5. **挂链建议输出**：把企业候选标记为 `confirmed`、`uncertain` 或 `rejected`。

核心原则：

- 先生成产业链本体，再做企业挂链。
- 企业不进入 L1-L5 图谱层级。
- L5 是企业挂链的最小目标。
- 高筛条件必须围绕业务语义扩展，不只使用节点名称。
- 所有凭证只保存在用户本地。

## 最小上手流程

如果只是安装后立即试用，按这 4 步走：

```bash
# 1. 拉取仓库。把 <your-name> 替换成实际 GitHub 账号或组织名。
git clone https://github.com/<your-name>/industry-chain-processing-skill.git

# 2. 安装 Skill 到 Codex。
mkdir -p ~/.codex/skills
cp -R industry-chain-processing-skill/industry-chain-processing ~/.codex/skills/

# 3. 创建本地配置，并填入自己的 Handaas / high-screen 参数。
mkdir -p ~/.industry-chain-processing
cp ~/.codex/skills/industry-chain-processing/assets/config.example.json \
  ~/.industry-chain-processing/handaas.config.json
vim ~/.industry-chain-processing/handaas.config.json

# 4. 验证配置结构。
python ~/.codex/skills/industry-chain-processing/scripts/validate_config.py
```

验证通过后，在 Codex 中直接说：

```text
使用 industry-chain-processing，为“低空经济 > 航空器制造 > eVTOL整机制造”查询候选企业，先 dry-run。
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
    ├── references/
    │   ├── ontology-contract.md
    │   ├── handaas-config.md
    │   ├── high-screen-condition-rules.md
    │   └── evidence-scoring.md
    └── scripts/
        ├── common.py
        ├── validate_config.py
        ├── build_condition.py
        ├── high_screen_preview.py
        ├── handaas_call.py
        └── link_enterprises.py
```

运行脚本只依赖 Python 标准库，建议 Python 3.10+。

## 安装到 Codex

下面示例中的 `<your-name>` 需要替换成你实际提交到 GitHub 的账号或组织名。

### 方式一：复制安装

```bash
git clone https://github.com/<your-name>/industry-chain-processing-skill.git
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

### 方式二：软链接安装，推荐给开发者

```bash
git clone https://github.com/<your-name>/industry-chain-processing-skill.git
mkdir -p ~/.codex/skills
ln -sfn "$(pwd)/industry-chain-processing-skill/industry-chain-processing" \
  ~/.codex/skills/industry-chain-processing
```

安装后重启 Codex，或在支持热加载的客户端中刷新 Skill 列表。

## 配置 Handaas / high-screen

创建本地配置文件：

```bash
mkdir -p ~/.industry-chain-processing
cp ~/.codex/skills/industry-chain-processing/assets/config.example.json \
  ~/.industry-chain-processing/handaas.config.json
```

编辑：

```bash
vim ~/.industry-chain-processing/handaas.config.json
```

配置结构：

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
    "url": "https://example.com/high-screen-endpoint",
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
5. `assets/config.example.json`，仅用于 `--dry-run` 示例

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

验证示例配置，不要求真实凭证：

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

## 在 Codex 中使用

安装后，可以直接让 Codex 使用该 Skill。

### 示例 1：生成产业链本体

```text
使用 industry-chain-processing，帮我生成“低空经济”产业链 L1-L5 本体，企业不要放进图谱层级。
```

期望 Codex 输出：

- L1 产业链域
- L2 价值环节
- L3 产业环节
- L5 产品 / 技术 / 服务节点
- L5 可挂链性说明

### 示例 2：为单个 L5 节点构造高筛条件

```text
使用 industry-chain-processing，为“低空经济 > 航空器制造 > eVTOL整机制造”构造 high-screen 条件组，先 dry-run，不真实调用接口。
```

Codex 应优先调用：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造"
```

### 示例 3：调用高筛接口找企业

```text
使用 industry-chain-processing，调用我的本地 high-screen 配置，为“eVTOL整机制造”查询前 10 个候选企业。
```

Codex 应先运行 `validate_config.py` 检查配置可用，然后执行 high-screen 查询。若你还没有确认要真实调用，可以要求：

```text
先 dry-run，只检查请求结构。
```

### 示例 4：带 Handaas 证据核验

```text
使用 industry-chain-processing，为“eVTOL整机制造”查询候选企业，并用工商照面、招聘明细、知识产权统计、企业招投标信息做证据核验，输出 confirmed / uncertain / rejected。
```

注意：带 `--with-evidence` 会调用多个 Handaas 产品，可能产生接口费用。

## 命令行使用

下面命令可不经过 Codex，直接作为本地接口脚本使用。

### 1. 生成 L5 节点高筛条件

```bash
python ~/.codex/skills/industry-chain-processing/scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --output /tmp/evtol-condition.json
```

追加业务词：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --keyword "适航认证" \
  --keyword "飞行器总装" \
  --exclude "航空培训" \
  --output /tmp/evtol-condition.json
```

追加行业边界：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --industry "制造业/铁路、船舶、航空航天和其他运输设备制造业" \
  --output /tmp/evtol-condition.json
```

### 2. 高筛 dry-run

只检查签名和请求形态，不调用网络：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/high_screen_preview.py \
  --filter-file /tmp/evtol-condition.json \
  --dry-run
```

### 3. 高筛真实查询

```bash
python ~/.codex/skills/industry-chain-processing/scripts/high_screen_preview.py \
  --filter-file /tmp/evtol-condition.json \
  --page-index 1 \
  --page-size 10
```

输出包含：

```json
{
  "total": 123,
  "pageIndex": 1,
  "pageSize": 10,
  "samples": [
    {
      "id": "企业ID",
      "name": "企业名称",
      "socialCreditCode": "统一社会信用代码",
      "regCapital": "注册资本"
    }
  ]
}
```

### 4. Handaas dry-run

```bash
python ~/.codex/skills/industry-chain-processing/scripts/handaas_call.py \
  --product 工商照面 \
  --keyword "test-enterprise-id" \
  --key-type nameId \
  --dry-run
```

### 5. Handaas 真实调用

```bash
python ~/.codex/skills/industry-chain-processing/scripts/handaas_call.py \
  --product 工商照面 \
  --keyword "<企业ID>" \
  --key-type nameId
```

使用企业名称查询：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/handaas_call.py \
  --product 工商照面 \
  --keyword "某某科技有限公司" \
  --key-type name
```

分页产品示例：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/handaas_call.py \
  --product 招聘明细 \
  --keyword "<企业ID>" \
  --key-type nameId \
  --extra-json '{"pageIndex":1,"pageSize":5}'
```

### 6. 单节点企业挂链 dry-run

```bash
python ~/.codex/skills/industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --dry-run
```

### 7. 单节点企业挂链真实查询

只调 high-screen，不调 Handaas 证据：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --page-size 10
```

同时做 Handaas 证据核验：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --path "低空经济产业链>航空器制造>eVTOL整机制造" \
  --page-size 5 \
  --with-evidence
```

限制证据产品：

```bash
python ~/.codex/skills/industry-chain-processing/scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --with-evidence \
  --evidence-product 工商照面 \
  --evidence-product 招聘明细
```

## 脚本接口说明

### `validate_config.py`

用途：检查配置结构，不泄露凭证。

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--config` | 指定配置文件路径 |
| `--allow-placeholders` | 允许示例占位值通过校验 |

### `build_condition.py`

用途：为 L5 节点构造 high-screen 条件组。

常用参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--chain` | 是 | 产业链名称 |
| `--node` | 是 | L5 节点名称 |
| `--path` | 否 | 完整节点路径，用 `>` 或 `/` 分隔 |
| `--keyword` | 否 | 追加业务关键词，可重复 |
| `--industry` | 否 | 追加高筛行业路径，可重复 |
| `--exclude` | 否 | 追加排除词，可重复 |
| `--output` | 否 | 写入条件 JSON 文件 |

### `high_screen_preview.py`

用途：调用 high-screen 查询企业候选。

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--filter-file` | 条件 JSON 文件 |
| `--filter-json` | 条件 JSON 字符串 |
| `--page-index` | 页码，默认 1 |
| `--page-size` | 每页数量，1-50 |
| `--dry-run` | 只输出脱敏请求，不调用网络 |

### `handaas_call.py`

用途：调用 Handaas 数据产品。

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--product` | 配置中的产品名，如 `工商照面` |
| `--keyword` | 企业 ID、企业名、统一社会信用代码等 |
| `--key-type` | `nameId`、`name`、`socialCreditCode`、`regNumber` |
| `--extra-json` | 额外请求参数 JSON |
| `--dry-run` | 只输出脱敏请求，不调用网络 |

### `link_enterprises.py`

用途：单个 L5 节点端到端企业挂链。

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--chain` | 产业链名称 |
| `--node` | L5 节点名称 |
| `--path` | 完整节点路径 |
| `--condition-file` | 使用已有条件 JSON |
| `--page-size` | 高筛候选数量 |
| `--with-evidence` | 对候选企业调用 Handaas 证据产品 |
| `--evidence-product` | 限定证据产品，可重复 |
| `--dry-run` | 只输出条件和脱敏请求 |

## 输出与决策口径

企业挂链输出中的 `decision`：

| decision | 含义 | 建议动作 |
| --- | --- | --- |
| `confirmed` | 有招聘、专利、招投标等强证据命中 L5 节点 | 可确认挂链 |
| `uncertain` | 只有中弱证据，或高筛召回但证据不足 | 人工复核 |
| `rejected` | 明显不相关或只有弱证据且业务冲突 | 剔除并补充排除词 |

证据强度：

| 强度 | 典型来源 |
| --- | --- |
| strong | 招聘岗位/描述、专利名称、招投标标题/标的、工厂/资质/产品认证 |
| medium | 经营范围、企业简介、业务关键词、国标行业、年报主营 |
| weak | 企业名称、注册资本、联系方式、地区、经营状态 |

## 故障排查

### 1. `未找到配置文件`

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

### 2. `仍是占位值`

说明配置中还有 `your_...` 或 `product_id_for_...`。真实调用前必须替换成自己的 Handaas / high-screen 参数。

### 3. high-screen 返回参数错误或 2007

建议：

1. 先使用 `--dry-run` 检查请求结构。
2. 确认传给接口的是条件组对象，不要包裹 `condition` / `filter` / `data` / `query`。
3. 减少复杂嵌套，先用基础 `must` + 一个业务 `should` + 少量 `must_not`。
4. 检查字段名和操作符是否被当前 high-screen 产品支持。

### 4. 高筛命中太宽

增加：

- `--industry` 行业路径
- `--exclude` 排除词
- 更具体的 `--keyword`

示例：

```bash
python scripts/build_condition.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --industry "制造业/铁路、船舶、航空航天和其他运输设备制造业" \
  --exclude "航空培训" \
  --exclude "旅游观光"
```

### 5. Handaas 产品找不到

检查配置中的产品名是否与命令一致：

```json
"products": {
  "工商照面": "...",
  "招聘明细": "..."
}
```

命令中的 `--product` 必须使用这些 key。

### 6. 真实接口调用超时

降低 `--page-size`，或只先运行 high-screen，不带 `--with-evidence`：

```bash
python scripts/link_enterprises.py \
  --chain "低空经济" \
  --node "eVTOL整机制造" \
  --page-size 5
```

## 安全边界

- 不提交真实 `handaas.config.json`。
- 不在 Git、日志、Issue、截图中暴露 `secret_id`、`secret_key`、signature、token。
- `--dry-run` 输出会脱敏敏感字段。
- 本仓库不托管用户数据，不保存调用结果。
- 带 `--with-evidence` 的命令会调用多个 Handaas 产品，可能产生接口费用。

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
```

首次推送到 GitHub：

```bash
cd /Users/sunjackson/Project/industry-chain-processing-skill
git remote add origin git@github.com:<your-name>/industry-chain-processing-skill.git
git push -u origin main
```

发布前检查：

```bash
git status --short
git grep -n "secret_key\|secret_id\|signature\|token" -- . ':!README.md' ':!industry-chain-processing/assets/config.example.json'
```

如果 grep 命中真实凭证，必须删除后再提交。
