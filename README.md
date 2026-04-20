# irodori-voice-drama-pipeline

小説本文とキャラクター/ナレーションのサンプル音声から、Irodori-TTS 用のボイスドラマ台本を作り、単体音声と結合音声を生成するためのリポジトリです。

このリポジトリは次の流れを前提にしています。

1. 小説本文を読む
2. ボイスドラマ向けに台本化する
3. DiT で破綻しにくい長さにセリフを分割する
4. Irodori-TTS で各セグメントを生成する
5. 必要に応じて ASR で逸脱を検査する
6. 作品として結合した wav を出力する

## 対応サーバー

- 参照音声クローン: `http://127.0.0.1:7860/`
- VoiceDesign fallback: `http://127.0.0.1:7861/`

## ディレクトリ構成

```text
agents/
manuscripts/
productions/
references/
scripts/
generated_voice_drama/
SKILL.md
README.md
```

`manuscripts/` と `productions/` は入力置き場です。`.gitkeep` だけを追跡し、実データは `.gitignore` で除外しています。

## 主要ファイル

- `SKILL.md`
  - Codex 用 Skill 本体
- `scripts/validate_production.py`
  - production YAML の検証
- `scripts/generate_voice_drama.py`
  - セグメント生成、ASR 検査、結合 wav 出力
- `references/production-schema.md`
  - production YAML のスキーマ
- `references/adaptation-guidelines.md`
  - 台本化、読み安定化、`asr_skip` の指針
- `references/emoji-annotations.md`
  - Irodori-TTS の絵文字注釈メモ

## production YAML の考え方

1 ファイルで 1 シーンを表します。

主な要素:

- `project`
  - タイトル、原稿パス、出力グループ、分割設定
- `cast`
  - 話者定義
  - `mode: clone` は参照音声を使う
  - `mode: voicedesign` は style prompt を使う
- `segments`
  - 実際の読み上げ単位
  - `text` は人が読むための本文寄り表記
  - `tts_text` は TTS 安定化用の表記
  - `chunks` は手動分割
  - `asr_skip: true` は ASR 検査を外したいセグメント用

## 読み安定化

読みが揺れそうな漢字は、`text` では原稿寄りに残し、`tts_text` や `chunks` 側でひらがなに開きます。

例:

- `静寂` -> `せいじゃく`
- `慟哭` -> `どうこく`
- `皆目見当` -> `かいもく けんとう`

これは単なる読み替えではなく、発話安定化のための正式な工程として扱います。

## ASR 検査

軽量の `faster-whisper` を使って、生成した音声が `tts_text` から大きく逸脱していないかを確認できます。

おすすめ設定:

```bash
python scripts/generate_voice_drama.py productions/chaimsphere/chapter4_42.yaml --asr-check --asr-model base --asr-device cpu --asr-compute-type int8 --asr-min-similarity 0.65
```

補足:

- `tiny` より `base` の方が日本語の実運用では安定しやすいです
- 泣き声、崩れた発話、非言語的なうめきは `asr_skip: true` を付けるのが無難です
- 判定結果は `manifest.jsonl` / `manifest.csv` に保存されます

## 生成方法

### 1. production を検証する

```bash
python scripts/validate_production.py productions/chaimsphere/chapter4_42.yaml
```

### 2. 通常生成

```bash
python scripts/generate_voice_drama.py productions/chaimsphere/chapter4_42.yaml
```

### 3. ASR 検査つき生成

```bash
python scripts/generate_voice_drama.py productions/chaimsphere/chapter4_42.yaml --asr-check --asr-model base --asr-device cpu --asr-compute-type int8 --asr-min-similarity 0.65
```

## 出力

生成結果は `generated_voice_drama/<timestamp>/<group>/` に保存されます。

含まれるもの:

- `segments/<speaker>/*.wav`
  - セグメントごとの単体音声
- `*_full.wav`
  - 結合済み作品音声
- `manifest.jsonl`
- `manifest.csv`

ASR 検査つき生成では、最後に「まだ通らなかったセグメント一覧」も標準出力へ表示されます。
同時に `unresolved_segments.csv` と `unresolved_segments.txt` も出力されるので、手修正対象をそのまま確認できます。

## 手動差し替え後の再結合

ASR で取り切れなかった行は、ユーザが `segments/<speaker>/*.wav` を手で差し替えてから再結合できます。

```bash
python scripts/recombine_voice_drama.py generated_voice_drama/<timestamp>/<group>/manifest.csv
```

任意の出力先を指定することもできます。

```bash
python scripts/recombine_voice_drama.py generated_voice_drama/<timestamp>/<group>/manifest.csv --output-wav generated_voice_drama/<timestamp>/<group>/manual_fix_full.wav
```

手順としては次の流れを想定しています。

1. 生成後に `unresolved_segments.csv` か `unresolved_segments.txt` を見る
2. 該当する `segments/<speaker>/*.wav` をユーザが手で差し替える
3. `recombine_voice_drama.py` で結合し直す

## 既知の実務上の知見

- 短い文でもハルシネーションで余計な語が足されることがあります
- そのため、短文でも `tts_text` を閉じた表現にする価値があります
- hallucination 対策としては、文面調整に加えて ASR 検査 + 再試行が有効です
- ただし ASR は泣き声や崩れた発話に弱いので、その種別は `asr_skip: true` を使います

## サンプル

このリポジトリには `望郷のカイムスフィア` chapter4 の `42.md` を元にしたサンプル production が入っています。

- `manuscripts/chaimsphere/chapter4/42.md`
- `productions/chaimsphere/chapter4_42.yaml`
