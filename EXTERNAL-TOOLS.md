# External Tools and Remote Resources

Use this document when setting up additional tools, remote skills, MCP servers, or reference catalogs on a new machine.

## Install Order

Recommended order:

1. Install this repo's generated agents and skills first.
2. Install external CLI tools and skills that should live in user home directories.
3. Add MCP servers only when you actually want MCP for that tool.
4. Restart Codex or Claude Code after new skills are installed.

## Install This Repo First

From the `ai-toolkit` repo root:

```powershell
python .\scripts\build.py
python .\scripts\sync.py --tool all
```

If project-local tool instructions are also needed:

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
- CodeGraph may append its own configuration to instruction files. This repo's marker-managed tool instructions preserve content outside their managed marker block during normal sync.

### Codebase Memory MCP

Links:
- [Codebase Memory MCP repository](https://github.com/DeusData/codebase-memory-mcp)
- [Codebase Memory MCP releases](https://github.com/DeusData/codebase-memory-mcp/releases)

Recommended for:
- persistent local knowledge-graph indexing for code discovery
- structural symbol search, caller/callee tracing, architecture analysis, change-impact mapping, and index-coverage checks through MCP

Official Windows install:

```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.ps1 -OutFile install.ps1
notepad .\install.ps1
Unblock-File .\install.ps1
.\install.ps1
```

Official macOS/Linux install:

```bash
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
```

Verify the binary and Codex registration:

```powershell
codebase-memory-mcp --version
codex mcp get codebase-memory-mcp
```

Notes:

- Inspect the installer before running it. The install command auto-detects supported agents and may update their user-level MCP configuration, instructions, skills, and lifecycle hooks.
- The native server runs locally without an API key. Restart open coding-agent sessions after installation, then ask the agent to `Index this project`.
- On Windows, Codex Desktop may grant `%TEMP%` mutation rights to `CodexSandboxUsers`, causing installation to fail closed with `acl-grants-cross-account-mutation`. Retry with a private user-owned staging directory rather than weakening the existing ACLs:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\cbm-stage" | Out-Null
$env:TMP = "$env:USERPROFILE\cbm-stage"
$env:TEMP = "$env:USERPROFILE\cbm-stage"
.\install.ps1
```

- The Codex MCP registration name is `codebase-memory-mcp`.

### Graphify

Links:
- [Graphify repository](https://github.com/Graphify-Labs/graphify)
- [Graphify package on PyPI](https://pypi.org/project/graphifyy/)

Recommended for:
- supplementary local knowledge-graph extraction and queries
- code-only AST indexing that does not require an API key
- a portable JSON graph that can combine multiple repositories

Install the official PyPI package in an isolated environment, then install its
Codex-specific skill globally:

```powershell
uv tool install graphifyy
graphify install --platform codex
```

Verify:

```powershell
graphify --version
Test-Path "$HOME\.codex\skills\graphify\SKILL.md"
```

Codex parallel extraction also expects this existing feature setting:

```toml
[features]
multi_agent = true
```

For the active Luchdom repositories, keep generated graphs outside the Git
worktrees and use local AST-only extraction. `--code-only` skips docs, PDFs, and
images and does not call an LLM:

```powershell
graphify extract C:\dev\luchdom\saas --code-only --out "$HOME\.codex\graphify-indexes\saas"
graphify extract C:\dev\luchdom\my-finance --code-only --out "$HOME\.codex\graphify-indexes\my-finance"

graphify global add "$HOME\.codex\graphify-indexes\saas\graphify-out\graph.json" --as saas
graphify global add "$HOME\.codex\graphify-indexes\my-finance\graphify-out\graph.json" --as my-finance
graphify global list
graphify global path
```

Notes:

- The PyPI distribution is `graphifyy`; the installed command is `graphify`.
- Use `$graphify` in Codex to invoke the skill explicitly.
- The global skill install above does not modify a repository. By contrast,
  `graphify codex install` writes an always-on section to the current
  `AGENTS.md` and registers `.codex/hooks.json`. Do not run that project command
  automatically in Luchdom repositories, whose instruction files and primary
  Codebase Memory policy are already repository-owned.
- Full semantic extraction can process docs and media through an LLM backend.
  Do not omit `--code-only` for private repositories unless the user has
  explicitly approved the selected provider and data boundary.
- Graphify and Codebase Memory are separate indexes. Neither index is proof of
  exhaustive source coverage; use direct source reads for reported gaps.

### Ponytail

Link:
- [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)

Recommended for:
- YAGNI and standard-library-first implementation guidance
- diff and repository reviews focused on unnecessary complexity

Install the native Codex plugin from its official marketplace:

```powershell
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

Verify:

```powershell
codex plugin list
node --version
```

Notes:

- The plugin uses small Node.js lifecycle hooks, so `node` must be on `PATH`.
- Restart Codex after installation. Open `/hooks`, inspect the Ponytail hooks,
  and trust them only after review.
- Codex exposes the bundled commands as skills, such as `@ponytail`,
  `@ponytail-review`, and `@ponytail-audit`.
- The default mode is `full`; use `@ponytail off` when its always-on minimalism
  is not appropriate for a task.
- Uninstall with `codex plugin remove ponytail@ponytail`.

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

### UI/UX Pro Max

Link:
- [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)

Recommended for:
- searchable UI/UX, accessibility, typography, color, chart, motion, and
  stack-specific implementation guidance
- global Codex design skills with bundled local datasets and Python search tools

Install the official CLI and generate its Codex skill bundle globally:

```powershell
npm install -g ui-ux-pro-max-cli
uipro init --ai codex --global
```

Verify:

```powershell
uipro --version
Test-Path "$HOME\.agents\skills\ui-ux-pro-max\SKILL.md"
```

Notes:

- The Codex target installs under `~/.agents/skills/`, including the
  `ui-ux-pro-max` orchestrator and its bundled sibling design skills.
- The bundled search scripts use Python 3 standard-library modules and do not
  require a network connection.
- Restart Codex after installation.
- Update the CLI and regenerate the global bundle with:

```powershell
uipro update
uipro init --ai codex --global --force
```

### Taste Skill

Link:
- [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill)

Recommended for:
- opinionated anti-generic visual direction for frontend work
- a stricter GPT/Codex-specific design and motion skill

Install the upstream Codex-oriented `gpt-taste` skill with Codex's built-in
GitHub skill installer:

```powershell
python "$HOME\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" `
  --repo Leonxlnx/taste-skill `
  --path skills/gpt-tasteskill `
  --name gpt-taste
```

Verify:

```powershell
Test-Path "$HOME\.codex\skills\gpt-taste\SKILL.md"
```

Notes:

- This repository already ships a GPT/Codex-specific skill, so no Claude-only
  conversion is needed.
- The repository also contains separate skills for image generation, redesign,
  minimalist, brutalist, and other styles. Install only the variant needed for
  the task so overlapping auto-trigger descriptions do not compete.
- Restart Codex after installation.

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

### MemPalace

Links:
- [MemPalace repository](https://github.com/MemPalace/mempalace)
- [MemPalace official documentation](https://mempalaceofficial.com/guide/getting-started.html)
- [MemPalace MCP integration](https://mempalaceofficial.com/guide/mcp-integration.html)

Recommended for:
- local persistent semantic memory across projects and conversations
- a writable MCP memory palace with project wings, rooms, entity relationships,
  and agent diaries

Install the official PyPI package in an isolated environment, then install the
native Codex plugin:

```powershell
uv tool install mempalace
codex plugin marketplace add MemPalace/mempalace
codex plugin add mempalace@mempalace
```

Verify the CLI and the plugin-provided MCP server:

```powershell
mempalace --version
codex plugin list
codex mcp get mempalace
mempalace status
```

Initialize and mine only an approved source directory. Use `--no-llm` when the
initial entity scan must remain local:

```powershell
mempalace init C:\path\to\approved-source --no-llm --yes --auto-mine --lang en,pt-br
```

For dirty repositories or repositories with private untracked files, create a
clean tracked-only local clone under `~/.mempalace/sources/` and mine that copy.
This preserves the working tree and prevents unrelated untracked artifacts from
entering the palace:

```powershell
git clone --no-hardlinks --single-branch --branch main C:\dev\luchdom\saas "$HOME\.mempalace\sources\saas"
git clone --no-hardlinks --single-branch --branch main C:\dev\luchdom\my-finance "$HOME\.mempalace\sources\my-finance"

mempalace init "$HOME\.mempalace\sources\saas" --no-llm --yes --auto-mine --lang en,pt-br
mempalace init "$HOME\.mempalace\sources\my-finance" --no-llm --yes --auto-mine --lang en,pt-br
```

Notes:

- MemPalace stores and returns mined text verbatim. Never mine secrets, raw
  financial documents, provider payloads, private transcripts, or other content
  that is outside the approved memory boundary.
- Project mining respects `.gitignore` by default. A clean tracked-only clone is
  still the safer boundary when the live checkout contains unrelated changes.
- The default Chroma/ONNX embedding path is local and needs no API key. The first
  mine downloads the embedding model and may take several minutes.
- The plugin registers `mempalace-mcp` and includes writable memory tools and
  auto-save hooks. Restart Codex and review the plugin hooks before trusting
  automatic transcript saves.
- The plugin and PyPI package can briefly publish at different versions. The
  executable on `PATH` controls the MCP runtime; use `mempalace --version` and
  `mempalace status` to verify it, then restart Codex after an upgrade.

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
- [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)
- [Codebase Memory Windows Codex ACL issue](https://github.com/DeusData/codebase-memory-mcp/issues/1529)
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)
- [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)
- [Dammyjay93/interface-design](https://github.com/Dammyjay93/interface-design)
- [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill)
- [blader/napkin](https://github.com/blader/napkin)
- [MemPalace/mempalace](https://github.com/MemPalace/mempalace)
- [MemPalace official docs](https://mempalaceofficial.com/guide/getting-started.html)
- [Firecrawl CLI docs](https://docs.firecrawl.dev/sdks/cli)
- [PostHog CLI package](https://www.npmjs.com/package/@posthog/cli)
- [PostHog CLI source map upload docs](https://posthog.com/docs/error-tracking/upload-source-maps/cli)
- [PostHog skills store docs](https://posthog.com/docs/prompt-management/skills-store)
- [PostHog AI plugin](https://github.com/PostHog/ai-plugin)
- [stripe/ai skills](https://github.com/stripe/ai/tree/main/skills)
- [Build on Stripe with AI](https://docs.stripe.com/building-with-ai)
- [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills)
- [openai/skills](https://github.com/openai/skills)
