# Reduce Autonomous Supervisor Prompt Context — Code Re-review

## Verdict

**CHANGES REQUESTED.** The repair closes the originally demonstrated same-line link forms, but one P2 bypass remains for a valid multiline reference definition. No P1 or P3 findings were identified.

## Reviewed target

- Baseline and current HEAD: `c1a421cc0e1966f0cde53a1e40c5519c588cc466` (`main`)
- Workflow: `c8804502-5267-4415-85f6-5db6b86d1a34`
- Re-review scope: the repaired local-link extraction and prompt-closure code in `validation/delivery_contracts.py` and its tests in `tests/test_delivery_contracts.py`
- Re-review date: 2026-07-19

## Finding

### P2 — A multiline Markdown reference definition still bypasses closure

`REFERENCE_DEFINITION_PATTERN` at `validation/delivery_contracts.py:89-92` permits only spaces or tabs between the definition colon and destination. Markdown reference definitions may place the destination on the following line. For example:

```md
[details][protocol]

[protocol]:
  delivery-stages.md
```

The repaired `_markdown_and_html_targets` returns no target for this form. Consequently, the autonomous entry or compact contract can acquire a real local prompt dependency that is neither rejected by `check_autonomous_prompt_surface` nor included in the 8,192-byte closure. The added reference-style tests at `tests/test_delivery_contracts.py:200-257` cover only same-line definitions.

Required repair: either parse the allowed one-line continuation in reference definitions and add entry/contract negative fixtures, or fail closed whenever reference-definition syntax is present but cannot be resolved canonically.

## Verified repair coverage

- Inline Markdown links: resolved.
- Angle-bracket inline destinations: resolved.
- Full, collapsed, and shortcut reference links with same-line definitions: resolved.
- Raw HTML `href` links: resolved.
- Indirect local links from the compact contract: rejected for the covered forms.
- Scheme-qualified external links, protocol-relative links, and fragment-only links: excluded.
- Prompt budget remains enforced at 8,192 bytes; the current entry plus compact contract is 5,968 bytes.

## Validation evidence

- `python -m unittest tests.test_delivery_contracts -v` — exit 0, 21/21 tests passed.
- Focused parser probe confirmed the covered forms resolve, external/fragment targets are excluded, and the multiline reference definition returns no target.
