#!/bin/bash
# Print the task list of the sweep: one line "tokenizer normalize N data-file" per task.
# The settings that produce the most pairs (short n-grams) and the largest files come first.
# Run in the work directory, after convert_sft.py: bash make_tasks.sh > work/sweep_tasks.txt
set -euo pipefail
for pair in "char 20" "spm 8" "char 30" "spm 13" "char 50" "spm 20" "char 80" "spm 30" "char 120" "spm 50" "char 200" "spm 80"; do
  set -- $pair
  for norm in nfkc-lower-ws none; do
    for f in $(ls -S work/sft_jsonl/*/*.jsonl.gz); do echo "$1 $norm $2 $f"; done
  done
done
