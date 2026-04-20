---
name: irodori-voice-drama-pipeline
description: Create playable voice-drama scripts and generated audio from Japanese novel manuscript markdown plus character or narration sample voices, using Irodori-TTS for reference-audio cloning on port 7860 and optional VoiceDesign fallback on port 7861. Use when Codex needs to adapt prose into spoken segments, annotate delivery with Irodori emoji controls, split long lines for DiT stability, batch-generate per-line audio, and export both isolated clips and a combined work.
---

# Irodori Voice Drama Pipeline

Use this skill to turn manuscript prose and sample voices into a voice-drama production package.

Keep the pipeline centered on four outputs:

1. A casted production YAML
2. Short, TTS-safe spoken chunks with emoji-aware `tts_text`
3. Per-segment generated `.wav` files
4. One combined `.wav` for the full scene

## Workflow

### 1. Gather inputs and cast the scene

Collect:

- the manuscript markdown
- character and narration sample audio
- any in-world playback or recording voices
- the intended narrator voice

Prefer user-provided sample audio first. If a needed sample is missing, generate a provisional one with the companion character pipeline and then feed that `.wav` back into this skill.

For this project:

- base Irodori-TTS cloning runs at `http://127.0.0.1:7860/`
- VoiceDesign fallback runs at `http://127.0.0.1:7861/`
- upstream repo: [Aratako/Irodori-TTS](https://github.com/Aratako/Irodori-TTS)
- `ルノフェン` and `ルノフェット` are the same character; use the `ルノフェット` sample

### 2. Adapt prose into a production YAML

Write one production file under:

```text
productions/<world>/<scene>.yaml
```

Use [references/production-schema.md](references/production-schema.md) as the schema.

Keep `text` human-readable and close to the source. Add `tts_text` only when you need:

- emoji annotations
- easier readings than the original prose
- lighter punctuation for spoken delivery
- performance tweaks for breath, crying, laughter, or playback texture
- reading stabilization for ambiguous kanji by opening them into hiragana when needed

When a line feels too long or fragile, write `chunks` yourself instead of trusting auto-splitting.

### 3. Annotate for performance, not decoration

Read [references/emoji-annotations.md](references/emoji-annotations.md) before adding emoji controls.

Prefer restrained annotation. A good default is:

- fix reading first
- split second
- add emojis last

Treat reading stabilization as a standard part of adaptation. If a kanji has multiple likely readings, or tends to be misread by the model, prefer rewriting the spoken form in hiragana inside `tts_text` or `chunks` while keeping the original form in `text`.

Use narration to carry scene description and timing. Use dialogue for intent and character beats. Use separate cast entries for special sources like recorded audio, even when they come from the same character in-world.

### 4. Keep chunks short for DiT stability

Read [references/adaptation-guidelines.md](references/adaptation-guidelines.md) when adapting dense prose or emotional scenes.

Default chunking target:

- soft ceiling: about `60` Japanese characters
- hard ceiling: about `80`

Split earlier when a chunk includes:

- repeated emoji cues
- sobbing or gasps
- quotations inside quotations
- difficult kanji readings
- long explanatory narration

For reading stabilization:

- keep `text` close to the manuscript for humans
- make `tts_text` the pronunciation-safe layer for TTS
- open ambiguous or niche readings into hiragana before blaming the model
- prefer partial rewrites over flattening the entire line when only one phrase is risky

### 5. Validate before generation

Run:

```bash
python scripts/validate_production.py productions/<world>/<scene>.yaml
```

Do this whenever you create or edit a production YAML.

### 6. Generate audio and combine it

Run:

```bash
python scripts/generate_voice_drama.py productions/<world>/<scene>.yaml
```

When you want automatic hallucination checks, enable lightweight ASR verification with `faster-whisper`:

```bash
python scripts/generate_voice_drama.py productions/<world>/<scene>.yaml --asr-check --asr-model tiny
```

The generator will:

- resolve cast aliases
- split long `tts_text` automatically when `chunks` are absent
- call the appropriate Irodori server per cast member
- optionally transcribe generated clips with lightweight ASR and retry failed segments
- allow `asr_skip: true` on segments where crying or broken speech makes ASR unreliable
- write per-segment `.wav` files under `generated_voice_drama/<timestamp>/.../segments/`
- export a combined full-scene `.wav`
- write `manifest.jsonl` and `manifest.csv`
- print unresolved ASR failures and also save them to `unresolved_segments.csv` / `unresolved_segments.txt`

If unresolved clips remain after retries, prefer this recovery flow:

1. open `unresolved_segments.csv` or `unresolved_segments.txt`
2. manually replace the corresponding `segments/<speaker>/*.wav`
3. run `python scripts/recombine_voice_drama.py generated_voice_drama/<timestamp>/<group>/manifest.csv`

## Project layout

Prefer this structure:

```text
manuscripts/<world>/<chapter>/*.md
productions/<world>/*.yaml
generated_voice_drama/<timestamp>/<group>/
references/
scripts/
```

If the user already stores manuscripts elsewhere, keep the manuscript where it is and reference that path from the production YAML.
Do not assume bundled sample voices exist in this repo; user-provided sample audio is the default, and actual sample files may be ignored from version control.

## Example

This repo includes a working example for `42.md`:

```text
manuscripts/chaimsphere/chapter4/42.md
productions/chaimsphere/chapter4_42.yaml
```

Validate and generate with:

```bash
python scripts/validate_production.py productions/chaimsphere/chapter4_42.yaml
python scripts/generate_voice_drama.py productions/chaimsphere/chapter4_42.yaml
```

## Resources

- [references/production-schema.md](references/production-schema.md): production YAML shape and field rules
- [references/emoji-annotations.md](references/emoji-annotations.md): concise emoji control cheat sheet with source links
- [references/adaptation-guidelines.md](references/adaptation-guidelines.md): prose-to-drama adaptation and chunking rules
- [scripts/validate_production.py](scripts/validate_production.py): schema validator
- [scripts/generate_voice_drama.py](scripts/generate_voice_drama.py): audio generation and full-scene assembly




