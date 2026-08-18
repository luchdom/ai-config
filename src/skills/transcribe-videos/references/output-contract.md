# Output contract

## Directory shape

For one video:

```text
<output-root>/<video-slug>/
├── summary.md
└── transcript.md
```

For a course, create one direct child per lesson. Use lowercase ASCII slugs with hyphens and preserve the sidebar order through lesson numbers when available.

In text-only mode, those two Markdown files are the complete allowed file set for every lesson directory.

## `summary.md`

Use this structure, adapting headings to the content:

```markdown
# Summary — <title>

[Read the detailed transcript](./transcript.md)

## Source

- **Course/channel:** <name>
- **Phase:** <phase, when applicable>
- **Lesson/video:** <title>
- **Duration:** <duration>
- **Language:** <language>
- **Page:** [Source](<page-url>) — requires authenticated access, when applicable

## Summary

<substantive overview>

## Key points

<organized takeaways>
```

Translate headings and prose to the requested output language. Add sections for practical actions, tables, warnings, transitions, promotional material, or professional-advice caveats when the source contains them.

## `transcript.md`

Use this structure, translated to the requested output language:

```markdown
# Detailed transcript — <title>

> This is a comprehensive, non-literal transcript organized by time. It preserves the video’s sequence and guidance without reproducing protected content word for word. Timestamps are approximate.

[Read the summary](./summary.md)

## 00:00–01:10 — <section title>

<complete paraphrase of this interval>
```

Create meaningful timestamp ranges rather than one heading per raw speech segment. Preserve every substantive claim, example, instruction, caveat, transition, and sales section. Remove filler and duplicated speech without omitting meaning.

## Editorial checks

- Correct names and domain terms only when page text or context supports the correction.
- Keep uncertain wording conservative; never fabricate a missing sentence.
- Distinguish the speaker’s claims from independently verified facts.
- Do not place signed media URLs, tokens, cookies, local cache paths, or raw player payloads in either document.
- Use natural language for visible prose while keeping filenames stable and ASCII-safe.
