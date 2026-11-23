"""Convert one parquet file of llm-jp/llm-jp-4.1-thinking-sft-data to the input format of decontam-stats.

Output line: {"id": ID, "messages": [{"role": ..., "content": ..., "reasoning": ...}, ...]}
- user, tool: the text items, joined with a newline.
- assistant: the analysis channel becomes "reasoning", other channels (final, commentary) "content".
- developer: the "instructions" text only (the tool schemas are not matched).
- system: not matched (it holds only metadata: model identity, knowledge cutoff, date, effort).
Usage: convert_sft.py IN.parquet OUT.jsonl.gz
"""
import gzip, json, os, sys
import pyarrow.parquet as pq


def texts(content):
    if isinstance(content, str):
        return [content]
    out = []
    for item in content:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def convert(raw):
    messages = []
    for m in json.loads(raw):
        role, content = m["role"], m["content"]
        if role == "system":
            continue
        if role == "developer":
            parts = [c["instructions"] for c in content if isinstance(c, dict) and isinstance(c.get("instructions"), str)]
            if parts:
                messages.append({"role": "developer", "content": "\n".join(parts)})
            continue
        text = "\n".join(texts(content))
        if role == "assistant" and m.get("channel") == "analysis":
            messages.append({"role": "assistant", "content": "", "reasoning": text})
        else:
            messages.append({"role": role, "content": text})
    return messages


def main():
    src, dst = sys.argv[1], sys.argv[2]
    assert not os.path.exists(dst), dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    n = 0
    with gzip.open(dst + ".tmp", "wt", encoding="utf-8") as out:
        for batch in pq.ParquetFile(src).iter_batches(batch_size=2000, columns=["ID", "messages"]):
            for rid, raw in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist()):
                out.write(json.dumps({"id": rid, "messages": convert(raw)}, ensure_ascii=False) + "\n")
                n += 1
    os.replace(dst + ".tmp", dst)
    print(f"{src}\t{n}", flush=True)


main()
