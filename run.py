import m1_ingest, m2_extract, m3_normalize, m4_concepts, m5_prereqs, m6_visualize

url = "https://youtu.be/" + "XRcC7bAtL3c"

print("=" * 60)
print("step 1/6 - ingestion")
print("=" * 60)
m1 = m1_ingest.run(url, "data")

vid = m1["video_id"]

print("\n" + "=" * 60)
print("step 2/6 - extraction (asr + ocr + alignment)")
print("=" * 60)
aligned = m2_extract.run(vid, "data", model_size="small")

print("\n" + "=" * 60)
print("step 3/6 - normalization")
print("=" * 60)
normalized = m3_normalize.run(vid, "data")

print("\n" + "=" * 60)
print("step 4/6 - concept extraction")
print("=" * 60)
concepts = m4_concepts.run(vid, "data")

print("\n" + "=" * 60)
print("step 5/6 - prerequisite mapping")
print("=" * 60)
graph = m5_prereqs.run(vid, "data")

print("\n" + "=" * 60)
print("step 6/6 - visualization")
print("=" * 60)
viz = m6_visualize.run(vid, "data")

print("\n" + "=" * 60)
print("done")
print(f"  video id      : {vid}")
print(f"  segments      : {len(aligned)} raw -> {len(normalized)} normalized")
print(f"  concepts      : {concepts['total_concepts']}")
print(f"  graph         : {graph['total_nodes']} nodes, {graph['total_edges']} edges")
print(f"  topo order    : {' -> '.join(graph['topological_order'][:6])}...")
print(f"  output dir    : data/{vid}/")
print(f"  graph html    : {viz['html']}")
print(f"  report        : {viz['report']}")
print("=" * 60)
