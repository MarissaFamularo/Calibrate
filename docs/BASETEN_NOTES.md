# Baseten / Muse Spark Open: integration notes

Source: Baseten docs, fetched Oct 28, 2026. Coding agents: treat this file as the authority for model calls.

## Connection
- Base URL: `https://inference.baseten.co/v1` (OpenAI-compatible; use the `openai` SDK)
- Auth: `BASETEN_API_KEY` from `.env` (gitignored). Never hard-code or log the key.
- **Model ID: `meta-models/muse-spark-open-1026`** — the hackathon key works ONLY with this ID. Docs show `meta-models/muse-spark-open`; do not use it.

## Chat Completions (relevant params)
- `response_format`: `{"type":"json_schema","json_schema":{"name":...,"schema":{...},"strict":true}}` — use for every call whose output the code parses (assistant, verifier, educator).
- `reasoning_effort`: none | minimal | low | medium | high | xhigh | max. Muse Spark Open always reasons.
- Reasoning text is NOT returned as a field; only `usage.completion_tokens_details.reasoning_tokens`.
- `max_tokens` default 4096. Unverified: whether reasoning tokens count against it. Always check `finish_reason`; `length` = truncated → retry with higher `max_tokens` or lower `reasoning_effort`.
- `temperature`, `seed` available (use a fixed seed for reproducible demo runs).
- Errors: 400 bad params, 401 bad key, 429 rate limit (retry with backoff), 500 server.
- Rate-limit headers: `x-ratelimit-remaining-requests`, `x-ratelimit-remaining-tokens`.

## Vision (Muse Spark Open)
- Content part `{"type":"image_url","image_url":{"url":..., "detail":"auto"}}`
- JPEG/PNG/WebP/GIF(first frame)/BMP/TIFF; max 8 images, 10 MB each via URL; base64 data URLs allowed (count toward 100 MiB body).
- URLs must be public HTTPS reachable by Baseten (no localhost). For local dev, use base64.
- Video: up to 2, MP4/MOV/MKV/WebM, ≤300 s, 96 frames sampled.

## Audio (Muse Spark Open)
- Content part `{"type":"audio_url","audio_url":{"url":...}}` alongside a text part.
- WAV/MP3/FLAC/OGG/M4A; 8–48 kHz; ≤4 files, ≤5 min, ≤25 MB each.
- Billed as input tokens. Base64 data URLs work (count toward body limit).
- Combined media cap 200 MB per request.

## Links
- Quickstart: https://docs.baseten.co/quickstart.md
- Chat Completions: https://docs.baseten.co/reference/inference-api/chat-completions.md
- Vision: https://docs.baseten.co/inference/model-apis/vision.md
- Audio: https://docs.baseten.co/inference/model-apis/audio
- Model APIs overview (structured outputs, tools): https://docs.baseten.co/inference/model-apis/overview.md
