"""
module 3 - linguistic normalization (v3)

takes aligned_segments.json (raw ASR + OCR) and produces normalized_segments.json.

v3 — GENERALIZABLE CORRECTION APPROACH:
  instead of a hardcoded OCR correction map (video-specific), we now:
  1. build a domain vocabulary automatically from the ASR transcript
     (whisper output is much cleaner than tesseract on handwritten text)
  2. use rapidfuzz (edit-distance) to fuzzy-match noisy OCR tokens against
     the ASR-derived vocabulary
  3. only a tiny override map remains for truly extreme OCR garbling

  this means: for a NEW video, the pipeline adapts automatically —
  the ASR transcript seeds the vocabulary, and fuzzy matching handles
  novel OCR errors without needing manual correction entries.

pipeline:
  1. hallucination filter (whisper garbage)
  2. build_vocabulary() — extract domain vocab from ASR transcript
  3. fuzzy OCR correction against that vocabulary
  4. noise filtering (devanagari digits, parenthesized fragments, etc.)
  5. script-based language tagging
  6. visual grounding (clean OCR keywords per segment)
"""

import json
import re
from pathlib import Path
from collections import Counter
from rapidfuzz import fuzz, process


# ------------------------------------------------------------------
# vocabulary builder (auto-seeded from ASR)
# ------------------------------------------------------------------

# small set of universal CS/lecture terms — always in the vocab regardless
# of what the ASR transcript contains
_SEED_VOCAB = {
    # general CS / data structures
    "tree", "node", "root", "leaf", "left", "right", "child", "children",
    "parent", "binary", "graph", "vertex", "edge", "traversal", "order",
    "preorder", "inorder", "postorder", "pre-order", "in-order", "post-order",
    "algorithm", "recursive", "stack", "queue", "array", "list", "element",
    "pointer", "data", "structure", "technique", "dummy", "depth", "height",
    "subtree", "branch", "level", "search", "sort", "insert", "delete",
    # BFS / DFS / graph
    "breadth", "first", "visited", "adjacency", "matrix", "connected",
    "component", "shortest", "path", "directed", "undirected", "weighted",
    "unweighted", "cycle", "acyclic", "neighbor", "degree", "source",
    "destination", "explore", "frontier", "enqueue", "dequeue", "push", "pop",
}

# tiny override map — only for OCR garbling SO extreme that fuzzy matching
# can't bridge the gap (edit distance > 60% of word length)
_OVERRIDE_CORRECTIONS = {
    "phqohjhl": "preorder",
    "npqohjjul": "preorder",
    "pnqohjul": "preorder",
}

_MIN_FUZZY_SCORE = 65  # minimum rapidfuzz score to accept a correction
_MIN_TOKEN_LEN = 3     # don't try to correct very short tokens


def build_vocabulary(transcript_path: str) -> set:
    """
    build a domain vocabulary from the ASR transcript.
    extract all english tokens that appear 2+ times — these are
    reliable domain terms the teacher keeps repeating.
    supplement with _SEED_VOCAB for common CS terms.
    """
    with open(transcript_path) as f:
        segments = json.load(f)

    word_counts = Counter()
    for seg in segments:
        for word in seg["text"].lower().split():
            clean = word.strip(".,!?()-\"'")
            # only ascii / latin tokens
            if clean and all(c.isascii() for c in clean) and len(clean) >= _MIN_TOKEN_LEN:
                word_counts[clean] += 1

    # keep words that appear at least twice (not one-off noise)
    asr_vocab = {w for w, c in word_counts.items() if c >= 2 and len(w) >= _MIN_TOKEN_LEN}

    # merge with seed vocab
    vocab = asr_vocab | _SEED_VOCAB

    return vocab


def fuzzy_correct_token(token: str, vocabulary: set) -> str:
    """
    correct an OCR token by fuzzy-matching against the vocabulary.

    strategy:
      1. exact match? return as-is
      2. override map? return override
      3. rapidfuzz best match with score >= _MIN_FUZZY_SCORE? return match
      4. otherwise return token unchanged
    """
    key = token.lower().strip(".,!?()-")

    if not key or len(key) < _MIN_TOKEN_LEN:
        return token

    # exact match in vocab — already correct
    if key in vocabulary:
        return key

    # extreme garbling override
    if key in _OVERRIDE_CORRECTIONS:
        return _OVERRIDE_CORRECTIONS[key]

    # fuzzy match
    result = process.extractOne(
        key,
        vocabulary,
        scorer=fuzz.ratio,
        score_cutoff=_MIN_FUZZY_SCORE,
    )
    if result:
        match, score, _ = result
        return match

    return token


# ------------------------------------------------------------------
# hallucination detection
# ------------------------------------------------------------------

_HALLUCINATION_WORDS = {"labour", "work", "yeah", "hmm", "uh", "oh", "ah"}


def is_hallucination(text: str) -> bool:
    """detect whisper hallucinations."""
    words = text.lower().split()
    if not words:
        return True
    if len(words) <= 2:
        if all(w.strip(".,!?") in _HALLUCINATION_WORDS for w in words):
            return True
    if len(words) >= 3:
        top_word, top_count = Counter(words).most_common(1)[0]
        if top_count / len(words) > 0.6 and top_word in _HALLUCINATION_WORDS:
            return True
    # foreign script injection (korean, german extended latin)
    foreign_chars = len(re.findall(r'[\u0100-\u024F\u1100-\u11FF\uAC00-\uD7FF]', text))
    if foreign_chars > 3:
        return True
    # very short with no real content
    real_words = re.findall(r'[a-zA-Z\u0900-\u097F]{3,}', text)
    if len(real_words) == 0 and len(text) < 20:
        return True
    return False


# ------------------------------------------------------------------
# language detection
# ------------------------------------------------------------------

def detect_language(token: str) -> str:
    """simple script-based language detection for a single token."""
    devanagari = len(re.findall(r'[\u0900-\u097F]', token))
    latin = len(re.findall(r'[a-zA-Z]', token))
    if devanagari > 0 and latin == 0:
        return "hi"
    if latin > 0 and devanagari == 0:
        return "en"
    if devanagari > 0 and latin > 0:
        return "mixed"
    return "other"


# ------------------------------------------------------------------
# OCR noise filtering
# ------------------------------------------------------------------

def _is_ocr_noise(token: str) -> bool:
    """check if a token is OCR noise that should be filtered."""
    key = token.lower().strip(".,!?()-")

    # starts with parenthesis/bracket
    if token.startswith("(") or token.startswith(")"):
        return True

    # pure ASCII digits
    if re.match(r'^\d+$', key):
        return True

    # contains Devanagari digits (U+0966-U+096F) — OCR misreads of diagram lines
    if re.search(r'[\u0966-\u096F]', key):
        return True

    # very short Hindi fragments (common OCR noise on boards)
    if len(key) <= 2 and re.search(r'[\u0900-\u097F]', key):
        return True

    # mostly non-alphanumeric (symbols, diagram artifacts)
    alnum = len(re.findall(r'[a-zA-Z0-9\u0900-\u097F]', key))
    if len(key) > 0 and alnum / len(key) < 0.5:
        return True

    # very short tokens that aren't single uppercase letters (node labels)
    if len(key) < 3 and not (len(key) == 1 and key.isupper()):
        return True

    return False


def extract_ocr_keywords(visual_text: str, vocabulary: set) -> list:
    """extract meaningful keywords from visual_text after correction and filtering."""
    if not visual_text:
        return []
    tokens = visual_text.split()
    keywords = []
    seen = set()
    for tok in tokens:
        # apply noise filter BEFORE correction (skip obvious garbage)
        if _is_ocr_noise(tok):
            continue

        corrected = fuzzy_correct_token(tok, vocabulary)
        key = corrected.lower().strip(".,!?()-")

        if key in seen or not key:
            continue

        # post-correction noise check (corrected token might still be noise)
        if _is_ocr_noise(corrected):
            continue

        seen.add(key)
        keywords.append(corrected)
    return keywords


# ------------------------------------------------------------------
# main normalization
# ------------------------------------------------------------------

def normalize_segment(seg: dict, vocabulary: set) -> dict | None:
    """normalize a single aligned segment."""
    spoken = seg["spoken_text"]
    visual = seg.get("visual_text", "")

    if is_hallucination(spoken):
        return None

    spoken_tokens = spoken.split()
    tagged = []
    for tok in spoken_tokens:
        lang = detect_language(tok)
        tagged.append({"token": tok, "lang": lang})

    ocr_keywords = extract_ocr_keywords(visual, vocabulary)

    lang_counts = Counter(t["lang"] for t in tagged)
    if lang_counts.get("hi", 0) > lang_counts.get("en", 0):
        dominant_lang = "hi"
    elif lang_counts.get("en", 0) > 0:
        dominant_lang = "en"
    else:
        dominant_lang = "mixed"

    return {
        "start": seg["start"],
        "end": seg["end"],
        "spoken_text": spoken,
        "spoken_tokens": tagged,
        "dominant_lang": dominant_lang,
        "ocr_keywords": ocr_keywords,
        "visual_text_raw": visual,
    }


def run(video_id: str, data_root: str = "data") -> list:
    out_dir = Path(data_root) / video_id
    aligned_path = out_dir / "aligned_segments.json"
    transcript_path = out_dir / "transcript.json"
    normalized_path = out_dir / "normalized_segments.json"

    if normalized_path.exists():
        print(f"[m3] normalized_segments already exists, loading: {normalized_path}")
        with open(normalized_path) as f:
            return json.load(f)

    # --- build vocabulary from ASR transcript ---
    vocabulary = build_vocabulary(str(transcript_path))
    print(f"[m3] built vocabulary: {len(vocabulary)} terms ({len(vocabulary) - len(_SEED_VOCAB)} from ASR, {len(_SEED_VOCAB)} seed)")

    with open(aligned_path) as f:
        aligned = json.load(f)

    print(f"[m3] normalizing {len(aligned)} segments")

    normalized = []
    dropped = 0
    for seg in aligned:
        result = normalize_segment(seg, vocabulary)
        if result is None:
            dropped += 1
            continue
        normalized.append(result)

    with open(normalized_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    en_segs = sum(1 for s in normalized if s["dominant_lang"] == "en")
    hi_segs = sum(1 for s in normalized if s["dominant_lang"] == "hi")
    with_ocr = sum(1 for s in normalized if s["ocr_keywords"])

    print(f"[m3] kept {len(normalized)} segments, dropped {dropped} hallucinations")
    print(f"[m3] language breakdown: en={en_segs}, hi={hi_segs}, mixed={len(normalized)-en_segs-hi_segs}")
    print(f"[m3] segments with OCR keywords: {with_ocr}")
    print(f"[m3] -> {normalized_path}")

    return normalized


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--data-root", default="data")
    args = parser.parse_args()
    run(args.video_id, args.data_root)
