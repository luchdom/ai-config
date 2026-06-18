# GitHub Pages Deploy Options

Use this when choosing or changing how a Jekyll site deploys to GitHub Pages.

## Native GitHub Pages Build

Use native Pages when:

- The site can use the GitHub Pages supported Jekyll version, themes, and plugins.
- The repo should stay simple and avoid workflow maintenance.
- The site is mostly Markdown, Liquid, Sass, data files, static assets, and supported plugins.

Implementation notes:

- Use `gem "github-pages", group: :jekyll_plugins` when local dependency parity with Pages matters.
- Check `https://pages.github.com/versions/` before pinning versions or adding plugins.
- Keep unsupported plugins out of `_config.yml`.
- For project pages, set `baseurl: "/repo-name"` unless a custom domain or alternate deployment setup changes this.

## GitHub Actions Pages Build

Use Actions when:

- The site needs modern Jekyll, unsupported plugins, custom gems, custom build steps, npm asset tooling, or strict reproducible builds.
- The repo wants build/test checks before deployment.
- The site should deploy a generated `_site` artifact rather than rely on Pages' native Jekyll builder.

Implementation notes:

- Build with Bundler in the workflow.
- Run `bundle exec jekyll build`.
- Upload `_site` with `actions/upload-pages-artifact`.
- Deploy with `actions/deploy-pages`.
- Ensure workflow permissions include `contents: read`, `pages: write`, and `id-token: write` for deployment.

## Keep Both Paths Honest

- Do not present Actions as mandatory for simple Pages-compatible sites.
- Do not force native Pages when requirements need unsupported plugins or custom build behavior.
- Document the selected mode in README or repo docs when the choice affects local setup or deployment.
- Validate locally with the same Gemfile and command path that deployment will use.
