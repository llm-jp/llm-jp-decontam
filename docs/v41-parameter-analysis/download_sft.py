"""Download the official LLM-jp-4.1 SFT data (public part) at a fixed revision."""
import sys
from huggingface_hub import HfApi, snapshot_download

repo = "llm-jp/llm-jp-4.1-thinking-sft-data"
revision = sys.argv[1] if len(sys.argv) > 1 else HfApi().dataset_info(repo).sha
print("revision", revision, flush=True)
snapshot_download(repo, repo_type="dataset", revision=revision, local_dir=sys.argv[2] if len(sys.argv) > 2 else "data/sft", max_workers=8)
print("done", flush=True)
