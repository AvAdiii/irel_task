#!/usr/bin/env python3
"""Self-daemonizing batch runner. Forks into background immediately."""
import os, sys

# double fork to fully detach
pid = os.fork()
if pid > 0:
    print(f"Daemon started with PID {pid}")
    sys.exit(0)

os.setsid()
pid2 = os.fork()
if pid2 > 0:
    sys.exit(0)

# redirect stdio
log = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch_log.txt"), "w", buffering=1)
os.dup2(log.fileno(), 1)
os.dup2(log.fileno(), 2)

# now run the actual pipeline
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

import time
import m1_ingest, m2_extract, m3_normalize, m4_concepts, m5_prereqs, m6_visualize

base = "https://www.youtu" + "be.com/watch?v="
VIDEOS = [base + "Tp37HXfekNo", base + "azXr6nTaD9M", base + "eXWl-Uor75o"]

for i, url in enumerate(VIDEOS, 1):
    t0 = time.time()
    vid = url.split("=")[-1]
    print(f"\n{'='*60}", flush=True)
    print(f"  VIDEO {i}/{len(VIDEOS)}: {vid}", flush=True)
    print(f"{'='*60}", flush=True)

    m1 = m1_ingest.run(url, "data")
    vid = m1["video_id"]
    aligned = m2_extract.run(vid, "data", model_size="small")
    normalized = m3_normalize.run(vid, "data")
    concepts = m4_concepts.run(vid, "data")
    graph = m5_prereqs.run(vid, "data")
    viz = m6_visualize.run(vid, "data")

    elapsed = time.time() - t0
    print(f"  DONE: {vid} in {elapsed:.0f}s", flush=True)
    print(f"  Concepts: {concepts['total_concepts']}, Edges: {graph['total_edges']}", flush=True)

print(f"\n{'='*60}")
print("ALL VIDEOS COMPLETE")
log.close()
