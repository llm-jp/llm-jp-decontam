"""Merge the per-file summaries of every setting (OUT/<tok>_<norm>_n<N>/) and print tables (Markdown).
Usage: analyze.py OUT
The first table lists every setting; the other tables use only the settings whose 126 files are all finished."""
import collections, glob, json, os, re, sys

OUT = sys.argv[1]
NFILES = 126
REF = [0.2, 0.5, 0.8, 1.0]
DATA = [0.2, 0.5, 0.8]


def load(setting_dir):
    tot = {"pairs": 0, "records": 0, "hist": collections.Counter(), "bench": collections.defaultdict(collections.Counter),
           "ref_records": collections.Counter(), "ref_records50": collections.Counter(),
           "subset": collections.defaultdict(collections.Counter), "data_records": 0, "seconds": 0, "files": 0}
    for p in sorted(glob.glob(setting_dir + "/*.summary.json")):
        j = json.load(open(p))
        name = os.path.basename(p)[:-len(".summary.json")]
        tot["files"] += 1
        tot["pairs"] += j["pairs"]; tot["records"] += j["records"]
        tot["hist"].update(j["hist"])
        tot["subset"][name.split("__")[0]].update(j["hist"])
        for b, h in j["bench_hist"].items():
            tot["bench"][b].update(h)
        tot["ref_records"].update(j["ref_records"]); tot["ref_records50"].update(j["ref_records50"])
        log = open(p[:-len(".summary.json")] + ".log").read()
        tot["data_records"] += int(re.search(r"data_records=(\d+)", log).group(1))
        tot["seconds"] += int(open(p[:-len(".summary.json")] + ".time").read())
    return tot


def count(hist, ref=None, data=None, short=False):
    """Records removed by: ref% >= ref, or data% >= data, or a short-text match (each criterion optional)."""
    n = 0
    for k, v in hist.items():
        r, d, s = (int(x) for x in k.split("|"))
        if (ref is not None and r >= ref * 100) or (data is not None and d >= data * 100) or (short and s):
            n += v
    return n


def setting_key(name):
    tok, norm, n = re.match(r"(char|spm)_(.+)_n(\d+)$", name).groups()
    return (tok, norm, int(n))


settings = sorted((setting_key(os.path.basename(d)), d) for d in glob.glob(OUT + "/*_n*"))
data = {k: load(d) for k, d in settings}
print("## 設定ごとの完了ファイル数と所要時間\n\n| 単位 | 正規化 | N | 完了ファイル | 学習レコード | 実行単位の経過時間の合計（時間） |\n|---|---|---|---|---|---|")
for k, t in data.items():
    print(f"| {k[0]} | {k[1]} | {k[2]} | {t['files']}/{NFILES} | {t['data_records']:,} | {t['seconds']/3600:.1f} |")
done = {k: t for k, t in data.items() if t["files"] == NFILES}

print("\n## 表 A：重なりのあるレコードと、条件ごとに取り除かれるレコード（全評価タスク）\n")
print("| 単位 | 正規化 | N | ペア | 重なりのあるレコード | " + " | ".join(f"ref≥{x}" for x in REF) + " | " + " | ".join(f"data≥{x}" for x in DATA) + " | short | ref≥0.5 または short |")
print("|" + "---|" * (5 + len(REF) + len(DATA) + 2))
for k, t in done.items():
    h = t["hist"]
    cells = [f"{count(h, ref=x):,}" for x in REF] + [f"{count(h, data=x):,}" for x in DATA]
    print(f"| {k[0]} | {k[1]} | {k[2]} | {t['pairs']:,} | {t['records']:,} | " + " | ".join(cells) + f" | {count(h, short=True):,} | {count(h, ref=0.5, short=True):,} |")

benches = sorted({b for t in done.values() for b in t["bench"]})
print("\n## 表 B：評価タスクごとの、ref≥0.5 で取り除かれるレコード（括弧内は、学習レコードと ref≥0.5 で重なる評価の問の数）\n")
print("| 評価タスク | " + " | ".join(f"{k[0]}/{k[1][:4]}/{k[2]}" for k in done) + " |")
print("|---|" + "---|" * len(done))
for b in benches:
    cells = []
    for k, t in done.items():
        items = sum(1 for r in t["ref_records50"] if r.startswith(b + ":"))
        cells.append(f"{count(t['bench'].get(b, {}), ref=0.5):,} ({items})")
    print(f"| {b} | " + " | ".join(cells) + " |")

print("\n## 表 C：学習データのサブセットごとの、ref≥0.5 または short で取り除かれるレコード\n")
subsets = sorted({s for t in done.values() for s in t["subset"]})
print("| サブセット | " + " | ".join(f"{k[0]}/{k[1][:4]}/{k[2]}" for k in done) + " |")
print("|---|" + "---|" * len(done))
for s in subsets:
    print(f"| {s} | " + " | ".join(f"{count(t['subset'].get(s, {}), ref=0.5, short=True):,}" for t in done.values()) + " |")

print("\n## 表 D：重なりのある学習レコードが最も多い評価の問（各設定の上位 5 件、問の ID：学習レコード数）\n")
for k, t in done.items():
    top = ", ".join(f"`{r}`：{n:,}" for r, n in t["ref_records"].most_common(5))
    print(f"- {k[0]}/{k[1]}/N={k[2]}：{top}")
