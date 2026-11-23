"""Summarize one decontam-stats TSV (read from a file or named pipe) without keeping it.

Per --data record, over all its pairs: the maximum --ref-side coverage, the maximum --data-side coverage
(both as integer percent, floor), and whether any pair has a short-text match.  Written to SUMMARY (json):
  pairs, records: number of TSV rows and of distinct data_line
  hist: {"<ref%>|<data%>|<short>": records}             (all benchmarks)
  bench_hist: {benchmark: {"<ref%>|<data%>|<short>": records}}   (maxima over that benchmark's pairs only)
  ref_records: {ref_id: number of data records paired with it}
  ref_records50: {ref_id: number of data records whose pair with it has --ref-side coverage >= 0.5}
Rows with --ref-side or --data-side coverage >= 0.5 or a short-text match are copied to STRONG (tsv.gz).
Usage: aggregate.py TSV SUMMARY STRONG
"""
import collections, gzip, json, sys

src, summary_path, strong_path = sys.argv[1:4]
HEADER = "data_line\tdata_id\tref_line\tref_id\tmatched_ngrams\tref_ngrams\tdata_ngrams\tmatched_short_texts\n"


def pct(m, d):
    return min(100, m * 100 // d) if d else 0


pairs = 0
rec = {}                                   # data_line -> [ref%, data%, short]
brec = collections.defaultdict(dict)       # bench -> data_line -> [ref%, data%, short]
ref_records = collections.Counter()
ref_records50 = collections.Counter()
with open(src, encoding="utf-8") as f, gzip.open(strong_path, "wt", encoding="utf-8") as strong:
    assert f.readline() == HEADER
    strong.write(HEADER)
    for line in f:
        c = line.rstrip("\n").split("\t")
        dl, ref_id = int(c[0]), c[3]
        m, rn, dn, s = int(c[4]), int(c[5]), int(c[6]), int(c[7]) > 0
        r, d = pct(m, rn), pct(m, dn)
        pairs += 1
        for table in (rec, brec[ref_id.split(":", 1)[0]]):
            v = table.get(dl)
            if v is None:
                table[dl] = [r, d, s]
            else:
                v[0] = max(v[0], r); v[1] = max(v[1], d); v[2] = v[2] or s
        ref_records[ref_id] += 1
        if r >= 50:
            ref_records50[ref_id] += 1
        if r >= 50 or d >= 50 or s:
            strong.write(line)


def hist(table):
    return dict(collections.Counter(f"{r}|{d}|{int(s)}" for r, d, s in table.values()))


with open(summary_path, "w") as out:
    json.dump({"pairs": pairs, "records": len(rec), "hist": hist(rec),
               "bench_hist": {b: hist(t) for b, t in sorted(brec.items())},
               "ref_records": dict(ref_records), "ref_records50": dict(ref_records50)}, out)
