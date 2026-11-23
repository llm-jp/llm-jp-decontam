# パラメータと取り除かれるレコードの数の関係：LLM-jp-4.1 の公開 SFT データでの計測

このレポート（`docs/v41-parameter-analysis.md`）は、このリポジトリ（llm-jp-decontam）の `decontam-stats` の `--tokenizer`、`--normalize`、`--ngram-size` と、`decontam-filter` の条件を変えたときに、取り除かれる学習データのレコードの数がどう変わるかを計測した結果です。実際の規模のデータで、パラメータを選ぶための材料を示すことが目的で、推奨値は決めていません。

LLM-jp は、日本語の大規模言語モデルを開発・公開している研究開発の組織です。LLM-jp-4.1 は、LLM-jp が公開しているモデルの系列で、LLM-jp-4 の後継です。計測は 2026 年 11 月 23 日に行いました。データは次の 2 つです。

- 学習データ：LLM-jp-4.1 の thinking モデル用 SFT データのうち、公開されている部分
- 評価データ：LLM-jp-4.1 の評価に使われた、swallow-evaluation-instruct の評価タスク

取り除かれるレコードの数は、`decontam-filter` を実行して数えたのではなく、`decontam-stats` の出力の集計から、`decontam-filter` と同じ規則で計算しました。1 ファイル（`jaster_v1.4.1/reasoning_low-00000-of-00001.parquet`、263,624 レコード）の文字単位、N=50、`nfkc-lower-ws` の出力について、3 つの条件（`--min-ref-coverage 0.5 --short-texts`、`--min-data-coverage 0.5`、`--min-ref-coverage 0.2`）で `decontam-filter` を実際に実行し、取り除かれた数（12 件、5 件、18 件）が計算した数と一致することを確かめました。1 つ目の条件では、取り除かれたレコードの `id` の集合も一致しました。

この計測で分かるのは、条件ごとに取り除かれるレコードの数です。取り除かれたレコードが実際に評価データの問題を含むか（誤検出の割合）と、評価データの問題を含むのに取り除かれないレコード（検出漏れ）の数は測っていません。そのため、件数だけからパラメータの良し悪しは決められません。

この文書では、`decontam-filter` の条件の例として `--min-ref-coverage 0.5` を、N の例として文字単位の N=50 と spm の N=13 を使います。どれも計測した値の範囲の中ほどの値です。

## この文書の用語

用語は README と同じです。主な用語を次に示します。

- 「N」：`--ngram-size` の値です。
- 「文字単位」：`--tokenizer char`（Unicode のコードポイント 1 つを 1 トークンとする方法）です。文字単位では、N トークンは N 文字に当たります。
- 「spm」：`--tokenizer spm`（SentencePiece のモデルでトークンに分ける方法）です。
- 「`nfkc-lower-ws`」と「`none`」：`--normalize` の値です。`nfkc-lower-ws` は、NFKC 正規化、小文字への変換、空白文字（改行とタブを含む）の連続を半角スペース 1 つに置き換える処理を行います。`none` は正規化しません。
- 「問題」：評価データの 1 レコード（評価の 1 問）です。この計測では、1 問の問題文を 1 つの `content` にしたので、問題と照合対象の文字列は 1 対 1 です。
- 「ペア」：学習データの 1 レコードと評価データの 1 問の組です。共通の n-gram か全体一致があるペアが、`decontam-stats` の TSV に 1 行ずつ出ます。
- 「重なりのあるレコード」：TSV に 1 行以上ある学習データのレコードです。
- 「`--ref` 側の被覆率」：`matched_ngrams` ÷ `ref_ngrams` です。`--data` 側の被覆率は `matched_ngrams` ÷ `data_ngrams` です。`matched_ngrams` は共通の n-gram の種類数、`ref_ngrams` は問題の n-gram の種類数、`data_ngrams` は学習データのレコードの n-gram の種類数です（どれも出現回数ではなく種類数）。`data_ngrams` には、変換後のすべてのメッセージの `content` と `reasoning` が入り、変換で除いた部分（system のメッセージなど）は入りません。分母が 0 のペアは、被覆率の条件に合いません。
- 「全体一致」：N トークン未満の問題について、正規化してトークンに分けた結果が、学習データのレコードに含まれるいずれかのメッセージの `content` または `reasoning` を同じように処理した結果と、全体で等しいことです。一方が他方の一部であるだけの場合は含みません。TSV では `matched_short_texts` が 1 以上のペアに当たります。
- 「サブセット」：LLM-jp-4.1 の SFT データの区分です。公開データ `llm-jp/llm-jp-4.1-thinking-sft-data` では、最上位のディレクトリ（daring_anteater、flan など）に当たり、24 サブセットあります。
- 「設定」：`decontam-stats` の `--tokenizer`、`--ngram-size`、`--normalize` の値の組です。計測では 24 通りの設定を使いました。
- 「実行単位」：計測の実行の単位で、1 つの設定と 1 つの学習データのファイルの組み合わせです。

## 結論

数は、特に断らない限り `nfkc-lower-ws` の値です。24 通りの設定の一覧は「計測の方法」の節にあります。

- N が小さいと、重なりのあるレコードが大きく増えます。
  - 文字単位では、N=20 のとき約 383 万件（学習データの 78%）、N=50 のとき約 45 万件、N=80 のとき 1,966 件です。
  - 文字単位の N=50 では、2 つの問題（`mmluprox_ja:1239`、`mmluprox_en:1239`）が、それぞれ約 40 万件のレコードと重なります。この 2 つの問題は、ハイフンが 62 個続く区切り線を含みます。
  - `none` では、空白の連続（字下げ）による一致が別に起きます。ただし、重なりのあるレコードの数は、トークナイザーと N の 12 通りの組み合わせのすべてで、`nfkc-lower-ws` より少なくなります。
  - 重なりのあるレコードのうち、`--min-ref-coverage` の条件に合うものはわずかです。たとえば文字単位の N=20 で `--min-ref-coverage 0.5` を指定すると、約 383 万件のうち取り除かれるのは 1,285 件です。
- `--min-ref-coverage 0.5` で取り除かれるレコードは、N を大きくすると減ります。文字単位では N=20 で 1,285 件、N=200 で 392 件です。spm では N=8 で 918 件、N=80 で 176 件です。
- 取り除かれるレコードは、2 つのサブセット（daring_anteater と nemotron3_sft_chat_v3）に集中します。`--min-ref-coverage 0.5 --short-texts` で取り除かれるレコードのうち、この 2 つの割合は、24 通りのどの設定でも 86.6%（spm の N=8、`nfkc-lower-ws`）〜96.9%（文字単位の N=200、`nfkc-lower-ws`）です。確かめた例では、MMLU-ProX（英語）と MATH-500 の問題文が、daring_anteater の user メッセージにそのまま入っていました。
- 全体一致で取り除かれるレコードは、N を大きくすると増えます。文字単位の N=20 と spm の N=8 では、全体一致はありませんでした。ほかの設定では、全体一致はすべて MATH-500 の N トークン未満の問題によるものでした。
- `nfkc-lower-ws` で `--min-ref-coverage 0.5` を指定すると、`none` のときの件数に比べて、取り除かれるレコードの増加率は 2.9%（文字単位の N=20）〜18.9%（spm の N=80）です。

## 使ったデータ

### 学習データ（`--data`）

Hugging Face の [`llm-jp/llm-jp-4.1-thinking-sft-data`](https://huggingface.co/datasets/llm-jp/llm-jp-4.1-thinking-sft-data)（リビジョン `cb4210190af6a0000fd91cb5bb8361ad6d6ade01`）です。parquet 形式の 126 ファイルで、4,888,831 レコードあります。認証なしで取得できます。LLM-jp-4.1 の学習に使われたデータのうち、ライセンスの都合で再配布されていないサブセット（ac_002、ichikara など）は含まれていません。

このデータでは、各メッセージの `content` が、種類（text など）を持つ要素のリストになっています。assistant のメッセージには、`channel` という項目があり、思考の部分は `analysis`、回答は `final` です。次の規則で `decontam-stats` の入力形式に変換しました（`docs/v41-parameter-analysis/convert_sft.py`）。変換した `content` と `reasoning` は、どちらも照合に使います。

- user と tool のメッセージ：テキストの要素を改行でつないで `content` にします。
- assistant のメッセージ：`channel` が `analysis` のものを `reasoning` に、それ以外（回答と、ツールを呼び出すときの引数）を `content` にします。
- developer のメッセージ：指示文（instructions）だけを `content` にします。ツールの定義は照合しません。
- system のメッセージ：モデル名、knowledge cutoff（学習データの時期の上限）、日付などの情報だけなので、照合しません。

### 評価データ（`--ref`）

[swallow-evaluation-instruct](https://github.com/swallow-llm/swallow-evaluation-instruct) は、Swallow チームが公開している、指示に従うモデルの評価フレームワークです。LLM-jp-4.1 の[モデルカード](https://huggingface.co/llm-jp/llm-jp-4.1-8b-thinking)には、これで評価した 21 タスクが載っています。そのうち、認証なしで取得できる 19 タスクを使いました。LLM-jp-4.1 の[技術ブログ](https://llm-jp.nii.ac.jp/blog/llm-jp-4-1/)には、これらのタスクを「swallow-evaluation-instruct が提供するベンチマークの中から比較的高難度のもの」として選んだと書かれています。

- 評価データの 1 問を 1 レコードとし、データセットにある問題文を `content` にしました。選択式の問題（JamC-QA、JMMLU、MMLU-ProX の日本語と英語）では、選択肢の文を、記号（A. など）を付けずに改行でつないで問題文の後に加えました。評価のときに付ける指示文（プロンプトのテンプレート）と、解答は含めていません。
- どの列を問題文とするかは、swallow-evaluation-instruct の各タスクの実装に合わせました（`docs/v41-parameter-analysis/build_refs.py`）。実装は、計測の日の最新のリビジョン（`e8fbf6210eeae8a9cd65ed1d58dd0e4f34239f71`）を見ました。
- 除いたタスク：GPQA Diamond（`Idavidrein/gpqa`）と JGPQA Diamond（`llm-jp/jgpqa`）です。どちらも Hugging Face で利用条件への同意が必要で、認証なしでは取得できません。
- AIME 2026 は、上記のリビジョンに実装がありません。そのため、`MathArena/aime_2026` を使いました。このデータセットで文字列型の列は `problem` だけなので、これを問題文としました。
- 各データセットのリビジョンは `docs/v41-parameter-analysis/download_refs.py` に書いてあります。

19 タスクを 1 つのファイル（36,951 問）にまとめ、`id` を「タスク名:問題の ID」としました（例：`mmluprox_en:1239`、`humanevalplus:HumanEval/159`）。次の表の 2 列目が、このタスク名です。

| 評価タスク | `id` のタスク名 | 問題の数 |
|---|---|---|
| MMLU-ProX（日本語） | `mmluprox_ja` | 11,759 |
| MMLU-ProX（英語） | `mmluprox_en` | 11,759 |
| JMMLU（53 科目） | `jmmlu` | 7,097 |
| JamC-QA | `jamcqa` | 2,309 |
| WMT20（英日、英語の原文） | `wmt20_en_ja` | 1,000 |
| WMT20（日英、日本語の原文） | `wmt20_ja_en` | 993 |
| MATH-500 | `math500` | 500 |
| IFBench | `ifbench` | 300 |
| LiveCodeBench v6 | `lcb_v6` | 175 |
| M-IFEval（日本語） | `mifeval_ja` | 172 |
| JHumanEval | `jhumaneval` | 164 |
| HumanEval+ | `humanevalplus` | 164 |
| PolyMath（日本語、high） | `polymath_ja_high` | 125 |
| PolyMath（日本語、top） | `polymath_ja_top` | 125 |
| JEMHopQA | `jemhopqa` | 120 |
| MCLM MATH-100（日本語） | `mclm_math100_ja` | 99 |
| AIME 2024 | `aime2024` | 30 |
| AIME 2025 | `aime2025` | 30 |
| AIME 2026 | `aime2026` | 30 |

- JMMLU は、swallow-evaluation-instruct と同じく、56 科目のうち 3 科目（`japanese_civics`、`japanese_idiom`、`japanese_geography`）を除いています。
- MCLM MATH-100 は、名前に 100 とありますが、取得したデータセットの行数は 99 です。swallow-evaluation-instruct の `BENCHMARKS.md` でも 99 問とされています。

### トークナイザー

spm には、LLM-jp-4 の公式トークナイザーとして GitHub で公開されている、`llm-jp/llm-jp-tokenizer`（リビジョン `6703508d419960103bdf586a72ce30cc71dd098d`）の `models/ver4.0_alpha1.0/llm-jp-tokenizer_ver4.0_alpha1.0.model` を使いました。LLM-jp-4 の系列の公式のトークナイザーなので選びましたが、LLM-jp-4.1 のモデルがこれと同じトークナイザーを使っているかは確かめていません。

## 計測の方法

llm-jp-decontam のリビジョン `262726cf2af93b53d3c53ec32afc33195d45fd84` の `decontam-stats` を、次の 24 通りの設定で実行しました。`--ref` には、19 タスクをまとめたファイルを渡しました。

| `--tokenizer` | `--ngram-size` | `--normalize` |
|---|---|---|
| `char` | 20、30、50、80、120、200 | `nfkc-lower-ws`、`none` |
| `spm` | 8、13、20、30、50、80 | `nfkc-lower-ws`、`none` |

各実行単位では、次の形で `decontam-stats` を実行しました（`run_sweep.sh` の処理。例は spm、N=13、`none`）。`OUT` は `work/out/<--tokenizer>_<--normalize>_n<N>/<サブセット>__<ファイル名>`（例：`work/out/spm_none_n13/flan__reasoning_low-00000-of-00001`）です。`decontam-stats` は書き出しの途中のファイルを `<--output>.tmp` というパスに作るので、そのパスに名前付きパイプ（FIFO）を作り、`aggregate.py` がそれを読みます。TSV はファイルとして保存しません。`run_sweep.sh` は、実行後に名前付きパイプを消します。

```bash
mkfifo OUT.tsv.tmp
$PY aggregate.py OUT.tsv.tmp OUT.summary.json OUT.strong.tsv.gz &
decontam-stats --data work/sft_jsonl/flan/reasoning_low-00000-of-00001.jsonl.gz \
  --ref work/ref/all.jsonl.gz --output OUT.tsv --ngram-size 13 --normalize none \
  --tokenizer spm \
  --tokenizer-model external/llm-jp-tokenizer/models/ver4.0_alpha1.0/llm-jp-tokenizer_ver4.0_alpha1.0.model
```

`aggregate.py` は、学習データのファイルごとに次のものを `OUT.summary.json` に保存します。`decontam-stats` の標準エラー出力は `OUT.log` に、実行単位の経過時間は `OUT.time` に保存されます。

- 学習データのレコードごとに、そのレコードを含むペアのうち最も大きい `--ref` 側の被覆率、最も大きい `--data` 側の被覆率、全体一致のあるペアがあるか。評価タスクごとにも同じ値を求めます。
- 問題ごとに、その問題と重なるレコードの数と、その問題とのペアの `--ref` 側の被覆率が 0.5 以上のレコードの数。

あわせて、`--ref` 側か `--data` 側の被覆率が 0.5 以上のペアと、全体一致のあるペアの TSV の行だけを `OUT.strong.tsv.gz` に保存します。

`decontam-filter` は、条件に合うペアが 1 つでもあるレコードを取り除きます。被覆率の条件は「指定した値以上」で判定します。`decontam-filter` は、条件を複数指定すると、どれか 1 つに合うペアを条件に合うものとします。そのため、どの条件の組み合わせでも、取り除かれるレコードの数は、レコードごとの 3 つの値から計算できます。

以下の表の列名と `decontam-filter` の指定の対応は、次のとおりです。

| 列名 | `decontam-filter` の指定 |
|---|---|
| ref≥X | `--min-ref-coverage X` |
| data≥Y | `--min-data-coverage Y` |
| short | `--short-texts` |
| ref≥0.5 または short | `--min-ref-coverage 0.5 --short-texts` |

## 結果

### 重なりのあるレコードと、取り除かれるレコードの数

「重なりのあるレコード」の 2 列は参考の値で、`decontam-filter` で取り除かれる数ではありません（`decontam-filter` は、条件を 1 つも指定しないとエラーになります）。列名に「（none）」がある列は `none` の値で、ほかの列は `nfkc-lower-ws` の値です。ほかの条件の値は `docs/v41-parameter-analysis/results.md` の表 A にあります。

| `--tokenizer` | N | 重なりのあるレコード | 重なりのあるレコード（none） | ref≥0.2 | ref≥0.5 | ref≥0.5（none） | ref≥0.8 | ref≥1.0 | data≥0.5 | short | ref≥0.5 または short |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `char` | 20 | 3,834,578 | 3,775,443 | 22,747 | 1,285 | 1,249 | 546 | 322 | 58 | 0 | 1,285 |
| `char` | 30 | 1,249,714 | 1,227,153 | 2,604 | 1,071 | 1,035 | 534 | 319 | 41 | 3 | 1,074 |
| `char` | 50 | 446,480 | 442,222 | 1,327 | 952 | 899 | 487 | 314 | 40 | 8 | 960 |
| `char` | 80 | 1,966 | 1,857 | 1,101 | 774 | 707 | 412 | 281 | 38 | 41 | 815 |
| `char` | 120 | 1,079 | 1,043 | 903 | 605 | 531 | 308 | 212 | 39 | 82 | 687 |
| `char` | 200 | 852 | 806 | 566 | 392 | 334 | 189 | 130 | 42 | 160 | 552 |
| `spm` | 8 | 1,066,107 | 1,052,058 | 9,995 | 918 | 844 | 388 | 316 | 38 | 0 | 918 |
| `spm` | 13 | 146,503 | 130,370 | 2,826 | 717 | 665 | 370 | 313 | 36 | 3 | 720 |
| `spm` | 20 | 23,689 | 19,133 | 1,658 | 651 | 568 | 359 | 302 | 31 | 14 | 665 |
| `spm` | 30 | 4,885 | 3,695 | 955 | 560 | 474 | 336 | 287 | 25 | 29 | 589 |
| `spm` | 50 | 1,394 | 1,199 | 625 | 340 | 294 | 189 | 170 | 24 | 118 | 458 |
| `spm` | 80 | 687 | 649 | 356 | 176 | 148 | 86 | 80 | 19 | 208 | 384 |

- N が最小のときの重なりのあるレコードの数は、最大のときの約 4,500 倍（文字単位）、約 1,550 倍（spm）です。ref≥0.5 で取り除かれるレコードでは、この比は文字単位で約 3.3 倍、spm で約 5.2 倍です。
- ref≥0.2 では、N が小さいときに取り除かれるレコードが急に増えます（文字単位の N=20 で 22,747 件）。ありふれた語句の一致が短い問題の被覆率を押し上げることが原因の候補ですが、例は確かめていません。
- data≥0.5 で取り除かれるレコードは、`none` を含む 24 通りのどの設定でも 18〜58 件です（18 件は spm の N=80、`none`）。限界の節に挙げた、ref≥0.9 の 3 件の例（MMLU-ProX（英語）2 件と MATH-500 1 件）では、学習データのレコードの `data_ngrams` が 7,100〜10,287 で、問題の `ref_ngrams`（214〜418）よりずっと大きく、`--data` 側の被覆率は 0.06 未満でした。問題の全体が含まれていても、学習データのレコードが長いと、`--data` 側の被覆率は小さくなります。

### 重なるレコードが多い問題の例

N が小さい設定で、重なりのある学習データのレコードが最も多い問題は次のとおりです（`docs/v41-parameter-analysis/results.md` の表 D）。

- `mmluprox_ja:1239` と `mmluprox_en:1239`：どちらの問題も、ハイフンが 62 個続く区切り線を含み、それが学習データの区切り線と一致します。`nfkc-lower-ws` の文字単位では、それぞれと重なるレコードは、N=20 で約 100 万件（重なりのあるレコードの 26%）、N=30 で約 67 万件（54%）、N=50 で約 40 万件（90%）です。2 つの問題と重なるレコードが同じかどうかは集計していません。文字単位では、N が 62 を超えると、区切り線だけでは一致しなくなります。
- `humanevalplus:HumanEval/159` と `mmluprox_ja:11689`：`none` の文字単位の N=20 と N=30 で、30 万〜54 万件のレコードと重なります。どちらの問題も空白が 30 個以上続く部分を含み、それが学習データの字下げと一致するためです。`nfkc-lower-ws` では空白の連続が 1 つにまとまるので、この一致は起きません。
- spm の N=8〜20 では、どちらの正規化でも、`mmluprox_ja:8349`、`mmluprox_en:8349`、`mmluprox_ja:10176`、`mmluprox_en:10176`、`humanevalplus:HumanEval/78` が上位になります。最初の 4 つは、数を並べたリストを含む問題です。数の並びやコードの決まった書き方が、多くのレコードと共通のトークン列になることが原因の候補です。

これらの問題とだけ重なるレコードは、`--ref` 側の被覆率が小さいので、`--min-ref-coverage` の条件には合いません。ただし、N が小さいと、TSV の行数と処理時間は大きく増えます（これらの問題がその原因かは比べていません）。文字単位、`nfkc-lower-ws` の N=20 では、TSV は 5 億行を超え、126 実行単位の経過時間の合計は 4.5 時間でした。文字単位、`nfkc-lower-ws` の N=80 では 1.0 時間です（各設定の値は `results.md` の最初の表）。

### WMT20（英日、英語の原文）での一致

WMT20（英日、英語の原文）では、文字単位の N=20 のときだけ、ref≥0.5 で取り除かれるレコードがあります（`nfkc-lower-ws` で 48 件、`none` で 45 件）。WMT20 の原文は 1 文ずつで短いので、一部が一致するだけで `--ref` 側の被覆率が 0.5 を超えます。`nfkc-lower-ws` の 48 件のうち 36 件は、30 文字の問題（`ref_ngrams` が 11）のうち 26 文字の連続した部分が一致したもの（`matched_ngrams` が 7）でした。そのうち 1 件を確かめたところ、学習データの user メッセージは、同じ短い疑問の言い回しを含むだけで、話題は別のものでした。

### 評価タスクごとの結果

文字単位、N=50、`nfkc-lower-ws`、ref≥0.5 の値です。括弧内は、ref≥0.5 の条件に合うペアを 1 つ以上持つ問題の数です。1 つのレコードが複数のタスクの問題と条件に合う場合は、それぞれのタスクに数えています。そのため、合計（969 件）は全体の値（952 件）より多くなります。ほかの設定の値は `docs/v41-parameter-analysis/results.md` の表 B にあります。

| 評価タスク | 取り除かれるレコード |
|---|---|
| MMLU-ProX（英語） | 492（181 問） |
| MATH-500 | 316（104 問） |
| IFBench | 79（11 問） |
| AIME 2024 | 37（2 問） |
| JMMLU（53 科目） | 18（6 問） |
| MCLM MATH-100（日本語） | 11（4 問） |
| HumanEval+ | 6（1 問） |
| JHumanEval | 6（1 問） |
| PolyMath（日本語、top） | 4（1 問） |
| ほかの 10 タスク | 0 |

- MMLU-ProX では、この設定で条件に合うのは英語の問題だけで、日本語の問題（`mmluprox_ja`）は 0 件です。確かめた 2 件の例では、学習データに英語の問題文がそのまま入っていました。
- IFBench の問題は、もとの依頼文に条件の文を加えたものです。1 つの問題（`ifbench:164`）について確かめた 2 件の例では、学習データに、条件の文を除いたもとの依頼文が入っていました。このような場合、`--ref` 側の被覆率は 1 になりません。取り除かれる 79 件のうち、45 件が `--ref` 側の被覆率 0.8 以上、34 件が 0.5 以上 0.8 未満です。
- 次の 6 タスクは、24 通りのどの設定でも、ref≥0.5 で取り除かれるレコードが 0 件です。AIME 2026、LiveCodeBench v6、JamC-QA、M-IFEval（日本語）、PolyMath（日本語、high）、WMT20（日英、日本語の原文）です。
- 次の 4 タスクは、文字単位の N=20 か spm の N=8 のときだけ、ref≥0.5 で取り除かれるレコードがあります。
  - AIME 2025：文字単位の N=20 と spm の N=8（どちらの正規化でも）
  - MMLU-ProX（日本語）：文字単位の N=20 と spm の N=8（どちらの正規化でも）
  - JEMHopQA：spm の N=8 だけ（どちらの正規化でも）
  - WMT20（英日、英語の原文）：文字単位の N=20 だけ（どちらの正規化でも）

### 学習データのサブセットごとの結果

この節は、評価タスクごとの節と違い、全体一致も含めた条件（ref≥0.5 または short）の値です。サブセットごとの数は重複がないので、合計は全体の値（960 件）と同じです。文字単位、N=50、`nfkc-lower-ws` の値を次に示します。ほかの 19 サブセットは 0 件です。取り除かれるレコードの数の上位 2 つは、24 通りのどの設定でも daring_anteater と nemotron3_sft_chat_v3 です。ほかの設定の値は `docs/v41-parameter-analysis/results.md` の表 C にあります。

| サブセット | 取り除かれるレコード |
|---|---|
| daring_anteater | 720 |
| nemotron3_sft_chat_v3 | 192 |
| jaster_v1.4.1 | 38 |
| nemotron_post_v3_math | 6 |
| nemotron3_sft_science_vendor | 4 |

### 全体一致

全体一致で取り除かれるレコードは、文字単位の N=30 のとき 3 件、N=200 のとき 160 件、spm の N=80 のとき 208 件です。全体一致があった設定では、すべて MATH-500 の問題によるものでした。MATH-500 には数十文字の短い問題があり、学習データには、user メッセージの全文がその問題文と同じレコードがあります。

N を大きくすると、N トークン未満の問題が増えます。N トークン未満の問題は n-gram を作れず、`ref_ngrams` が 0 になるので、被覆率の条件には合いません。N を大きくすると ref≥1.0（問題の n-gram がすべて学習データのレコードにある）で取り除かれるレコードが減り、全体一致で取り除かれるレコードが増えるのは、これが原因の候補です。短い問題との一致も取り除くには、`--min-ref-coverage` と `--short-texts` を一緒に指定する必要があります。

### 正規化の影響

`nfkc-lower-ws` は `none` より、ref≥0.5 で取り除かれるレコードが多くなります。`none` に対する増加率は、文字単位の N=20 で最も小さく（1,285 件と 1,249 件、2.9%）、spm の N=80 で最も大きくなります（176 件と 148 件、18.9%）。この文書で例に使う 2 つの設定で、評価タスクごとの数の差（`nfkc-lower-ws` − `none`）は次のとおりです。評価タスクごとの数は 1 つのレコードを複数のタスクに数えるので、差の合計は全体の差と一致するとは限りません。

- 文字単位の N=50（全体の差は 53 件）：MMLU-ProX（英語）が 33 件、IFBench が 20 件多くなります。
- spm の N=13（全体の差は 52 件）：MMLU-ProX（英語）が 39 件、IFBench が 18 件多く、ほかのタスクの合計は 5 件少なくなります。

大文字と小文字の違いや空白の違いを無視して一致することが原因の候補ですが、例は確かめていません。

### 文字単位と spm の比較

ref≥0.5 で取り除かれるレコードの数が近い 2 つの設定を比べます（そのため、例に使う spm の N=13 ではなく N=8 を使います）。`nfkc-lower-ws` の文字単位の N=50（952 件）と spm の N=8（918 件）です。`nfkc-lower-ws` の文字単位の 6 通りと spm の 6 通りを組み合わせた 36 通りのうち、件数の差（34 件）が最も小さい組み合わせです。件数は近いものの、評価タスクごとの内訳は一致しません。MMLU-ProX（英語）は文字単位のほうが多く（492 件と 346 件）、JMMLU と MCLM MATH-100 は spm のほうが多くなります（18 件と 50 件、11 件と 23 件）。

## 限界

- 条件に合うレコードが本当に評価データの問題を含むかは、例でしか確かめていません。確かめた例は次のとおりです。どれも、その設定の `strong.tsv.gz` をファイル名の辞書順に読み、条件に合った行を先頭から順に選びました。書き手が、問題文と学習データのレコードの user メッセージの先頭を目で比べて判断しました。学習データのレコードの識別子は、学習データの `ID` の値です。
  - 文字単位、N=50、`nfkc-lower-ws`、daring_anteater、ref≥0.9：`mmluprox_en:9897` と `daring_anteater_en-6884`、`mmluprox_en:8380` と `daring_anteater_en-15829`、`math500:test/number_theory/149.json` と `daring_anteater_en-63873`
  - 文字単位、N=50、`nfkc-lower-ws`、nemotron3_sft_chat_v3、ref≥0.5：`ifbench:164` と `f5da571c-b978-402b-ac17-b06fe9686e35`、`ifbench:164` と `7371bbac-6287-41fc-bd2d-1e49a2267e3a`
  - 文字単位、N=20、`nfkc-lower-ws`、nemotron3_sft_chat_v3、ref≥0.5：`wmt20_en_ja:22` と `8b924d94-3d14-4139-af81-80f691eb7d9a`

  表の数は条件に合うレコードの数で、評価データの問題を実際に含むレコードの数ではありません。
- 評価データには解答を含めていません。解答だけが学習データに入っている場合は検出できません。
- N トークン未満の問題が、学習データのメッセージの一部として含まれている場合は、どの条件でも検出できません。N を大きくするほど、N トークン未満の問題が増えます。
- `decontam-filter` との一致は、1 ファイル、1 つの設定、3 つの条件でしか確かめていません。
- 評価データには、GPQA Diamond と JGPQA Diamond を含めていません。AIME 2026 は、swallow-evaluation-instruct の実装がないため、別のデータセット（`MathArena/aime_2026`）を使いました。LLM-jp-4.1 の評価に使われた swallow-evaluation-instruct のリビジョンは分かりません。
- 学習データには、再配布されていないサブセットを含めていません。system メッセージとツールの定義も照合していません。
- spm では、トークナイザーを 1 種類しか試していません。LLM-jp-4.1 のモデルと同じトークナイザーかどうかも確かめていません。

## ファイル

`docs/v41-parameter-analysis/` に、計測に使ったスクリプトと結果の表を置いています。

| ファイル | 内容 |
|---|---|
| `pyproject.toml`、`uv.lock` | 取得、変換、集計、表の作成に使う Python 環境の定義と、依存パッケージの版 |
| `download_sft.py`、`download_refs.py` | 学習データと評価データの取得 |
| `convert_sft.py`、`build_refs.py` | `decontam-stats` の入力形式への変換 |
| `make_tasks.sh`、`run_sweep.sh`、`aggregate.py` | 24 通りの設定での照合と集計 |
| `analyze.py` | 集計からの表の作成 |
| `results.md` | 今回の計測で作った表。最初の表は設定ごとの完了ファイル数と経過時間、表 A は条件ごとの取り除かれる数、表 B は評価タスクごと、表 C はサブセットごとの数、表 D は重なりのあるレコードが多い問題 |

## 再現の手順

Linux のマシンのホームディレクトリで、同じ計測を行う手順です。コマンドは bash で実行します。必要なものは、uv、Python 3.13 以上、git、bash、`find`・`xargs`・`sha256sum` などの標準のコマンド、インターネットへの接続です。認証は必要ありません。

- CPU：同時に実行する実行単位の数と同じ数以上のコア（例では 8）。今回の計測は、1 ノード 192 CPU の計算ノード 3 台で、各ノード 88 実行単位ずつ同時に実行しました。
- ディスク：約 32 GB（取得した学習データ 19 GB、変換した学習データ 12 GB、評価データと集計の結果 1 GB 未満）。Hugging Face のキャッシュは、取得先のディレクトリの中の `.cache` に作られ、5 MB 未満でした。
- メモリ：`decontam-stats` 1 プロセスあたり最大で約 1.3 GB（文字単位の N=20 で計測。`aggregate.py` は約 30 MB）。8 実行単位を同時に実行するなら約 11 GB です。変換の手順で使うメモリは計測していません。

1. このリポジトリを取得し、`docs/v41-parameter-analysis/` を最後に変更したコミットに切り替えます。計測に使ったスクリプトは、`262726cf2af93b53d3c53ec32afc33195d45fd84` より後のコミットで加えたためです。4 行目の `git diff` で何も表示されなければ、`src/` は計測に使ったリビジョンと同じです。何か表示された場合は、照合のプログラムが計測のときと違うので、結果が一致しないことがあります。

   ```bash
   git clone https://github.com/llm-jp/llm-jp-decontam.git ~/llm-jp-decontam
   cd ~/llm-jp-decontam
   git checkout $(git log -1 --format=%H -- docs/v41-parameter-analysis/)
   git diff 262726cf2af93b53d3c53ec32afc33195d45fd84 -- src
   uv sync
   mkdir ~/v41-analysis && cd ~/v41-analysis
   cp ~/llm-jp-decontam/docs/v41-parameter-analysis/* .
   uv sync
   ```

   1 回目の `uv sync` は `decontam-stats` の環境を作ります。2 回目の `uv sync` は、データの取得、変換、集計、表の作成に使う環境（`~/v41-analysis/.venv`）を `uv.lock` の版で作ります。以下の手順は、すべて `~/v41-analysis` で実行します。

2. LLM-jp-4 のトークナイザーを取得します。モデルファイルは Git LFS ではなく、通常の clone で取得できます。

   ```bash
   git clone https://github.com/llm-jp/llm-jp-tokenizer.git external/llm-jp-tokenizer
   git -C external/llm-jp-tokenizer checkout 6703508d419960103bdf586a72ce30cc71dd098d
   sha256sum external/llm-jp-tokenizer/models/ver4.0_alpha1.0/llm-jp-tokenizer_ver4.0_alpha1.0.model
   ```

   表示される値が `954fa47c753decffdba93f6cddf5eeda7964a99e2c4496c2cda0c95a84aa33ec` であることを確認してください。

3. 学習データ（約 19 GB、`data/sft/<サブセット>/` に保存）と評価データ（`data/ref/` に保存）を取得します。`download_sft.py` は引数で指定したリビジョンを、`download_refs.py` はスクリプトに書いたリビジョンを取得します。途中で止まった場合は、同じコマンドをもう一度実行してください（取得済みのファイルは、取得し直しません）。

   ```bash
   uv run python download_sft.py cb4210190af6a0000fd91cb5bb8361ad6d6ade01 data/sft
   uv run python download_refs.py
   ```

4. 入力形式に変換します。`convert_sft.py` は、引数に入力の parquet ファイルと出力の `.jsonl.gz` ファイルを受け取ります。下のコマンドのループは、`data/sft` 以下の相対パスを保ったまま `work/sft_jsonl` 以下の出力のパスを作ります（例：`data/sft/flan/reasoning_low-00000-of-00001.parquet` から `work/sft_jsonl/flan/reasoning_low-00000-of-00001.jsonl.gz`）。`build_refs.py` は、`work/ref/<タスク名>.jsonl.gz` と、全タスクをまとめた `work/ref/all.jsonl.gz` を作ります。どちらのスクリプトも出力先のディレクトリを作成するので、事前に作る必要はありません。学習データの変換は、8 並列で約 10 分かかりました。

   ```bash
   find data/sft -name '*.parquet' | sort | while read f; do
     o=${f/data\/sft/work\/sft_jsonl}; echo "$f ${o%.parquet}.jsonl.gz"
   done | xargs -P 8 -L 1 uv run python convert_sft.py
   uv run python build_refs.py
   ```

   `build_refs.py` は、タスクごとの問題の数を表示します。合計が 36,951 であることを確認してください。

5. 照合します。`make_tasks.sh` は、24 通りの設定と 126 ファイルの組み合わせ（3,024 実行単位）を標準出力に書き出します。`run_sweep.sh` は、実行単位ごとに `decontam-stats` を実行し、TSV を `aggregate.py` に渡して、集計の結果だけを `work/out/<設定>/` に保存します（ファイルの名前は「計測の方法」の節の `OUT`）。`run_sweep.sh` の最後の引数は、同時に実行する実行単位の数です。

   ```bash
   bash make_tasks.sh > work/sweep_tasks.txt
   STATS=~/llm-jp-decontam/.venv/bin/decontam-stats \
   SPM=external/llm-jp-tokenizer/models/ver4.0_alpha1.0/llm-jp-tokenizer_ver4.0_alpha1.0.model \
   PY=.venv/bin/python bash run_sweep.sh work/sweep_tasks.txt 8
   ```

   今回の計測では、3,024 実行単位の経過時間の合計が 45.7 時間でした。8 実行単位ずつ同時に実行するなら 6 時間程度が目安です。
   - 失敗した実行単位があると、`run_sweep.sh` は `FAILED` で始まる行を表示し、ほかの実行単位を続けます。失敗した実行単位の `summary.json` は作られません（書きかけの集計は別の名前で書き、完成したときに `summary.json` に名前を変えます）。失敗の原因は `OUT.log` で確かめてください。
   - `run_sweep.sh` は、実行中の実行単位を示すため、`OUT.lock` というディレクトリを作ります。同時に動いている別の `run_sweep.sh` は、ロックのある実行単位を飛ばします。
   - 途中で止めた場合や、失敗した実行単位がある場合は、`run_sweep.sh` が動いていないこと（`pgrep -f decontam-stats` で何も表示されないこと）を確かめてから、`rm -rf work/out/*/*.lock` でロックのディレクトリを消し、同じコマンドを実行してください。`run_sweep.sh` は、`summary.json` がまだない実行単位だけを実行します。

6. 表を作り、このリポジトリにある計測の結果と比べます。

   ```bash
   uv run python analyze.py work/out > results_new.md
   diff ~/llm-jp-decontam/docs/v41-parameter-analysis/results.md results_new.md
   ```

   `results_new.md` の最初の表（設定ごとの完了ファイル数と所要時間）で、「完了ファイル」がすべて 126/126 であることを確認してください。同じ表の「実行単位の経過時間の合計」の列は、マシンによって変わります。ほかの値に違いが出た場合は、再現できていません。そのときは、手順 1 と手順 2 のリビジョンと sha256、手順 4 の問題の数を確かめてください。
