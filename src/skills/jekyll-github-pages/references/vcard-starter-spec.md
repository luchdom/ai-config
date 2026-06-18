# vCard Starter Spec

Use this as the default structure for a full customizable Jekyll vCard, personal profile, link-in-bio, or lightweight portfolio site.

## File Structure

```text
.
|-- _config.yml
|-- Gemfile
|-- index.html
|-- 404.html
|-- _data/
|   `-- profile.yml
|-- _includes/
|   |-- head.html
|   |-- profile-hero.html
|   |-- link-list.html
|   |-- project-list.html
|   |-- social-links.html
|   `-- footer.html
|-- _layouts/
|   |-- default.html
|   `-- home.html
|-- _sass/
|   |-- _base.scss
|   |-- _layout.scss
|   |-- _components.scss
|   `-- _utilities.scss
|-- assets/
|   |-- css/
|   |   `-- main.scss
|   |-- images/
|   `-- js/
`-- README.md
```

Add `CNAME`, `robots.txt`, `sitemap.xml`, feeds, posts, or collections only when the site requires them.

## Data Model

Use `_data/profile.yml` for user-editable content:

```yaml
name: "Full Name"
headline: "Role or positioning statement"
location: "City, Region"
avatar: "/assets/images/avatar.jpg"
bio: "Short bio written for quick scanning."
primary_action:
  label: "Email"
  url: "mailto:hello@example.com"
links:
  - label: "Portfolio"
    url: "https://example.com"
    icon: "external"
socials:
  - label: "GitHub"
    url: "https://github.com/example"
skills:
  - "Jekyll"
  - "Static sites"
projects:
  - name: "Project name"
    summary: "One-line outcome."
    url: "https://example.com/project"
```

Keep optional fields optional in Liquid templates. Use `if` guards before rendering sections.

## Layout And Includes

- `default.html` owns the document shell, skip link, head include, main landmark, and footer.
- `home.html` composes the vCard sections and renders `{{ content }}` only if page content is expected.
- `head.html` includes title, description, canonical URL, responsive viewport, favicon hooks, Open Graph/Twitter metadata, and stylesheet link.
- Section includes read from `site.data.profile` and render nothing when the needed data is absent.

## Styling

- Use `assets/css/main.scss` with front matter so Jekyll processes it.
- Store Sass partials in `_sass` and import them from `main.scss`.
- Use CSS custom properties for brand colors, surfaces, text, borders, focus, spacing, and radius.
- Keep the mobile layout a single readable column. Desktop may use a two-column profile/sidebar plus content layout when it improves scanning.
- Respect reduced motion and visible focus styles.

## Content Defaults

- First viewport: avatar or mark, name, headline, location, short bio, primary action, and key links.
- Secondary sections: socials, skills, projects, experience, services, testimonials, writing, or contact details as requested.
- Avoid placeholder content that looks real. Use clearly marked placeholders when the user has not supplied copy.
