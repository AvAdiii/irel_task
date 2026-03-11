"""
module 7 - orchestration

unified pipeline entry point with CLI.
runs all modules in sequence: M1 -> M2 -> M3 -> M4 -> M5 -> M6
each stage caches its output — re-runs skip completed stages.

usage:
  python pipeline.py "https://youtu.be/XRcC7bAtL3c"
  python pipeline.py "https://youtu.be/XRcC7bAtL3c" --data-root ./output --model small
  python pipeline.py "https://youtu.be/XRcC7bAtL3c" --force-from m3  # re-run m3 onward
"""

import argparse
import json
import sys
import time
from pathlib import Path

import m1_ingest
import m2_extract
import m3_normalize
import m4_concepts
import m5_prereqs
import m6_visualize


_STAGES = ["m1", "m2", "m3", "m4", "m5", "m6"]

_STAGE_FILES = {
    "m3": "normalized_segments.json",
    "m4": "concepts.json",
    "m5": "graph.json",
    "m6": "graph.html",
}


def _clear_from(video_id: str, data_root: str, stage: str):
    """remove cached outputs from a given stage onward to force re-run."""
    out_dir = Path(data_root) / video_id
    idx = _STAGES.index(stage)
    for s in _STAGES[idx:]:
        fname = _STAGE_FILES.get(s)
        if fname:
            p = out_dir / fname
            if p.exists():
                p.unlink()
                print(f"  cleared {p}")
    # also clear report.md if m6 is being re-run
    report = out_dir / "report.md"
    if report.exists() and idx <= _STAGES.index("m6"):
        report.unlink()
        print(f"  cleared {report}")


def run_pipeline(url: str, data_root: str = "data", model_size: str = "small",
                 force_from: str | None = None):
    """run the full pedagogical flow extraction pipeline."""
    t0 = time.time()
    print("=" * 60)
    print("  Code-Mixed Pedagogical Flow Extractor")
    print("=" * 60)
    print(f"  URL        : {url}")
    print(f"  Data root  : {data_root}")
    print(f"  ASR model  : {model_size}")
    if force_from:
        print(f"  Force from : {force_from}")
    print()

    # stage 1: ingestion
    print("-" * 60)
    print("[1/6] Ingestion")
    print("-" * 60)
    m1 = m1_ingest.run(url, data_root)
    vid = m1["video_id"]

    if force_from:
        print(f"\n  forcing re-run from {force_from}:")
        _clear_from(vid, data_root, force_from)
        print()

    # stage 2: extraction
    print("-" * 60)
    print("[2/6] Multi-modal Extraction (ASR + OCR)")
    print("-" * 60)
    aligned = m2_extract.run(vid, data_root, model_size=model_size)

    # stage 3: normalization
    print("-" * 60)
    print("[3/6] Linguistic Normalization")
    print("-" * 60)
    normalized = m3_normalize.run(vid, data_root)

    # stage 4: concept extraction
    print("-" * 60)
    print("[4/6] Concept Extraction")
    print("-" * 60)
    concepts = m4_concepts.run(vid, data_root)

    # stage 5: prerequisite mapping
    print("-" * 60)
    print("[5/6] Prerequisite Mapping")
    print("-" * 60)
    graph = m5_prereqs.run(vid, data_root)

    # stage 6: visualization
    print("-" * 60)
    print("[6/6] Visualization")
    print("-" * 60)
    viz = m6_visualize.run(vid, data_root)

    elapsed = time.time() - t0
    out_dir = Path(data_root) / vid

    print()
    print("=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Video ID       : {vid}")
    print(f"  Segments       : {len(aligned)} raw -> {len(normalized)} normalized")
    print(f"  Concepts       : {concepts['total_concepts']}")
    print(f"  Graph          : {graph['total_nodes']} nodes, {graph['total_edges']} edges")
    print(f"  Topo order     : {' -> '.join(graph['topological_order'][:6])}...")
    print(f"  Elapsed        : {elapsed:.1f}s")
    print(f"  Output dir     : {out_dir}/")
    print(f"  Interactive DAG: {viz['html']}")
    print(f"  Report         : {viz['report']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Code-Mixed Pedagogical Flow Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python pipeline.py "https://youtu.be/XRcC7bAtL3c"
  python pipeline.py "https://youtu.be/XRcC7bAtL3c" --data-root ./output
  python pipeline.py "https://youtu.be/XRcC7bAtL3c" --force-from m3
""",
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--data-root", default="data", help="directory for cached outputs")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: small)")
    parser.add_argument("--force-from", choices=_STAGES,
                        help="force re-run from this stage onward")
    args = parser.parse_args()
    run_pipeline(args.url, args.data_root, args.model, args.force_from)


if __name__ == "__main__":
    main()
