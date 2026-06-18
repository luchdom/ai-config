# Validation Checklist

Use this before finishing Jekyll/GitHub Pages work.

## Local Build

- Run `bundle install` when dependencies changed or gems are missing.
- Run `bundle exec jekyll build`.
- For local preview, run `bundle exec jekyll serve` or `bundle exec jekyll serve --livereload` when interactive review is needed.
- If Ruby 3 reports a missing WEBrick server during `serve`, add or recommend `bundle add webrick` only when it fits the repo dependency policy.

## Output Review

- Inspect `_site` only as generated output unless the repo intentionally publishes built files.
- Check rendered homepage, important pages, custom 404 page, metadata, CSS, images, and JavaScript.
- Verify links, mailto/tel links, social URLs, project URLs, and downloadable files.
- Confirm absolute, relative, and `baseurl` paths work for local preview and the intended Pages URL.

## Accessibility And Responsive Checks

- Use semantic landmarks: header, main, nav where needed, sections, footer.
- Ensure one clear `h1`, sensible heading order, descriptive link text, alt text for meaningful images, and visible keyboard focus.
- Check mobile, tablet, and desktop widths.
- Keep tap targets usable and text readable without horizontal scrolling.
- Respect `prefers-reduced-motion` for animation-heavy designs.

## Deployment Checks

- Native Pages: confirm dependencies and plugins are supported by GitHub Pages.
- Actions Pages: confirm workflow builds, uploads `_site`, deploys the Pages artifact, and has the required permissions.
- Preserve `CNAME` and custom domain settings when present.
- Confirm README or project docs mention the local build command and selected deployment mode when non-obvious.
