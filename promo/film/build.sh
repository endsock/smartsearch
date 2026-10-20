#!/usr/bin/env bash
# Builds out/film/smart-search-promo.mp4: cue list -> synthesized mix -> limiter + two-pass loudnorm -> frames -> mp4.
#   bash film/build.sh            full 1920x1080 @ 60 fps
#   bash film/build.sh draft      960x540 @ 30 fps
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=out/film
mkdir -p "$OUT"

node tools/events.mjs film/timeline.js "$OUT/events.json"
python3 film/sound.py "$OUT/events.json" "$OUT/mix_raw.wav"

# Peak-limit first so loudnorm can stay linear, then normalise to -14 LUFS / -1 dBTP in two passes.
ffmpeg -v error -y -i "$OUT/mix_raw.wav" -af "alimiter=limit=0.33:attack=3:release=90:level=false" "$OUT/mix_lim.wav"
MEASURE=$(ffmpeg -hide_banner -i "$OUT/mix_lim.wav" -af loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
read -r I TP LRA TH OFF < <(python3 -c 'import json,sys; m=json.loads(sys.argv[1]); print(m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"], m["target_offset"])' "$MEASURE")
ffmpeg -v error -y -i "$OUT/mix_lim.wav" -af "loudnorm=I=-14:TP=-1.0:LRA=11:measured_I=$I:measured_TP=$TP:measured_LRA=$LRA:measured_thresh=$TH:offset=$OFF:linear=true" -ar 48000 "$OUT/mix.wav"

if [ "${1:-}" = draft ]; then
  node tools/render.mjs film/index.html "$OUT/draft.mp4" --size 960x540 --fps 30 --duration 45 --audio "$OUT/mix.wav" --crf 24
else
  node tools/render.mjs film/index.html "$OUT/smart-search-promo.mp4" --size 1920x1080 --fps 60 --duration 45 --audio "$OUT/mix.wav" --crf 18
fi
