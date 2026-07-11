# Operating-System Commands

Use this reference whenever installation, environment variables, local configuration, MCP startup, or command paths are involved. Detect the user's operating system and show only the matching command block unless a cross-platform comparison is requested.

## Python command

- macOS/Linux: prefer `python3` for creating the virtual environment, then use `python` after activation.
- Windows PowerShell: prefer `py -3` for creating the virtual environment, then use `python` after activation.

## Clone and virtual environment

### macOS / Linux

```bash
git clone https://github.com/handaas/industry-chain-processing-skill.git
cd industry-chain-processing-skill
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
git clone https://github.com/handaas/industry-chain-processing-skill.git
Set-Location industry-chain-processing-skill
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Install the Codex Skill

### macOS / Linux — copy installation

```bash
mkdir -p "$HOME/.codex/skills"
rm -rf "$HOME/.codex/skills/industry-chain-processing"
cp -R industry-chain-processing "$HOME/.codex/skills/"
```

### macOS / Linux — developer symlink

```bash
mkdir -p "$HOME/.codex/skills"
ln -sfn "$(pwd)/industry-chain-processing" \
  "$HOME/.codex/skills/industry-chain-processing"
```

### Windows PowerShell — copy installation

```powershell
$skillsRoot = Join-Path $HOME ".codex\skills"
$skillTarget = Join-Path $skillsRoot "industry-chain-processing"
New-Item -ItemType Directory -Force -Path $skillsRoot | Out-Null
Remove-Item -Recurse -Force $skillTarget -ErrorAction SilentlyContinue
Copy-Item -Recurse .\industry-chain-processing $skillTarget
```

### Windows PowerShell — developer junction

```powershell
$skillsRoot = Join-Path $HOME ".codex\skills"
$skillTarget = Join-Path $skillsRoot "industry-chain-processing"
$source = (Resolve-Path .\industry-chain-processing).Path
New-Item -ItemType Directory -Force -Path $skillsRoot | Out-Null
Remove-Item -Recurse -Force $skillTarget -ErrorAction SilentlyContinue
New-Item -ItemType Junction -Path $skillTarget -Target $source | Out-Null
```

## Remote MCP environment

### macOS / Linux

```bash
export INDUSTRY_CHAIN_MCP_TOKEN="<platform-token>"
# Or use a complete URL:
export INDUSTRY_CHAIN_MCP_URL="https://mcp.handaas.com/industry-chain/industry_chain?token=${INDUSTRY_CHAIN_MCP_TOKEN}"
```

### Windows PowerShell

```powershell
$env:INDUSTRY_CHAIN_MCP_TOKEN = "<platform-token>"
# Or use a complete URL:
$env:INDUSTRY_CHAIN_MCP_URL = "https://mcp.handaas.com/industry-chain/industry_chain?token=$($env:INDUSTRY_CHAIN_MCP_TOKEN)"
```

## Local MCP startup

### macOS / Linux

```bash
git clone https://github.com/handaas/industry-chain-mcp-server.git
cd industry-chain-mcp-server
python3 -m venv mcp_env
source mcp_env/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
${EDITOR:-nano} .env
./start_mcp_server.sh
```

In the Skill shell:

```bash
export INDUSTRY_CHAIN_MCP_URL="http://127.0.0.1:8000/mcp"
```

### Windows PowerShell

```powershell
git clone https://github.com/handaas/industry-chain-mcp-server.git
Set-Location industry-chain-mcp-server
py -3 -m venv mcp_env
Set-ExecutionPolicy -Scope Process Bypass
.\mcp_env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python .\server\mcp_server.py streamable-http
```

In the Skill PowerShell session:

```powershell
$env:INDUSTRY_CHAIN_MCP_URL = "http://127.0.0.1:8000/mcp"
```

## Create local direct configuration

Run these commands from the `industry-chain-processing-skill` repository root.

### macOS / Linux

```bash
mkdir -p "$HOME/.industry-chain-processing"
cp industry-chain-processing/assets/config.example.json \
  "$HOME/.industry-chain-processing/handaas.config.json"
${EDITOR:-nano} "$HOME/.industry-chain-processing/handaas.config.json"
export INDUSTRY_CHAIN_CONFIG="$HOME/.industry-chain-processing/handaas.config.json"
```

### Windows PowerShell

```powershell
$configRoot = Join-Path $HOME ".industry-chain-processing"
$configPath = Join-Path $configRoot "handaas.config.json"
New-Item -ItemType Directory -Force -Path $configRoot | Out-Null
Copy-Item .\industry-chain-processing\assets\config.example.json $configPath
notepad $configPath
$env:INDUSTRY_CHAIN_CONFIG = $configPath
```

## Validate from the repository root

The following commands avoid operating-system-specific installed paths.

### macOS / Linux

```bash
python industry-chain-processing/scripts/validate_config.py
python industry-chain-processing/scripts/mcp_client.py ping
python industry-chain-processing/scripts/mcp_client.py list-tools
```

### Windows PowerShell

```powershell
python .\industry-chain-processing\scripts\validate_config.py
python .\industry-chain-processing\scripts\mcp_client.py ping
python .\industry-chain-processing\scripts\mcp_client.py list-tools
```

## Command translation rules

- Bash line continuation `\` becomes PowerShell backtick `` ` ``; alternatively run the command on one line.
- Bash `export NAME=value` becomes PowerShell `$env:NAME = "value"`.
- Bash `cp`, `rm -rf`, and `mkdir -p` become PowerShell `Copy-Item`, `Remove-Item -Recurse -Force`, and `New-Item -ItemType Directory -Force`.
- Use repository-relative script paths in documentation whenever possible. Do not assume a fixed home directory or drive letter.
