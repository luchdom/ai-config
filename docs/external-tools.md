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

### .NET SDK 10

Link:
- [Install .NET on Windows](https://learn.microsoft.com/en-us/dotnet/core/install/windows)

Recommended for:
- Repos that target `net10.0`, including current Luchdom backend scaffolds.

Official install example from Microsoft Learn:

```powershell
winget install Microsoft.DotNet.SDK.10
```

Verify:

```powershell
dotnet --list-sdks
```

### GitHub CLI

Links:
- [GitHub CLI README](https://github.com/cli/cli)
- [GitHub CLI manual](https://cli.github.com/manual/index)

Recommended for:
- local PR workflows
- manual repo inspection
- auth verification outside MCP

Repo workflow:
- Use `$github-cli` for safe read-first GitHub CLI workflows.
- Use `$pr-description` before drafting or updating PR titles and bodies.

After install, authenticate with:

```powershell
gh auth login
gh auth status
```

### RTK

Links:
- [RTK repository](https://github.com/rtk-ai/rtk)
- [RTK releases](https://github.com/rtk-ai/rtk/releases)

Recommended for:
- reducing noisy command output before it reaches an agent context

Windows setup:

- Download `rtk-x86_64-pc-windows-msvc.zip` from the releases page.
- Put `rtk.exe` on `PATH`, such as `%USERPROFILE%\.local\bin`.
- Use it from PowerShell, Command Prompt, or Windows Terminal; do not launch the executable directly.

Enable RTK for a supported agent only after reviewing its telemetry behavior:

```powershell
rtk init -g --codex
rtk --version
rtk gain
```

Restart the agent after initialization. Native Windows supports RTK filtering, though automatic hook rewriting is more limited than WSL.

### CodeGraph

Links:
- [CodeGraph repository](https://github.com/colbymchenry/codegraph)

Recommended for:
- indexed codebase exploration in larger repositories where symbol search, call paths, or impact analysis reduce repeated file searches

Official setup:

```powershell
npx @colbymchenry/codegraph
codegraph init
codegraph install --print-config codex
```

Notes:

- `codegraph init` creates the local `.codegraph/` index; do not commit it.
- Use CodeGraph only for supported, indexed files. Fall back to `rg` and direct reads when indexing is unavailable or incomplete.
- CodeGraph may append its own configuration to instruction files. This repo's marker-managed project templates preserve content outside their managed marker block during normal sync.

### AWS CLI

Link:
- [Installing or updating the latest AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Recommended for:
- repos that eventually provision or inspect AWS resources outside the editor

Official Windows MSI command from the AWS docs:

```powershell
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

Verify:

```powershell
aws --version
```

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

### PostHog CLI + Skills

Links:
- [PostHog CLI package](https://www.npmjs.com/package/@posthog/cli)
- [PostHog CLI source map upload docs](https://posthog.com/docs/error-tracking/upload-source-maps/cli)
- [PostHog skills store docs](https://posthog.com/docs/prompt-management/skills-store)
- [PostHog AI plugin](https://github.com/PostHog/ai-plugin)

Recommended for:
- PostHog setup, analytics inspection, source map workflows, and product-instrumentation work where CLI + skill usage is preferred over MCP.

Preferred local install:

```powershell
npm install -g @posthog/cli
posthog-cli login
posthog-cli --help
```

PostHog's CLI docs also provide a native installer:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://download.posthog.com/cli | iex"
posthog-cli login
posthog-cli --help
```

Notes:
- Prefer local skills plus `posthog-cli` commands for coding-agent workflows.
- Use the PostHog MCP server or PostHog AI plugin only when you explicitly want remote PostHog product tools or the PostHog-hosted skills store.
- The PostHog skills store is a centralized, versioned store for Agent Skills-style `SKILL.md` bodies plus optional bundled files.
- Its remote workflow depends on PostHog Prompt Management and the PostHog MCP tools such as `skill-list`, `skill-get`, `skill-file-get`, `skill-create`, and `skill-update`.
- If you choose to use the official PostHog AI plugin, it ships a `skills-store` bridge skill plus additional PostHog task skills.

Optional Codex plugin install from the PostHog AI plugin README:

```powershell
codex plugin marketplace add PostHog/ai-plugin
codex
# Then run /plugins, select PostHog, and install.
/plugins
```

Self-hosted PostHog note:

```powershell
$env:POSTHOG_MCP_URL = "https://mcp.your-posthog-instance.com/mcp"
```

### Stripe AI Skills

Links:
- [Stripe AI repo skills](https://github.com/stripe/ai/tree/main/skills)
- [Build on Stripe with AI](https://docs.stripe.com/building-with-ai)

Recommended for:
- Stripe integration design, review, upgrade, and best-practice checks.
- Payment, billing, Connect, webhook, sandbox, and Stripe API version work.

Current upstream skills in the GitHub `skills/` directory:

- `stripe-best-practices`
- `stripe-directory`
- `stripe-projects`
- `upgrade-stripe`

Official project-local skill install from Stripe docs:

```powershell
npx skills add https://docs.stripe.com
```

Official Codex plugin install from Stripe docs:

```powershell
codex plugin add stripe@openai-curated
```

Official Claude Code plugin install from Stripe docs:

```powershell
claude plugin install stripe@claude-plugins-official
```

Stripe sandbox bootstrap from Stripe docs:

```powershell
stripe sandbox create
```

Notes:
- Run the skill or plugin install from the project folder that needs Stripe guidance.
- Manually added skills do not auto-update; pull or reinstall updates when Stripe changes the catalog.
- `stripe sandbox create` provisions an anonymous, claimable sandbox with API keys and does not require an account up front.
- Prefer official Stripe docs, hosted skills, and plugins over copying stale local skill snapshots.

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

### Linear MCP

Link:
- [Linear MCP server docs](https://linear.app/docs/mcp)

Recommended for:
- issue intake and status updates in repos that use Linear as the autonomous work queue

Official Codex setup from the Linear docs:

```powershell
codex mcp add linear --url https://mcp.linear.app/mcp
codex mcp login linear
```

The Linear docs also note that some Codex versions require the remote MCP feature to be enabled in `~/.codex/config.toml`.

### Slack Approval Integration

Links:
- [Slack app quickstart](https://docs.slack.dev/quickstart/)
- [Slack incoming webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/)

Recommended for:
- approval requests from autonomous coding runs
- high-risk or cost-bearing decision notifications

Recommended policy:

- start with a small Slack app, not an undocumented side channel
- post approval requests to a dedicated channel such as `#codex-approvals`
- persist every Slack approval back into repo or issue artifacts
- do not treat Slack as the source of truth

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
- [PostHog CLI package](https://www.npmjs.com/package/@posthog/cli)
- [PostHog CLI source map upload docs](https://posthog.com/docs/error-tracking/upload-source-maps/cli)
- [PostHog skills store docs](https://posthog.com/docs/prompt-management/skills-store)
- [PostHog AI plugin](https://github.com/PostHog/ai-plugin)
- [stripe/ai skills](https://github.com/stripe/ai/tree/main/skills)
- [Build on Stripe with AI](https://docs.stripe.com/building-with-ai)
- [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills)
- [openai/skills](https://github.com/openai/skills)
