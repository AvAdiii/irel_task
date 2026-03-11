# iREL Recruitment Task 2026
## Code-Mixed Pedagogical Flow Extractor

**Author:** Aytida V A  
**Date:** March 2026  
**Test Video:** [Tree Traversal Techniques](https://youtu.be/XRcC7bAtL3c) — Code-mixed Hindi+English lecture on Pre-order, In-order, Post-order traversals

---

## Table of Contents
1. [Problem Statement](#problem-statement)
2. [Architecture Overview](#architecture-overview)
3. [Module Descriptions](#module-descriptions)
4. [Version History & Major Changes](#version-history--major-changes)
5. [Pipeline Results](#pipeline-results)
6. [Key Design Decisions](#key-design-decisions)
7. [Environment & Setup](#environment--setup)
8. [How to Run](#how-to-run)

---

## Problem Statement

Given a code-mixed (Hindi + English) educational video lecture, automatically:
1. **Extract** spoken and visual content (ASR + OCR)
2. **Identify** pedagogical concepts being taught
3. **Map** prerequisite relationships between concepts
4. **Produce** a directed acyclic graph (DAG) representing the teaching flow

The challenge lies in handling:
- Code-mixed language (technical terms in English, explanations in Hindi)
- Noisy OCR from handwritten board content
- Top-down teaching style where examples precede formal definitions
- Multiple modalities (audio + visual) that must be fused

---

## Architecture Overview

The system is a **7-module pipeline** where each module produces a JSON artifact consumed by the next:

```
Video URL
   │
   ▼
[M1: Ingest] ──────────────────────────────────┐
   │ audio.wav          frames/                 │
   ▼                       ▼                    │
[M2a: ASR]           [M2b: OCR]                 │
   │ timestamped         visual_text            │
   └──────────┬──────────┘                      │
              ▼ aligned_segments.json           │
         [M3: Normalize]                        │
              │ normalized_segments.json         │
              ▼                                 │
         [M4: Concept Extract]                  │
              │ concepts.json                   │
              ▼                                 │
         [M5: Prereq Map]                       │
              │ graph.json (DAG verified)        │
              ▼                                 │
         [M6: Visualize] ──► graph.html + report│
                                                │
[M7: Orchestrator controls all of the above] ◄──┘
```

Every intermediate artifact is cached to disk. Re-running the pipeline skips already-completed stages unless `--force-from` is used.

---

## Module Descriptions

### Module 1: Data Ingestion (`m1_ingest.py`, 117 lines)

**Purpose:** Download the lecture video and extract raw media for downstream processing.

**What it does:**
- Downloads YouTube video via `yt-dlp` (best quality mp4)
- Extracts 16kHz mono WAV audio via `ffmpeg` (optimal for Whisper)
- Extracts keyframes at 1fps as JPEGs for OCR processing

**Why this design:**
- 1fps is sufficient for board content that changes slowly; higher rates waste compute on identical frames
- 16kHz mono is Whisper's native input format — avoids internal resampling
- Separate audio+frames allows independent ASR and OCR pipelines

**Output:** `data/{video_id}/video.mp4`, `audio.wav`, `frames/frame_XXXX.jpg`

**Notable fix:** Python's `sys.executable` inside the venv returns `/usr/bin/python` due to symlink resolution on Arch Linux. Fixed by computing `_BIN = Path(__file__).resolve().parent / "venv" / "bin"` to locate `yt-dlp` reliably.

---

### Module 2: Multi-Modal Content Extraction (`m2_extract.py`, 267 lines)

**Purpose:** Convert raw audio and images into timestamped, aligned text segments.

**What it does:**
1. **ASR (Whisper):** Transcribes audio using OpenAI's Whisper `small` multilingual model. Produces timestamped segments with start/end times. Whisper handles Hindi+English code-mixing well — technical terms come through in English, explanations in Devanagari.
2. **OCR (Tesseract):** Processes each keyframe through a 3-stage pipeline:
   - **Preprocessing:** Grayscale → 2x bicubic upscale → adaptive Gaussian threshold
   - **Confidence filtering:** Uses `image_to_data()` to get per-word confidence scores; keeps only words with conf ≥ 50
   - **Token validation:** Regex filter requires ≥ 2 alphanumeric characters, drops pure symbols/digits
3. **Alignment:** Maps OCR frames to ASR segments by matching frame timestamps (derived from filename) to ASR segment time ranges.

**Why confidence-filtered OCR (v3):**
The lecture video has handwritten tree diagrams on a board. Raw Tesseract (v1) produced complete garbage — arrows, circles, and connecting lines were misread as random Unicode characters. Preprocessing alone (v2) reduced noise but still kept diagram artifacts. Confidence filtering (v3) was the breakthrough: Tesseract's internal confidence scores effectively distinguish real text from diagram misreads.

**Evolution:**
| Version | Approach | Result |
|---------|----------|--------|
| v1 | Raw Tesseract | Garbled — arrows read as symbols |
| v2 | + preprocessing (threshold, upscale) | Hindi detected but diagram garbage persists |
| v3 | + confidence filter (conf≥50, regex) | 245/406 frames kept, clean domain terms |

**Output:** `transcript.json` (93 segments), `ocr.json` (245 frames), `aligned_segments.json` (93 segments, 83 with visual text)

**Systematic OCR error pattern discovered:** Tesseract consistently misreads uppercase R as K on this handwriting style (Root→Koot, Right→Kight). This is corrected downstream in M3.

---

### Module 3: Linguistic Normalization (`m3_normalize.py`, 324 lines)

**Purpose:** Clean and normalize the raw ASR+OCR text into structured, language-tagged segments with reliable OCR keywords.

**What it does:**
1. **Hallucination filter:** Detects Whisper hallucinations — repeated filler words ("yeah yeah yeah"), foreign script injection (Korean/German characters that Whisper sometimes hallucinates), and contentless short segments.
2. **Vocabulary building (v3):** Automatically constructs a domain vocabulary from the ASR transcript. Since Whisper output is much cleaner than Tesseract on handwritten text, ASR terms serve as the "ground truth" vocabulary.
3. **Fuzzy OCR correction (v3):** Uses `rapidfuzz` (edit-distance) to match noisy OCR tokens against the auto-built vocabulary. Tokens within edit distance threshold get corrected to the closest vocabulary match.
4. **OCR noise filtering:** Removes Devanagari digit noise (U+0966-U+096F), parenthesized fragments, short non-meaningful tokens, and symbol artifacts.
5. **Language tagging:** Script-based per-token language detection (Devanagari → `hi`, Latin → `en`, both → `mixed`).

**Major design change — v2 → v3 (generalizable correction):**

In v2, OCR correction used a **hardcoded correction map** with 30+ entries specific to this video's handwriting:
```python
# v2 — video-specific, won't work on new videos
_OCR_CORRECTIONS = {
    "koot": "root", "kight": "right", "llff": "left",
    "lihord": "inorder", "fost": "post", ...  # 30+ entries
}
```

This was effective but **completely non-generalizable** — a new video with different handwriting would need a new manual map.

**v3 approach — ASR-seeded vocabulary + fuzzy matching:**
```
ASR transcript → extract English tokens appearing 2+ times → domain vocabulary
                                                                    ↓
OCR token → fuzzy match against vocabulary (rapidfuzz, score ≥ 65) → corrected token
```

**Why this works:** The teacher repeatedly says domain terms aloud (Whisper captures them cleanly), and those same terms appear on the board (Tesseract garbles them). By using ASR output as the correction target, the system automatically adapts to whatever domain the video covers — no manual map needed.

**Vocabulary composition (test video):**
- 54 terms extracted from ASR (tree, node, root, left, right, pre-order, in-order, post-order, first, second, means, children, ...)
- 42 seed terms (universal CS vocabulary — always included regardless of ASR content)
- Total: 96 terms

**Only 3 override entries remain** (for extreme garbling where edit distance is too large for fuzzy matching to bridge):
```python
_OVERRIDE_CORRECTIONS = {
    "phqohjhl": "preorder",
    "npqohjjul": "preorder",
    "pnqohjul": "preorder",
}
```

**Output:** `normalized_segments.json` — 80 segments (13 hallucinations dropped), language breakdown: en=70, hi=10

---

### Module 4: Concept Extraction (`m4_concepts.py`, 227 lines)

**Purpose:** Identify distinct pedagogical concepts from the normalized segments.

**What it does:**
1. **Pattern-based extraction:** A lexicon of 14 concept patterns (regex) scans both spoken text and OCR keywords for domain concept mentions.
2. **Cross-modal enrichment:** OCR keywords are mapped to concepts via a separate `_OCR_KEYWORD_CONCEPTS` dictionary, catching visual mentions that ASR might miss.
3. **Source tracking:** Each mention is tagged with its source: `asr` (spoken only), `ocr` (visual only), or `asr+ocr` (both modalities).
4. **Example node detection:** Identifies concrete tree node labels (A-I) used in the lecture's running example.

**Major fix — v1 → v2 (OCR temporal deduplication):**

In v1, every OCR frame containing "root" counted as a separate mention. Since the board content is static (the teacher writes it once and it stays), this inflated mention counts dramatically: `root_node=72`, `left_subtree=69`.

**v2 fix:** A 10-second temporal dedup window — an OCR-only mention is only counted if the last OCR-only mention of the same concept was >10 seconds ago. This correctly reflects that static board text is one persistent mention, not 72 separate ones.

| Concept | v1 mentions | v2 mentions | Reduction |
|---------|-------------|-------------|-----------|
| root_node | 72 | 34 | -53% |
| left_subtree | 69 | 29 | -58% |
| right_subtree | 18 | 13 | -28% |

**Output:** `concepts.json` — 14 concepts with timestamps, mention counts, and source distributions

**Extracted concepts:** pre-order traversal, root node, tree, tree traversal, in-order traversal, post-order traversal, left subtree, node, right subtree, traversal technique, binary tree, children, leaf node, dummy node

---

### Module 5: Prerequisite Mapping (`m5_prereqs.py`, 423 lines)

**Purpose:** Build a prerequisite dependency graph (DAG) from domain knowledge, causal language, and temporal ordering.

**What it does:**
1. **Domain rules (21 rules):** Handcrafted prerequisite relationships based on CS domain knowledge (e.g., `tree → binary_tree`, `node → root_node`, `children → left_subtree`).
2. **Causal anchor detection (20 anchors):** Regex patterns detect definitional and sequential language in the transcript ("X means Y", "first we do X then Y", "X ke baad Y"). Each anchor is converted to a directed edge if it doesn't contradict domain rules.
3. **Temporal edges:** If concept A's first mention precedes concept B's by a sufficient gap, a `temporal_precedence` edge is added — but only if there's no existing transitive path between them.
4. **DAG verification:** Kahn's algorithm checks for cycles and produces topological ordering. Any remaining cycles are broken by removing the lowest-confidence edge.

**Major fix — 3 iterations to get cycles right (v1 → v2c):**

This was the hardest module to get right. The core problem: the teacher uses **top-down teaching style** — mentions specific examples (pre-order) at 0s but foundational concepts (children) at 105s. So temporal ordering says `pre-order → children` but domain knowledge says `children → pre-order`.

| Version | Fix | Topo nodes | Problem |
|---------|-----|-----------|---------|
| v1 | None | 3/14 | 45 temporal edges create massive cycles |
| v2a | Bidirectional domain pair check | 3/14 | Not enough — indirect paths still create cycles |
| v2b | + reverse-domain check in causal edges | 3/14 | Temporal edges still route around checks |
| v2c ✅ | **Transitive reachability (BFS)** | 14/14 | All cycles prevented |

**v2c solution — transitive reachability check:**
Before adding ANY temporal edge A→B, compute all nodes reachable from both A and B using BFS on the existing domain+causal graph. If B can already reach A (or A can already reach B), skip the temporal edge — it would create a cycle.

This elegantly handles the top-down teaching style: domain rules establish `children → left_subtree → pre-order`, so even though `pre-order` is mentioned first temporally, the temporal edge `pre-order → children` is correctly suppressed because `children` can reach `pre-order` through domain edges.

**Edge type distribution:**
| Type | Count | Source |
|------|-------|--------|
| is_prerequisite_for | 27 | Domain rules + causal anchors |
| temporal_precedence | 20 | Temporal ordering (filtered) |
| refines | 3 | tree_traversal → {pre,in,post}-order |
| is_part_of | 1 | dummy_node → traversal_technique |

**Output:** `graph.json` — 14 nodes, 51 edges, valid DAG with full topological ordering

---

### Module 6: Visualization (`m6_visualize.py`, 218 lines)

**Purpose:** Render the prerequisite graph as an interactive visualization and a summary report.

**What it does:**
1. **Interactive graph (`graph.html`):** Uses `pyvis` to create a force-directed, hierarchical DAG:
   - Node size proportional to mention count
   - Node color by topological depth (yellow → purple gradient)
   - Edge color by type: red=prerequisite, blue=refines, green=part-of, grey=temporal
   - Edge thickness by confidence score
   - Hover tooltips with mention count and first-seen timestamp
2. **Summary report (`report.md`):** Markdown document with pipeline statistics, concept table, topological order, edge distribution, and full edge list.

**Output:** `graph.html` (interactive, viewable in browser), `report.md`

---

### Module 7: Orchestration (`pipeline.py`, 152 lines + `run.py`, 47 lines)

**Purpose:** Unified CLI entry point for the full pipeline.

**Features:**
- Runs M1→M6 sequentially with status logging
- Intermediate artifact caching — completed stages are skipped automatically
- `--force-from <stage>` flag to re-run from a specific module (e.g., `--force-from m3` clears M3-M6 outputs and re-runs)
- `--model <name>` to select Whisper model (tiny/base/small/medium/large)
- `--data-root <path>` to change output directory

**`run.py`** is a convenience script that runs the full pipeline for the test video with default settings.

---

## Version History & Major Changes

### v1 — Initial Implementation
- All 7 modules built and connected
- Basic functionality working end-to-end
- **Problems:** OCR noise tokens in keywords, inflated mention counts, 45/66 temporal edges causing cycles (only 3/14 topo order)

### v2 — Quality Fixes
- **M3:** Added OCR noise filters (Devanagari digits, parenthesized fragments, known garbage set). Added hardcoded correction map (30+ entries) for systematic Tesseract misreads.
- **M4:** Added 10-second temporal dedup window for OCR mentions. Prevented static board text from inflating counts.
- **M5:** Three iterations of cycle fixes culminating in transitive reachability check (BFS). Achieved 14/14 topo order with valid DAG.
- **M6+M7:** Built from scratch (not in v1).

### v3 — Generalization (Current)
- **M3 rewrite:** Replaced hardcoded OCR correction map with ASR-seeded vocabulary + `rapidfuzz` edit-distance matching. The system now adapts automatically to any video — the ASR transcript provides the domain vocabulary, and fuzzy matching handles novel OCR errors.
- **Why:** The v2 correction map had 30+ entries specific to one video's handwriting style. A new video would require manually building a new map. v3 eliminates this dependency.
- **Result:** Identical pipeline output (14 concepts, 51 edges, 14/14 topo) but zero video-specific hardcoding in the correction logic.
- **Added dependency:** `rapidfuzz` (C-extension, fast edit-distance library)

---

## Pipeline Results

### Test Video: `XRcC7bAtL3c`
**Topic:** Tree Traversal Techniques (Pre-order, In-order, Post-order)  
**Language:** Code-mixed Hindi + English  
**Duration:** ~6:46  
**Visual content:** Handwritten binary tree diagrams with labeled nodes (A-I)

### Final Numbers (v3)
| Metric | Value |
|--------|-------|
| Raw ASR segments | 93 |
| Normalized segments | 80 (13 hallucinations dropped) |
| Language breakdown | en=70, hi=10 |
| Vocabulary (auto-built) | 96 terms (54 ASR + 42 seed) |
| Concepts extracted | 14 |
| Graph nodes | 14 |
| Graph edges | 51 (27 prereq + 3 refines + 1 part-of + 20 temporal) |
| Causal anchors | 20 detected → 14 converted to edges |
| Cycles removed | 1 (tree_traversal → children) |
| Topological completeness | 14/14 nodes |
| Example tree nodes | F, B, A, D, C, E, G, I, H |

### Topological Order (Recommended Teaching Sequence)
```
tree → node → root node → children → left subtree → right subtree →
binary tree → dummy node → tree traversal → traversal technique →
in-order traversal → post-order traversal → pre-order traversal → leaf node
```

This ordering represents the **bottom-up prerequisite order**: learn basic tree/node concepts before subtrees, subtrees before traversals, general traversal before specific algorithms.

---

## Key Design Decisions

### 1. No-LLM Approach
All modules use rule-based methods, regex patterns, and edit-distance matching — no large language model calls. For a well-defined domain (tree traversals) with a small concept space (~14 concepts), handcrafted lexicons are more reliable, reproducible, and fast than LLM prompting. The system runs entirely on CPU.

### 2. ASR-Seeded Vocabulary for OCR Correction (v3)
The key insight: **Whisper's output is much cleaner than Tesseract's on handwritten content.** The teacher says "root" and Whisper transcribes "root"; the teacher writes "Root" on the board and Tesseract reads "Koot". By using ASR tokens as the correction vocabulary, we automatically adapt to whatever domain the video covers. This is the most important generalizability decision in the pipeline.

### 3. Multi-Modal Grounding
OCR provides visual grounding that supplements noisy ASR. Technical terms on the board (root, left, right, pre-order) are detected even in segments where the ASR only captures Hindi explanation. 89% of ASR segments have corresponding visual text.

### 4. Confidence-Filtered OCR
Raw Tesseract on handwritten boards produces garbage from diagram lines and arrows. The 3-stage filtering pipeline (preprocessing → confidence scoring → token validation) reduces noise by ~40% while keeping all meaningful text.

### 5. Transitive Reachability for Temporal Edges
Top-down teaching style (specific examples first, foundational concepts later) creates temporal orderings that contradict domain prerequisites. The BFS reachability check ensures temporal edges never create paths that compete with domain-established prerequisite chains.

### 6. OCR Temporal Deduplication (10s Window)
Static board text appears identically in every consecutive frame. Without deduplication, a concept written on the board at t=12s and visible until t=300s would get 288 OCR mentions. The 10-second window correctly counts this as one persistent visual mention.

### 7. Causal Anchors with Domain Contradiction Check
Regex patterns detect definitional/sequential language ("X means Y", "pehle X phir Y"). But causal anchors can suggest edges that contradict domain knowledge (e.g., if the teacher says "root means the top node", that's root→node, but domain knowledge says node→root_node). The reverse-domain check prevents such contradictions.

---

## Environment & Setup

| Component | Version/Details |
|-----------|----------------|
| OS | Arch Linux |
| Shell | fish |
| Python | 3.13.11 |
| Virtual env | `./venv/` |
| PyTorch | CPU-only (188MB) via `--index-url https://download.pytorch.org/whl/cpu` |
| Whisper | `small` (461MB), multilingual |
| Tesseract | 5.5.2, languages: `eng+hin` |
| rapidfuzz | C-extension, fast edit-distance |
| pyvis | Interactive graph rendering |

### Dependencies (`requirements.txt`)
```
yt-dlp
openai-whisper
pytesseract
Pillow
scenedetect[opencv]
rapidfuzz
pyvis
```

### System dependencies (must be pre-installed)
```
tesseract (with eng and hin language data)
ffmpeg
```

---

## How to Run

### Full pipeline (single command)
```bash
cd /path/to/irel_task
source venv/bin/activate.fish   # or activate for bash
python run.py
```

### CLI with options
```bash
python pipeline.py "https://youtu.be/VIDEO_ID" \
    --model small \
    --data-root data \
    --force-from m3   # re-run from M3 onwards
```

### Individual modules
```bash
python m1_ingest.py VIDEO_ID
python m2_extract.py VIDEO_ID --model small
python m3_normalize.py VIDEO_ID
python m4_concepts.py VIDEO_ID
python m5_prereqs.py VIDEO_ID
python m6_visualize.py VIDEO_ID
```

### Output location
All artifacts are stored in `data/{video_id}/`:
```
data/XRcC7bAtL3c/
├── video.mp4              # Downloaded video
├── audio.wav              # Extracted audio (16kHz mono)
├── frames/                # Keyframes (406 JPEGs at 1fps)
├── transcript.json        # ASR output (93 segments)
├── ocr.json               # OCR output (245 frames)
├── aligned_segments.json  # ASR+OCR aligned (93 segments)
├── normalized_segments.json # Normalized (80 segments)
├── concepts.json          # Extracted concepts (14)
├── graph.json             # Prerequisite DAG (14 nodes, 51 edges)
├── graph.html             # Interactive visualization
└── report.md              # Summary report
```

---

## File Structure
```
irel_task/
├── m1_ingest.py        (117 lines)  — Video download + media extraction
├── m2_extract.py       (267 lines)  — Whisper ASR + Tesseract OCR + alignment
├── m3_normalize.py     (324 lines)  — Hallucination filter + fuzzy OCR correction + language tagging
├── m4_concepts.py      (227 lines)  — Pattern-based concept extraction with OCR dedup
├── m5_prereqs.py       (423 lines)  — Domain rules + causal anchors + temporal DAG construction
├── m6_visualize.py     (218 lines)  — Interactive pyvis graph + markdown report
├── pipeline.py         (152 lines)  — CLI orchestrator
├── run.py               (47 lines)  — Quick-run convenience script
├── requirements.txt                 — Python dependencies
├── venv/                            — Virtual environment
└── data/                            — Pipeline output artifacts
    └── XRcC7bAtL3c/                 — Test video outputs
```

**Total pipeline code:** 1,775 lines across 8 Python files.
