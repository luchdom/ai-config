# External Tools and Remote Resources

Use this document when setting up additional tools, remote skills, MCP servers, or reference catalogs on a new machine.

## Install Order

Recommended order:

1. Install this repo's generated agents and skills first.
2. Install external CLI tools and skills that should live in user home directories.
3. Add MCP servers only when you actually want MCP for that tool.
4. Restart Codex or Claude Code after new skills are installed.

## Install This Repo First

From the `ai-config` repo root:

```powershell
python .\scripts\build.py
python .\scripts\sync.py --tool all
```

If project-local instruction files are also needed:

```powershell
python .\scripts\sync.py --tool all --project C:\path\to\repo
```

## Recommended External Installs

### Playwright CLI + Skills

Link:
- [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli)

Why:
- Recommended for coding-agent workflows when you want CLI + skill usage instead of MCP.

Official install from the Playwright CLI README:

```powershell
npm install -g @playwright/cli@latest
playwright-cli install --skills
playwright-cli --help
```

Notes:
- The Playwright CLI README says CLI + skills is the better fit for coding agents, while MCP is better for persistent introspection-heavy loops.
- After skill installation, restart the agent so it discovers the new skills.
- You can prefer this over Playwright MCP in repos where token efficiency matters more than persistent browser context.

### Playwright MCP

Link:
- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)

Use when:
- You explicitly want MCP-based browser automation rather than Playwright CLI skills.

Official examples:

```powershell
claude mcp add playwright npx @playwright/mcp@latest
codex mcp add playwright npx "@playwright/mcp@latest"
```

Codex config alternative from the repository README:

```toml
[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest"]
```

### Interface Design

Link:
- [Dammyjay93/interface-design](https://github.com/Dammyjay93/interface-design)

Recommended for:
- Claude Code design-oriented UI work.

Official recommended install:

```text
/plugin marketplace add Dammyjay93/interface-design
/plugin menu
```

Manual install from the repository README:

```powershell
git clone https://github.com/Dammyjay93/interface-design.git
cd interface-design
cp -r .claude/* ~/.claude/
cp -r .claude-plugin/* ~/.claude-plugin/
```

Notes:
- Restart Claude Code after installation.
- The repo is plugin-oriented; do not treat it as a Codex skill unless you intentionally adapt it.

### Napkin

Link:
- [blader/napkin](https://github.com/blader/napkin)

Recommended for:
- Per-repo persistent memory in Claude Code or Codex.

Official install commands:

```powershell
git clone https://github.com/blader/napkin.git ~/.claude/skills/napkin
git clone https://github.com/blader/napkin.git ~/.codex/skills/napkin
```

Notes:
- The repository states that the skill activates every session.
- It writes a per-repo markdown file for accumulated working memory.

### Firecrawl CLI + Skill

Link:
- [Firecrawl CLI docs](https://docs.firecrawl.dev/sdks/cli)

Recommended for:
- AI-agent web extraction, crawl, search, and browser workflows.

Official one-shot init from the Firecrawl docs:

```powershell
npx -y firecrawl-cli@latest init --all --browser
```

The docs say:
- `--all` installs the Firecrawl skill to every detected AI coding agent.
- `--browser` opens the browser for Firecrawl authentication automatically.

Observed install behavior on Windows:

- Firecrawl installs shared skills under `~/.agents/skills/` and then wires supported tools such as Codex and Claude Code to those shared skills.
- This means the Firecrawl skills may not appear directly under `~/.codex/skills` or `~/.claude/skills` even when installation succeeded.
- Authentication may still be required after skill installation.

Manual global install from the docs:

```powershell
npm install -g firecrawl-cli
firecrawl login --browser
firecrawl view-config
```

If the `firecrawl` command is not immediately available in the current shell on Windows, use:

```powershell
npx -y firecrawl-cli@latest login --browser
npx -y firecrawl-cli@latest view-config
```

### OpenAI Curated Linear Skill

Link:
- [openai/skills linear skill](https://github.com/openai/skills/blob/main/skills/.curated/linear/SKILL.md)

Recommended for:
- Codex workflows that read, create, or update Linear issues using the Linear MCP server.

Global install behavior:

- Installs under `~/.codex/skills/linear`
- This is a global Codex skill, not a project-local skill

Install with the built-in skill installer:

```powershell
python "$HOME\\.codex\\skills\\.system\\skill-installer\\scripts\\install-skill-from-github.py" --url https://github.com/openai/skills/tree/main/skills/.curated/linear
```

Notes:

- Restart Codex after installation so the skill is discovered.
- The skill expects the Linear MCP server to be configured.
- The installed skill says to add Linear MCP with:

```powershell
codex mcp add linear --url https://mcp.linear.app/mcp
```

- The installed skill also says remote MCP client support must be enabled with either:

```toml
[features]
rmcp_client = true
```

or:

```powershell
codex --enable rmcp_client
```

## Reference Catalogs

Use these as discovery sources for reusable skills and patterns:

- [anthropics/skills catalog](https://github.com/anthropics/skills/tree/main/skills)
- [openai/skills catalog](https://github.com/openai/skills)

OpenAI-specific note from the catalog:

- Curated or experimental Codex skills can be installed with `$skill-installer`.
- The catalog README shows that a GitHub directory URL can be installed directly, for example:

```text
$skill-installer install https://github.com/openai/skills/tree/main/skills/.experimental/create-plan
```

## Recommended Policy For This Repo

- Prefer Playwright CLI + skills over Playwright MCP for coding-agent workflows unless persistent MCP state is specifically needed.
- Keep reusable cross-tool workflows in `src/skills/`.
- Keep tool-specific setup instructions here instead of scattering them across repo docs.
- When an agent is asked to install all AI tooling from this repo on a new machine, it should:
  1. install this repo's generated outputs
  2. install the recommended external tools listed above
  3. verify the installed commands or directories
  4. restart Codex or Claude Code if needed

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)
- [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli)
- [Dammyjay93/interface-design](https://github.com/Dammyjay93/interface-design)
- [blader/napkin](https://github.com/blader/napkin)
- [Firecrawl CLI docs](https://docs.firecrawl.dev/sdks/cli)
- [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills)
- [openai/skills](https://github.com/openai/skills)
