#!/usr/bin/env bash
# Nemotron 3 Diarization CPU benchmark for Caption With Intention v2.
# Usage: ./run_bench.sh [model-name] [threads]
#   model-name: bf16 (default) | q8
#   threads:    CPU threads (default 4)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="${1:-bf16}"
THREADS="${2:-4}"

if [[ "$MODEL" == "q8" ]]; then
  WEIGHTS="$DIR/models/nemotron-3-diarization-q8_0.gguf"
else
  WEIGHTS="$DIR/models/nemotron-3-diarization-bf16.gguf"
fi

AUDIO="$DIR/bench/test10min.wav"
CLI="$DIR/audio.cpp/build/bin/audiocpp_cli"

DURATION=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$AUDIO")
echo "model=$MODEL threads=$THREADS audio=${DURATION}s"

# Warmup run (loads model + warms caches), not counted.
echo "--- warmup ---"
"$CLI" --task diar --family nemotron_3_diar \
  --model "$WEIGHTS" --backend cpu --threads "$THREADS" \
  --audio "$AUDIO" --turns-out "$DIR/bench/warmup.json" --log 2>&1 | tail -3

# Timed run
echo "--- timed run ---"
START=$(date +%s.%N)
"$CLI" --task diar --family nemotron_3_diar \
  --model "$WEIGHTS" --backend cpu --threads "$THREADS" \
  --audio "$AUDIO" --turns-out "$DIR/bench/turns_${MODEL}.json" --log 2>&1 | grep -E "elapsed|runtime|rtf|RTF|took|time" | tail -5
END=$(date +%s.%N)

WALL=$(awk -v a="$END" -v b="$START" 'BEGIN{printf "%.3f", a-b}')
RTF=$(awk -v d="$DURATION" -v w="$WALL" 'BEGIN{printf "%.4f", d/w}')
echo "wall=${WALL}s duration=${DURATION}s RTF=${RTF}x (audio seconds per wall second)"

echo "--- turns summary ---"
python3 - "$DIR/bench/turns_${MODEL}.json" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
turns = data if isinstance(data, list) else data.get("speaker_turns", data.get("turns", []))
print(f"turns={len(turns)}")
speakers = sorted({t.get("speaker") or t.get("speaker_id") or t.get("label") for t in turns if isinstance(t, dict)})
print(f"speakers={speakers}")
for t in turns[:15]:
    print(t)
PY
