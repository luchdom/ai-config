# Site Audit Checklist

Use this checklist before editing an existing Jekyll or GitHub Pages site.

## Project Shape

- Confirm the site root: repository root, `/docs`, or another configured source.
- Read `_config.yml` or `_config.toml` for `title`, `url`, `baseurl`, theme, plugins, collections, defaults, excludes, includes, permalink rules, Sass settings, and markdown processor.
- Read `Gemfile` and `Gemfile.lock` to identify whether the site uses `github-pages`, direct `jekyll`, a theme gem, or custom plugins.
- Check `.github/workflows/` for Pages deployment workflows and build commands.
- Check branch/source settings in docs, README, or repository notes when available.

## Content And Templates

- Map pages, posts, collections, `_data`, `_layouts`, `_includes`, `_sass`, `assets`, static files, `404.html`, `robots.txt`, `sitemap.xml`, and `CNAME`.
- For theme-based sites, inspect overridden files in the repo first; use `bundle info <theme-gem>` only when local theme source is needed.
- Verify front matter on pages that should be rendered by Jekyll. Files without front matter may be copied as static files instead of processed.
- Check Liquid includes for missing variables, unescaped user-visible data, broken loops, or assumptions about optional data fields.

## GitHub Pages Fit

- Native Pages builds must stay within supported GitHub Pages dependency and plugin versions.
- Actions builds may use newer Jekyll, additional plugins, custom asset steps, and custom build commands, but still deploy a static artifact.
- Confirm `baseurl` and asset paths work for user/organization pages, project pages, custom domains, and local preview.

## Change Safety

- Preserve existing URLs and permalinks unless the requested change explicitly includes redirects or URL cleanup.
- Preserve custom domain files, analytics snippets, SEO tags, feed/sitemap behavior, and configured collections.
- Keep generated outputs such as `_site`, `.jekyll-cache`, and `.sass-cache` out of source changes unless the repo intentionally publishes generated static output.
