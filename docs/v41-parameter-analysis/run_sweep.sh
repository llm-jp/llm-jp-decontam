#!/bin/bash
# Run decontam-stats for every task of a task list (make_tasks.sh) and keep only a summary per task.
# One task = (tokenizer, normalize, N, data file); --ref is work/ref/all.jsonl.gz.  The TSV of decontam-stats is
# written to a named pipe and read by aggregate.py, so the full TSV is never stored.
#   output: work/out/<tokenizer>_<normalize>_n<N>/<subset>__<file>.{summary.json,strong.tsv.gz,log,time}
# Finished tasks are skipped, so the script can be run again after an interruption (remove the *.lock
# directories of the interrupted tasks first).
# Usage (in the work directory):
#   STATS=<path to decontam-stats> SPM=<path to the SentencePiece .model> PY=<python with pyarrow> \
#     bash run_sweep.sh work/sweep_tasks.txt <number of parallel processes>
set -uo pipefail
TASKS=$1
PAR=$2
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
export STATS SPM PY SCRIPT_DIR OUT=work/out OMP_NUM_THREADS=1
mkdir -p "$OUT"
run_one() {
  local tok=$1 norm=$2 n=$3 f=$4 name d fifo t0 extra=()
  name=$(echo "${f#work/sft_jsonl/}" | sed 's|/|__|; s|\.jsonl\.gz$||'); d="$OUT/${tok}_${norm}_n${n}"
  mkdir -p "$d"
  [ -e "$d/$name.summary.json" ] && return 0
  mkdir "$d/$name.lock" 2>/dev/null || return 0
  [ "$tok" = spm ] && extra=(--tokenizer-model "$SPM")
  fifo="$d/$name.pipe"; t0=$(date +%s)
  rm -f "$fifo" "$fifo.tmp" "$d/$name.strong.tsv.gz"; mkfifo "$fifo.tmp"
  # decontam-stats writes to "<--output>.tmp" (here the named pipe) and renames it to --output when it succeeds
  "$PY" -I "$SCRIPT_DIR/aggregate.py" "$fifo.tmp" "$d/$name.summary.json.part" "$d/$name.strong.tsv.gz" & local ap=$!
  "$STATS" --data "$f" --ref work/ref/all.jsonl.gz --output "$fifo" --ngram-size "$n" --normalize "$norm" \
    --tokenizer "$tok" "${extra[@]}" 2> "$d/$name.log"; local rc=$?
  if [ $rc != 0 ]; then kill $ap 2>/dev/null; rm -f "$fifo" "$fifo.tmp" "$d/$name.summary.json.part"; rm -rf "$d/$name.lock"; echo "FAILED $d/$name rc=$rc"; return 1; fi
  wait $ap || { rm -f "$fifo" "$d/$name.summary.json.part"; rm -rf "$d/$name.lock"; echo "FAILED aggregate $d/$name"; return 1; }
  rm -f "$fifo"
  echo "$(( $(date +%s) - t0 ))" > "$d/$name.time"
  mv "$d/$name.summary.json.part" "$d/$name.summary.json"
  rm -rf "$d/$name.lock"
}
export -f run_one
xargs -P "$PAR" -L 1 bash -c 'run_one "$@"' _ < "$TASKS"
