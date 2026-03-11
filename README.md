# iREL Recruitment Task 2026
## Code-Mixed Pedagogical Flow Extractor

**Author:** Aytida V A  
**Date:** March 2026  

---

## Table of Contents
1. [Problem Statement](#problem-statement)
2. [Approach 1 — Rule-Based Pipeline](#approach-1--rule-based-pipeline)
   - [Architecture Overview](#architecture-overview)
   - [Module Descriptions](#module-descriptions)
   - [Version History & Major Changes](#version-history--major-changes)
   - [Pipeline Results](#pipeline-results)
   - [Key Design Decisions](#key-design-decisions)
3. [Environment & Setup](#environment--setup)
4. [How to Run](#how-to-run)

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

## Approach 1 — Rule-Based Pipeline

> This approach uses **no LLMs** — only rule-based methods, regex patterns, domain lexicons,
> and edit-distance matching. It is fast, reproducible, and runs entirely on CPU.
> For a list of all hardcoded / domain-specific elements, see [`HARDCODED.md`](HARDCODED.md).

### Architecture Overview

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

### Module Descriptions

#### Module 1: Data Ingestion (`m1_ingest.py`)

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

---

#### Module 2: Multi-Modal Content Extraction (`m2_extract.py`)

**Purpose:** Convert raw audio and images into timestamped, aligned text segments.

**What it does:**
1. **ASR (Whisper):** Transcribes audio using OpenAI's Whisper `small` multilingual model. Produces timestamped segments with start/end times. Whisper handles Hindi+English code-mixing well.
2. **OCR (Tesseract):** Processes each keyframe through a 3-stage pipeline:
   - **Preprocessing:** Grayscale → 2x bicubic upscale → adaptive Gaussian threshold
   - **Confidence filtering:** Uses `image_to_data()` with conf ≥ 50
   - **Token validation:** Regex filter requires ≥ 2 alphanumeric characters
3. **Alignment:** Maps OCR frames to ASR segments by matching frame timestamps to ASR time ranges.

**Evolution:**
| Version | Approach | Result |
|---------|----------|--------|
| v1 | Raw Tesseract | Garbled — arrows read as symbols |
| v2 | + preprocessing (threshold, upscale) | Hindi detected but diagram garbage persists |
| v3 | + confidence filter (conf≥50, regex) | Clean domain terms |

---

#### Module 3: Linguistic Normalization (`m3_normalize.py`)

**Purpose:** Clean and normalize the raw ASR+OCR text into structured, language-tagged segments.

**What it does:**
1. **Hallucination filter:** Detects Whisper hallucinations — repeated filler words, foreign script injection
2. **Vocabulary building (v3):** Constructs domain vocabulary from ASR transcript automatically
3. **Fuzzy OCR correction (v3):** Uses `rapidfuzz` edit-distance to match noisy OCR tokens against auto-built vocabulary
4. **OCR noise filtering:** Removes Devanagari digit noise, parenthesized fragments, symbol artifacts
5. **Language tagging:** Script-based per-token language detection (Devanagari → `hi`, Latin → `en`)

**Major design change — v2 → v3:**
In v2, OCR correction used a hardcoded 30+ entry map specific to one video's handwriting. In v3, the ASR transcript seeds the vocabulary and fuzzy matching handles novel OCR errors automatically.

**Hardcoded elements:** `_SEED_VOCAB` (67 CS terms), `_OVERRIDE_CORRECTIONS` (3 entries) — see [HARDCODED.md](HARDCODED.md)

---

#### Module 4: Concept Extraction (`m4_concepts.py`)

**Purpose:** Identify distinct pedagogical concepts from the normalized segments.

**What it does:**
1. **Pattern-based extraction:** A lexicon of concept patterns (regex) scans spoken text and OCR keywords
2. **Cross-modal enrichment:** OCR keywords mapped to concepts via `_OCR_KEYWORD_CONCEPTS`
3. **Source tracking:** Each mention tagged as `asr`, `ocr`, or `asr+ocr`
4. **OCR temporal dedup (10s window):** Prevents static board text from inflating counts

**Hardcoded elements:** `_CONCEPT_PATTERNS` (26 concepts), `_OCR_KEYWORD_CONCEPTS` (18 entries) — see [HARDCODED.md](HARDCODED.md)

---

#### Module 5: Prerequisite Mapping (`m5_prereqs.py`)

**Purpose:** Build a prerequisite dependency graph (DAG) from domain knowledge, causal language, and temporal ordering.

**What it does:**
1. **Domain rules:** Handcrafted prerequisite relationships based on CS domain knowledge
2. **Causal anchor detection:** Regex patterns detect definitional/sequential language in transcript
3. **Temporal edges:** Conservative temporal ordering with transitive reachability check (BFS)
4. **DAG verification:** Kahn's algorithm + cycle-breaking by removing lowest-confidence edges

**Key insight — transitive reachability:**
Top-down teaching style (specific examples first, foundations later) creates temporal orderings that contradict domain prerequisites. BFS reachability check ensures temporal edges never create competing paths.

**Hardcoded elements:** `_DOMAIN_RULES` (38 rules), `_CONCEPT_FRAGMENTS` (30 entries) — see [HARDCODED.md](HARDCODED.md)

---

#### Module 6: Visualization (`m6_visualize.py`)

**Purpose:** Interactive graph visualization + summary report.

**What it does:**
1. **Interactive graph (`graph.html`):** `pyvis` force-directed DAG with color-coded edges and sized nodes
2. **Summary report (`report.md`):** Markdown with statistics, concept table, topological order

---

#### Module 7: Orchestration (`pipeline.py` + `run.py`)

**Purpose:** Unified CLI entry point.

**Features:**
- Runs M1→M6 sequentially with caching
- `--force-from <stage>` to re-run from a specific module
- `--model <name>` to select Whisper model
- `--data-root <path>` to change output directory

---

### Version History & Major Changes

#### v1 — Initial Implementation
- All 7 modules built and connected
- **Problems:** OCR noise, inflated mention counts, 45 temporal edges causing cycles (3/14 topo order)

#### v2 — Quality Fixes
- **M3:** OCR noise filters + hardcoded correction map (30+ entries)
- **M4:** 10-second temporal dedup window for OCR mentions
- **M5:** Three iterations of cycle fixes → transitive reachability check (BFS) → 14/14 topo order
- **M6+M7:** Built from scratch

#### v3 — Generalization (Current)
- **M3 rewrite:** Replaced hardcoded OCR correction map with ASR-seeded vocabulary + `rapidfuzz` fuzzy matching
- **M4+M5 extended:** Added BFS/DFS/graph domain patterns and rules for second test video
- Zero video-specific hardcoding in the correction logic; domain patterns remain hardcoded

---

### Pipeline Results

#### Video 1: `XRcC7bAtL3c` — Tree Traversal Techniques
| Metric | Value |
|--------|-------|
| Concepts extracted | 14 |
| Graph edges | 51 (27 prereq + 3 refines + 1 part-of + 20 temporal) |
| Topological completeness | 14/14 |
| Language split | en=70, hi=10 |

**Topological order:** tree → node → root node → children → left subtree → right subtree → binary tree → dummy node → tree traversal → traversal technique → in-order → post-order → pre-order → leaf node

#### Video 2: `N2P7w22tN9c` — BFS/DFS Graph Traversal
| Metric | Value |
|--------|-------|
| Concepts extracted | 12 |
| Graph edges | 41 |
| Topological completeness | 12/12 |

#### Videos 3-5 (Generalizability Test — No New Patterns Added)

These videos were run with the existing rule set (tree + BFS/DFS patterns) to test how the pipeline handles unseen topics:

| Video ID | Language | Segments | Concepts | Edges | Notes |
|----------|----------|----------|----------|-------|-------|
| `Tp37HXfekNo` | Hindi | 120 | 0 | 0 | Topic outside pattern set; OCR: 11/691 frames useful |
| `azXr6nTaD9M` | Hindi | 138 | 1 (stack) | 0 | Only matched 'stack' from seed vocab |
| `eXWl-Uor75o` | Telugu | 34 | 1 (right subtree) | 0 | Telugu lecture; OCR-only match |

**Key observations:**
- M1-M3 (ingestion, extraction, normalization) work well regardless of topic — they are domain-agnostic
- M4-M5 (concept extraction, prerequisite mapping) produce near-empty results because the hardcoded pattern/rule sets only cover tree traversals and BFS/DFS
- This confirms the need for a generalized approach (see [HARDCODED.md](HARDCODED.md))

---

### Key Design Decisions

1. **No-LLM Approach:** All modules use rule-based methods, regex, and edit-distance. Fast, reproducible, CPU-only.
2. **ASR-Seeded Vocabulary:** Whisper output seeds the OCR correction vocabulary — automatically adapts to any video's domain.
3. **Multi-Modal Grounding:** OCR supplements noisy ASR; technical terms on board detected even when ASR only captures Hindi.
4. **Confidence-Filtered OCR:** 3-stage pipeline (preprocessing → confidence → validation) reduces noise ~40%.
5. **Transitive Reachability:** BFS check prevents temporal edges from contradicting domain prerequisites.
6. **OCR Temporal Dedup:** 10s window prevents static board text from inflating mention counts.
7. **Causal Anchors with Domain Check:** Regex-detected causal language converted to edges only if consistent with domain rules.

---

## Environment & Setup

| Component | Version/Details |
|-----------|----------------|
| OS | Arch Linux |
| Python | 3.13.11 |
| PyTorch | CPU-only |
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

### System dependencies
```
tesseract (with eng and hin language data)
ffmpeg
```

---

## How to Run

### Full pipeline
```bash
cd irel_task
source venv/bin/activate.fish   # or activate for bash
python pipeline.py "https://youtu.be/VIDEO_ID"
```

### With options
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

### Output structure
```
data/{video_id}/
├── video.mp4                  # Downloaded video
├── audio.wav                  # Extracted audio (16kHz mono)
├── frames/                    # Keyframes (1fps JPEGs)
├── transcript.json            # ASR output
├── ocr.json                   # OCR output
├── aligned_segments.json      # ASR+OCR aligned
├── normalized_segments.json   # Normalized segments
├── concepts.json              # Extracted concepts
├── graph.json                 # Prerequisite DAG
├── graph.html                 # Interactive visualization
└── report.md                  # Summary report
```

---

## File Structure
```
irel_task/
├── m1_ingest.py         — Video download + media extraction
├── m2_extract.py        — Whisper ASR + Tesseract OCR + alignment
├── m3_normalize.py      — Hallucination filter + fuzzy OCR correction + language tagging
├── m4_concepts.py       — Pattern-based concept extraction with OCR dedup
├── m5_prereqs.py        — Domain rules + causal anchors + temporal DAG
├── m6_visualize.py      — Interactive pyvis graph + markdown report
├── pipeline.py          — CLI orchestrator
├── run.py               — Quick-run convenience script
├── batch_run.py         — Batch runner for multiple videos
├── requirements.txt     — Python dependencies
├── README.md            — This document
├── HARDCODED.md         — Per-video hardcoded elements inventory
├── venv/                — Virtual environment
└── data/                — Pipeline output artifacts
    ├── XRcC7bAtL3c/     — Video 1: Tree Traversal
    ├── N2P7w22tN9c/     — Video 2: BFS/DFS
    ├── Tp37HXfekNo/     — Video 3
    ├── azXr6nTaD9M/     — Video 4
    └── eXWl-Uor75o/     — Video 5
```
