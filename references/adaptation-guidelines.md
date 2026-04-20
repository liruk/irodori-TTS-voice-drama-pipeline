# Adaptation Guidelines

Turn prose into a playable voice-drama script, not a literal line-by-line reading.

## Priorities

1. Preserve emotional beats and information flow.
2. Prefer spoken-natural phrasing over exact prose when narration would sound stiff.
3. Keep chunks short enough for stable DiT pronunciation.
4. Use narration to bridge scene description, motion, and point-of-view shifts.

## Recommended workflow

1. Read the manuscript section once for plot and once for sound.
2. Build the cast list from explicit speakers, narration, and any in-world playback voice.
3. Draft `segments` in chronological order.
4. Convert dense exposition into narration lines that can be spoken in one breath.
5. Add `tts_text` only when you need reading fixes, emoji cues, or a cleaner spoken form.
6. Split any long or emotionally complex line into `chunks`.
7. Generate a small subset first, listen, then tighten wording before full batch synthesis.

## Reading Stabilization

- Treat reading stabilization as part of script adaptation, not as a last-resort patch.
- Keep manuscript fidelity in `text`, but use `tts_text` to protect pronunciation.
- Open ambiguous, literary, or uncommon kanji into hiragana when the intended reading is not guaranteed.
- Prefer targeted rewrites such as `せいじゃく`, `どうこく`, `かいもく けんとう` over replacing an entire line.
- If a proper noun already has a stable katakana or kana reading in the project, reuse that exact form.

## Chunking rules

- Split on sentence boundaries first.
- Split on `、` or rhetorical pivots when a sentence stays long.
- Separate breaths, cries, and quoted playback into their own chunk whenever possible.
- Avoid putting stage direction and spoken line in the same chunk.
- Treat `60` Japanese characters as a soft ceiling and `80` as a hard ceiling.

## Casting rules

- Reuse the same reference voice for multiple roles only when that is the artistic intent.
- For this project, `ルノフェン` and `ルノフェット` are the same character; use the `ルノフェット` sample for both.
- The user-provided recording sample `小凪葉らん` should be treated as an in-world recorded voice, not narration.
