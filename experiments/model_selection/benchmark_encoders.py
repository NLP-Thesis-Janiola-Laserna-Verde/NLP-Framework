"""Benchmark the encoders: mean inference time per document and peak memory.

Run from the repository root, once on each laptop:
    pip install psutil
    python experiments/model_selection/benchmark_encoders.py 

Output: data/benchmarks/benchmark_<machine>.csv. Combine the laptops' files with:
    python experiments/model_selection/benchmark_encoders.py --merge
"""
import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "retrieval" / "candidates_pilot_tuning_validation_test_enriched.csv"
OUT_DIR = ROOT / "data" / "benchmarks"
MODELS = ["all-MiniLM-L6-v2", "all-mpnet-base-v2", "allenai-specter"]


def peak_rss_mb():
    """Peak memory in MB on Windows, macOS and Linux; never raises."""
    import psutil
    mi = psutil.Process().memory_info()
    if hasattr(mi, "peak_wset"):  # Windows
        return mi.peak_wset / 2**20
    try:  # macOS / Linux only (the module does not exist on Windows)
        import resource
        peak = resource.getrusage(getattr(resource, "RUSAGE_SELF")).ru_maxrss
        return peak / 2**20 if sys.platform == "darwin" else peak / 1024
    except (ImportError, AttributeError):
        return mi.rss / 2**20  # fallback: current memory


def current_rss_mb():
    import psutil
    return psutil.Process().memory_info().rss / 2**20


def load_texts(path, sets, n_docs, seed, sep):
    import pandas as pd
    df = pd.read_csv(path)
    df = df[df["set"].isin(sets)]
    title = df["title"].fillna("").str.strip()
    abstract = df["abstract"].fillna("").str.strip()
    texts = (title + sep + abstract).where(abstract.ne(""), title).str.strip()
    texts = texts[texts.ne("")].sort_index()
    return texts.sample(n=min(n_docs, len(texts)), random_state=seed).tolist()


def worker(a):
    import torch
    from sentence_transformers import SentenceTransformer

    base = current_rss_mb()
    t0 = time.perf_counter()
    model = SentenceTransformer(a.worker, device="cpu")
    load_s = time.perf_counter() - t0
    after_load = current_rss_mb()

    sep = f" {model.tokenizer.sep_token} " if "specter" in a.worker.lower() else ". "
    texts = load_texts(a.input, a.sets, a.n_docs, a.seed, sep)

    for t in texts[:a.warmup]:
        model.encode([t], normalize_embeddings=True, show_progress_bar=False)

    times = []
    for _ in range(a.repeats):
        for t in texts:
            s = time.perf_counter()
            model.encode([t], batch_size=1, normalize_embeddings=True, show_progress_bar=False)
            times.append((time.perf_counter() - s) * 1000)

    s = time.perf_counter()
    model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    batch_s = time.perf_counter() - s

    times.sort()
    print("RESULT " + json.dumps({
        "model": a.worker,
        "n_docs": len(texts),
        "repeats": a.repeats,
        "ms_per_doc_mean": round(statistics.mean(times), 2),
        "ms_per_doc_median": round(statistics.median(times), 2),
        "ms_per_doc_p95": round(times[int(0.95 * (len(times) - 1))], 2),
        "docs_per_sec_batch": round(len(texts) / batch_s, 2),
        "load_seconds": round(load_s, 2),
        "rss_before_mb": round(base, 1),
        "rss_after_load_mb": round(after_load, 1),
        "peak_rss_mb": round(peak_rss_mb(), 1),
        "torch_threads": torch.get_num_threads(),
    }))


def machine_info(name):
    import psutil
    import torch
    cpu = platform.processor() or platform.machine()
    return {
        "machine": name,
        "os": f"{platform.system()} {platform.release()}",
        "cpu": cpu,
        "cores_physical": psutil.cpu_count(logical=False),
        "cores_logical": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "python": platform.python_version(),
        "torch": torch.__version__,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=platform.node(), help="label for this laptop")
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--input", default=str(INPUT))
    ap.add_argument("--sets", nargs="+", default=["validation"])
    ap.add_argument("--n-docs", type=int, default=100)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--worker", help=argparse.SUPPRESS)
    ap.add_argument("--merge", action="store_true", help="combine data/benchmarks/benchmark_*.csv")
    a = ap.parse_args()

    if a.worker:
        return worker(a)

    import pandas as pd
    if a.merge:
        files = sorted(p for p in OUT_DIR.glob("benchmark_*.csv") if p.stem != "benchmark_all")
        out = pd.concat([pd.read_csv(p) for p in files], ignore_index=True)
        out.to_csv(OUT_DIR / "benchmark_all.csv", index=False)
        print(out.drop(columns=["os", "cpu", "python", "torch"], errors="ignore").to_string(index=False))
        return

    missing = []
    for mod, pkg in [("psutil", "psutil"), ("torch", "torch"),
                     ("sentence_transformers", "sentence-transformers"), ("pandas", "pandas")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        raise SystemExit("Missing packages. Run:\n    pip install " + " ".join(missing))
    if not Path(a.input).exists():
        raise SystemExit(f"Input file not found: {a.input}\nRun from the repository root.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    info = machine_info(a.machine)
    print(info)
    rows = []
    for m in a.models:
        print(f"\n== {m}", flush=True)
        cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", m,
               "--input", a.input, "--sets", *a.sets, "--n-docs", str(a.n_docs),
               "--repeats", str(a.repeats), "--warmup", str(a.warmup), "--seed", str(a.seed)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        line = next((l for l in proc.stdout.splitlines() if l.startswith("RESULT ")), None)
        if proc.returncode != 0 or line is None:
            raise SystemExit(f"{m} failed:\n{proc.stderr[-2000:]}")
        res = json.loads(line[len("RESULT "):])
        print({k: res[k] for k in ("ms_per_doc_mean", "peak_rss_mb", "load_seconds")})
        rows.append({**info, **res})

    out = OUT_DIR / f"benchmark_{a.machine}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()