# Voice Drama Production Schema

Use one YAML file per production. Keep it human-editable first, machine-runnable second.

## Top-level shape

```yaml
project:
  title: 作品名
  manuscript: manuscripts/world/chapter/file.md
  output_group: optional/subdir
  default_pause_ms: 500
  chunk_pause_ms: 150
  max_chars_per_chunk: 70

cast:
  - id: arm
    name: アルム
    aliases: [アルム]
    mode: clone
    server_url: http://127.0.0.1:7860/
    ref_wav: C:/path/to/ref.wav
  - id: narration
    name: ナレーション
    aliases: [ナレーション]
    mode: clone
    server_url: http://127.0.0.1:7860/
    ref_wav: C:/path/to/ref.wav
  - id: temp-npc
    name: 仮キャラ
    aliases: [仮キャラ]
    mode: voicedesign
    server_url: http://127.0.0.1:7861/
    caption: 中性的で高め、静かで知的な少年の声で

segments:
  - id: s001
    speaker: narration
    text: 物語が、終わる。
    tts_text: 物語が、終わる。⏸️
    pause_ms: 700
  - id: s002
    speaker: arm
    text: 全部終わった？
    tts_text: 全部終わった？
  - id: s003
    speaker: narration
    text: 長い説明文
    chunks:
      - ここで一度切る。
      - さらに短く切って読む。
```

## Rules

- `project.manuscript` is provenance only. The generator does not parse it.
- `mode: clone` requires `ref_wav` and normally targets the base server on port `7860`.
- `mode: voicedesign` requires `caption` and normally targets the VoiceDesign server on port `7861`.
- `speaker` may use either a cast `id` or an alias listed in `aliases`.
- Prefer `tts_text` when you need emoji annotations, furigana-like rewrites, or punctuation adjustments.
- Use `chunks` when the sentence is fragile or clearly too long for DiT inference. If omitted, the generator will split automatically.
- Keep one chunk roughly under `50` to `80` Japanese characters. Push shorter for emotionally unstable or annotation-heavy lines.
- Put performance pauses in `pause_ms`, not inside giant runs of punctuation.

## Casting guidance

- Duplicate a cast entry when the same voice should play multiple functions, such as both `ルノフェン` and `ナレーション`.
- Keep `aliases` generous so manuscript names and stage names both resolve.
- If the user lacks sample audio, generate provisional samples first with the companion character pipeline and then reference those `.wav` files here.
