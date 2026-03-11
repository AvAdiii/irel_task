"""
module 6 - visualization

takes graph.json and produces:
  1. graph.html — interactive pyvis DAG visualization
  2. report.md  — summary report with stats and concept list
"""

import json
from pathlib import Path


# edge type -> color mapping
_EDGE_COLORS = {
    "is_prerequisite_for": "#e74c3c",   # red
    "refines":             "#3498db",   # blue
    "is_part_of":          "#2ecc71",   # green
    "temporal_precedence": "#bdc3c7",   # grey
}

_EDGE_LABELS = {
    "is_prerequisite_for": "prereq",
    "refines": "refines",
    "is_part_of": "part-of",
    "temporal_precedence": "temporal",
}

# color nodes by "depth" in the DAG (lighter = earlier in topo order)
_NODE_COLORS = [
    "#1a5276", "#1f618d", "#2471a3", "#2980b9", "#3498db",
    "#5dade2", "#85c1e9", "#aed6f1", "#d4e6f1", "#d5f5e3",
    "#a9dfbf", "#7dcea0", "#52be80", "#27ae60",
]


def build_html(graph: dict, output_path: str):
    """build interactive pyvis graph."""
    from pyvis.network import Network

    net = Network(
        height="750px",
        width="100%",
        directed=True,
        bgcolor="#f8f9fa",
        font_color="#2c3e50",
    )

    # physics for hierarchical layout
    net.set_options("""
    {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed",
          "levelSeparation": 120,
          "nodeSpacing": 200
        }
      },
      "physics": {
        "hierarchicalRepulsion": {
          "centralGravity": 0.0,
          "springLength": 150,
          "springConstant": 0.01,
          "nodeDistance": 200
        }
      },
      "edges": {
        "smooth": {
          "type": "cubicBezier",
          "forceDirection": "vertical"
        },
        "arrows": {
          "to": {"enabled": true, "scaleFactor": 0.8}
        }
      },
      "nodes": {
        "shape": "box",
        "font": {"size": 14, "face": "arial"}
      }
    }
    """)

    topo = graph.get("topological_order", [])
    topo_idx = {name: i for i, name in enumerate(topo)}

    # add nodes
    for node in graph["nodes"]:
        nid = node["id"]
        idx = topo_idx.get(nid, 0)
        color = _NODE_COLORS[min(idx, len(_NODE_COLORS) - 1)]
        sources = ", ".join(node.get("sources", []))
        title = (
            f"<b>{nid}</b><br>"
            f"mentions: {node['mention_count']}<br>"
            f"first: {node['first_mention']:.0f}s<br>"
            f"last: {node['last_mention']:.0f}s<br>"
            f"sources: {sources}<br>"
            f"topo rank: {idx + 1}/{len(topo)}"
        )
        net.add_node(
            nid,
            label=nid,
            title=title,
            color=color,
            level=idx,
            size=20 + min(node["mention_count"], 30),
        )

    # add edges
    for edge in graph["edges"]:
        etype = edge["type"]
        color = _EDGE_COLORS.get(etype, "#95a5a6")
        label = _EDGE_LABELS.get(etype, etype)
        width = edge["confidence"] * 3
        net.add_edge(
            edge["source"],
            edge["target"],
            color=color,
            title=f"{label} (conf={edge['confidence']:.2f})",
            width=width,
            label="" if etype == "temporal_precedence" else label,
        )

    net.save_graph(output_path)


def build_report(graph: dict, concepts_data: dict, norm_count: int, raw_count: int) -> str:
    """build a markdown summary report."""
    lines = []
    lines.append("# Pedagogical Flow Report")
    lines.append(f"**Video:** `{graph['video_id']}`\n")

    lines.append("## Pipeline Summary")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Raw ASR segments | {raw_count} |")
    lines.append(f"| Normalized segments | {norm_count} |")
    lines.append(f"| Concepts extracted | {graph['total_nodes']} |")
    lines.append(f"| Graph edges | {graph['total_edges']} |")
    lines.append(f"| Causal anchors detected | {graph['causal_anchors_detected']} |")
    lines.append(f"| Causal edges created | {graph.get('causal_edges_created', 'N/A')} |")
    lines.append("")

    lines.append("## Topological Order (Teaching Sequence)")
    for i, name in enumerate(graph["topological_order"], 1):
        lines.append(f"{i}. **{name}**")
    lines.append("")

    lines.append("## Concepts")
    lines.append("| # | Concept | Mentions | First (s) | Sources |")
    lines.append("|---|---------|----------|-----------|---------|")
    for i, c in enumerate(concepts_data["concepts"], 1):
        sources = ", ".join(c["sources"])
        lines.append(f"| {i} | {c['name']} | {c['mention_count']} | {c['first_mention']:.0f} | {sources} |")
    lines.append("")

    if concepts_data.get("example_tree", {}).get("node_labels"):
        tree = concepts_data["example_tree"]
        lines.append("## Example Tree")
        lines.append(f"Nodes: {', '.join(tree['node_labels'])}\n")

    lines.append("## Edge Distribution")
    from collections import Counter
    edge_types = Counter(e["type"] for e in graph["edges"])
    lines.append("| Edge Type | Count |")
    lines.append("|-----------|-------|")
    for t, n in sorted(edge_types.items()):
        lines.append(f"| {t} | {n} |")
    lines.append("")

    lines.append("## Prerequisite Edges (Domain + Causal)")
    for e in graph["edges"]:
        if e["type"] in ("is_prerequisite_for", "refines", "is_part_of"):
            lines.append(f"- **{e['source']}** -> **{e['target']}** ({e['type']}, conf={e['confidence']:.2f})")
    lines.append("")

    return "\n".join(lines)


def run(video_id: str, data_root: str = "data") -> dict:
    out_dir = Path(data_root) / video_id
    graph_path = out_dir / "graph.json"
    concepts_path = out_dir / "concepts.json"
    normalized_path = out_dir / "normalized_segments.json"
    aligned_path = out_dir / "aligned_segments.json"
    html_path = out_dir / "graph.html"
    report_path = out_dir / "report.md"

    with open(graph_path) as f:
        graph = json.load(f)
    with open(concepts_path) as f:
        concepts = json.load(f)
    with open(normalized_path) as f:
        norm = json.load(f)
    with open(aligned_path) as f:
        aligned = json.load(f)

    # build interactive graph
    build_html(graph, str(html_path))
    print(f"[m6] -> {html_path}")

    # build report
    report = build_report(graph, concepts, len(norm), len(aligned))
    with open(report_path, "w") as f:
        f.write(report)
    print(f"[m6] -> {report_path}")

    return {"html": str(html_path), "report": str(report_path)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--data-root", default="data")
    args = parser.parse_args()
    run(args.video_id, args.data_root)
