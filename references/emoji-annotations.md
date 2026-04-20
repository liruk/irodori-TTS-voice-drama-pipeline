# Emoji Annotation Notes

Use emoji control sparingly and only when it clearly helps performance. The reference list comes from the official Irodori-TTS model card and `EMOJI_ANNOTATIONS.md`:

- [Irodori-TTS GitHub](https://github.com/Aratako/Irodori-TTS)
- [Irodori-TTS-500M-v2 model card](https://huggingface.co/Aratako/Irodori-TTS-500M-v2)
- [EMOJI_ANNOTATIONS.md](https://huggingface.co/Aratako/Irodori-TTS-500M-v2-VoiceDesign/blame/main/EMOJI_ANNOTATIONS.md)

## Useful drama annotations

- `⏸️`: short pause or held silence
- `🤭`: chuckle or suppressed laugh
- `😏`: teasing or sweetly provocative tone
- `🥺`: trembling, unsure, or about to cry
- `😮`: audible intake of breath
- `🌬️`: rougher breathing
- `😭`: sobbing or crying
- `🫶`: gentle warmth
- `😟`: worried tone
- `🙏`: pleading tone
- `🐢`: intentionally slow delivery
- `⏩`: rapid-fire delivery
- `📞`: sounds like playback through a device or call

## Heuristics

- Add at most one or two emoji cues per short chunk unless the effect itself is the point.
- Prefer rewriting orthography before adding emojis. Example: break a line, simplify kanji, remove nested quotes.
- Place emotional emoji near the phrase it should affect, not only at the start of a long line.
- For cries or breakdowns, split the line first, then add `😭` or `🥺` to the specific crying chunk.
- For recorded or device-like playback, `📞` can help, but a separate role and clean shorter chunking matter more.
