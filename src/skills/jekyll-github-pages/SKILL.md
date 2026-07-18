---
name: jekyll-github-pages
description: Work with Jekyll sites hosted on GitHub Pages, including existing-site audits, local Bundler/Jekyll builds, Liquid layouts and includes, _config.yml, data files, Sass/assets, Pages deployment, GitHub Actions Pages workflows, custom domains, personal portfolio sites, vCards, and full customizable static site scaffolding. Use when Codex needs to create, customize, debug, migrate, or validate a Jekyll/GitHub Pages site.
---

# Jekyll GitHub Pages

Build and maintain Jekyll sites that deploy cleanly to GitHub Pages. Prefer repo-local instructions first, then use this skill for Jekyll, Liquid, Bundler, GitHub Pages, and vCard-site workflow.

## Default Workflow

1. Read `AGENTS.md`, the active registered `docs-ai/<work-key>-<slug>/` artifacts when present, README, `_config.yml`, `Gemfile`, `.github/workflows/`, and the nearest site docs before changing a site. Use explicitly supplied numbered-and-dated or flat workflow artifacts only as historical read fallback and never rewrite them.
2. Identify the deployment mode:
   - Native GitHub Pages build from a branch/source folder.
   - GitHub Actions build that uploads a Pages artifact.
3. Inspect Jekyll shape: `_layouts`, `_includes`, `_data`, `_sass`, `assets`, collections, pages, posts, theme settings, plugins, and custom domain files.
4. Choose the smallest site structure that supports the requested content and customization.
5. Use Bundler for local commands: `bundle install`, `bundle exec jekyll build`, and `bundle exec jekyll serve`.
6. Validate generated output, links, metadata, responsive behavior, accessibility basics, and deployment assumptions before finishing.

## Deployment Rules

- Treat native GitHub Pages and GitHub Actions Pages as equal first-class options.
- For native Pages, check the current dependency and supported plugin list at `https://pages.github.com/versions/` before pinning gems or adding plugins.
- For Actions Pages, prefer a workflow that builds with Bundler, runs `jekyll build`, uploads `_site`, and deploys via the official Pages actions.
- Do not add unsupported plugins to a native Pages build. If unsupported plugins, modern Jekyll, custom Ruby dependencies, or custom build steps are required, use Actions or document the constraint.
- Keep `baseurl` correct for project pages. User/organization pages usually use an empty `baseurl`; project pages usually use `/<repo-name>`.

Read [references/github-pages-deploy-options.md](./references/github-pages-deploy-options.md) before changing deployment mode or adding dependencies.

## vCard Sites

For a new personal vCard, portfolio, or link-in-bio site, make the content data-driven and theme-independent:

- Store profile content in `_data/profile.yml`.
- Build layouts and includes directly in the repo instead of relying on a theme unless the user asked for theme customization.
- Keep CSS custom properties and Sass partials organized for easy color, type, spacing, and section customization.
- Include strong first-viewport identity: name, role/headline, avatar or visual mark, location, primary contact action, and important links.
- Design for small-screen scanning first, then expand to richer desktop layout.

Read [references/vcard-starter-spec.md](./references/vcard-starter-spec.md) before scaffolding a full vCard or portfolio site.

## Existing-Site Audit

Read [references/site-audit-checklist.md](./references/site-audit-checklist.md) when modifying an existing site or debugging a build.

## Validation

Read [references/validation-checklist.md](./references/validation-checklist.md) before final verification. If Ruby, Bundler, or Jekyll is unavailable, report the missing tool and validate static file structure plus configuration as far as possible.

## Source Docs To Recheck

- Jekyll docs: `https://jekyllrb.com/docs/`
- Jekyll directory structure: `https://jekyllrb.com/docs/structure/`
- Jekyll data files: `https://jekyllrb.com/docs/datafiles/`
- Jekyll assets and Sass: `https://jekyllrb.com/docs/assets/`
- GitHub Pages with Jekyll: `https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/about-github-pages-and-jekyll`
- GitHub Pages custom workflows: `https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages`
- GitHub Pages dependency versions: `https://pages.github.com/versions/`
