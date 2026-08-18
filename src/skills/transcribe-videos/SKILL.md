---
name: transcribe-videos
description: Download, inspect, transcribe, and summarize videos from YouTube, direct media URLs, local files, and user-authorized logged-in course pages. Use when the user asks Codex to download or watch a video, create a summary or transcript, process a YouTube URL, avoid retaining media after transcription, or batch every lesson exposed by a course sidebar.
---

# Transcribe Videos

Turn one video or a course collection into durable Markdown while keeping authentication and temporary media contained.

## Establish the contract

1. Identify the source, output directory, requested language, scope, and media-retention requirement from the request and prior context.
2. For a download-only request, retain the requested media and stop after validating it; do not generate text the user did not ask for.
3. Treat "summary/transcript only" as temporary-media mode. Keep a downloaded video only when the user explicitly asks to retain it.
4. For a course or sidebar request, enumerate phases and lessons before processing. Record the expected lesson count and page URLs so completion can be verified.
5. Tell the user before batch navigation if opening lessons may mark them as viewed.

## Respect access boundaries

- Process public content, user-provided files, or content available through a logged-in session the user has authorized.
- Use the user's active browser session for logged-in pages. Do not export passwords, cookies, bearer tokens, or browser profiles.
- Treat signed player and HLS URLs as secrets: keep them only in a temporary manifest, never place them in Markdown, Git, logs, or the final directory.
- Do not bypass DRM, a paywall, access controls, or a site restriction. Stop and explain when the media is encrypted or inaccessible through the authorized session.
- Use `--cookies-from-browser` only after explicit user approval; it can expose browser-wide authentication material.

## Select the source workflow

- **YouTube or another public supported URL:** use `yt-dlp` for metadata and audio/video acquisition.
- **Local media:** pass the file directly to the bundled transcription helper.
- **Logged-in course:** use browser control to enumerate lessons and inspect the authorized player. Extract a non-DRM direct media or HLS URL only inside the active session, then process it as ephemeral input.
- **Multiple lessons:** create one temporary manifest and transcribe the batch in a single model session.

Read [source-workflows.md](./references/source-workflows.md) for commands and the batch-manifest shape.

## Prepare tooling and temporary state

1. Check `yt-dlp --version` and `python --version`. Check `ffmpeg -version` when a retained download needs separate audio and video merged.
2. Use an isolated Python environment containing `faster-whisper`. Do not install packages into a repository environment without repository permission.
3. Create a uniquely named workspace under the operating system's temporary directory. Store manifests, raw JSON, and any transient media there.
4. Resolve the directory containing this `SKILL.md` and prefer its bundled helper for repeatability. The examples below assume that directory is the current working directory:

```powershell
python .\scripts\transcribe_media.py --input "<video-url-or-file>" --output ".\raw.json" --title "<title>" --slug "<slug>" --language <language-code>
```

For a direct authorized media stream, add `--direct-media`. For a course manifest, use:

```powershell
python .\scripts\transcribe_media.py --manifest ".\manifest.json" --output-dir ".\transcripts" --language <language-code>
```

Use `small`, CPU, and `int8` as reliable defaults. Increase model size or use a GPU only when accuracy requirements and available hardware justify the added cost.

## Produce the final documents

Read [output-contract.md](./references/output-contract.md) before writing the final files.

1. Review the automatic transcript and correct obvious recognition errors using the lesson title, visible page text, and surrounding context. Never invent unclear content.
2. Create one slugged folder per video or lesson.
3. Write `summary.md` and `transcript.md` in the requested language. Default to the conversation language when the user did not specify one.
4. Make the transcript comprehensive, timestamped, and non-literal for third-party copyrighted material. Preserve the sequence, examples, caveats, and promotional sections without reproducing the source word for word.
5. Attribute health, legal, financial, or other individualized claims to the speaker and add an appropriate professional-advice caveat.
6. Link the two Markdown files to each other and include the public or authenticated lesson-page URL, never the signed media URL.

## Validate and clean up

1. Compare completed folders with the pre-recorded lesson count and manifest.
2. In text-only mode, verify every lesson folder contains exactly `summary.md` and `transcript.md`, both non-empty, with reciprocal links.
3. Verify the final tree contains no video, audio, subtitle, cookie, manifest, model-cache, or raw-transcript file unless the user explicitly requested it.
4. Resolve the exact temporary path and confirm it is a child of the operating system's temporary directory before recursively deleting it.
5. Recheck the final counts after cleanup and report lesson folders, Markdown files, retained media, and whether temporary state is absent.

## Failure handling

- Refresh an expired signed URL from the authorized browser session; do not persist it for reuse.
- If only one lesson fails, preserve completed text outputs, identify the exact lesson, reacquire its authorized source, and retry it without retranscribing the whole course.
- If automatic speech recognition is uncertain, mark the passage as unclear or summarize conservatively.
- If `yt-dlp` reports a site or format change, verify against its official documentation and update the tool before inventing extractor workarounds.
