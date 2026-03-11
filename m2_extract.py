"""
module 2 - multi-modal content extraction (v3)

runs whisper asr on audio and tesseract ocr on frames,
then aligns them by timestamp into aligned_segments.json.

v3 — confidence-filtered OCR:
  raw tesseract on handwritten boards produces garbage from diagram lines
  and arrows. the 3-stage filtering pipeline fixes this:
    1. preprocess: grayscale -> 2x bicubic upscale -> adaptive gaussian threshold
    2. confidence: image_to_data() per-word confidence scores, keep only conf >= 50
    3. validation: regex filter requires >= 2 alphabetic characters per token
"""

import os
import json
import argparse
import re
from pathlib import Path

import whisper
import pytesseract
from PIL import Image
import cv2


# ------------------------------------------------------------------
# 2a: asr via whisper
# ------------------------------------------------------------------

def run_asr(audio_path: Path, model_size: str = "small") -> list[dict]:
    """
    runs whisper on the audio file.
    returns list of segments: [{start, end, text}, ...]
    code-mixed text is preserved as-is — normalization is m3's job.
    """
    transcript_path = audio_path.parent / "transcript.json"

    if transcript_path.exists():
        print(f"[m2a] transcript already exists, loading: {transcript_path}")
        with open(transcript_path) as f:
            return json.load(f)

    print(f"[m2a] loading whisper model: {model_size}")
    model = whisper.load_model(model_size)

    print(f"[m2a] transcribing: {audio_path}")
    # task=transcribe preserves original language (no forced translation)
    result = model.transcribe(str(audio_path), task="transcribe", verbose=False)

    segments = [
        {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
        for s in result["segments"]
    ]

    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    print(f"[m2a] transcribed {len(segments)} segments -> {transcript_path}")
    return segments


# ------------------------------------------------------------------
# 2b: ocr on frames via tesseract (confidence-filtered v3)
# ------------------------------------------------------------------

# token must contain at least 2 alphabetic chars (latin or devanagari)
_VALID_TOKEN_RE = re.compile(r'[a-zA-Z\u0900-\u097F]{2,}')


def preprocess_for_ocr(img_path: Path) -> Image.Image:
    """
    preprocess a frame image for better OCR accuracy.
    pipeline: grayscale -> 2x bicubic upscale -> adaptive gaussian threshold
    this dramatically improves tesseract on handwritten board content.
    """
    img = cv2.imread(str(img_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 2x upscale helps tesseract with small handwriting
    h, w = gray.shape
    upscaled = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    # adaptive threshold handles uneven lighting on boards
    thresh = cv2.adaptiveThreshold(
        upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return Image.fromarray(thresh)


def _is_valid_token(text: str) -> bool:
    """check if a token has at least 2 alphabetic characters."""
    return bool(_VALID_TOKEN_RE.search(text))


def run_ocr(frames_dir: Path) -> list[dict]:
    """
    runs confidence-filtered tesseract OCR on every frame.
    returns list of: [{frame, timestamp_sec, text}, ...]
    only frames with meaningful text are kept.

    uses image_to_data() instead of image_to_string() to get
    per-word confidence scores. words with conf < 50 are dropped.
    """
    ocr_path = frames_dir.parent / "ocr.json"

    if ocr_path.exists():
        print(f"[m2b] ocr output already exists, loading: {ocr_path}")
        with open(ocr_path) as f:
            return json.load(f)

    frame_files = sorted(frames_dir.glob("frame_*.jpg"))
    print(f"[m2b] running confidence-filtered OCR on {len(frame_files)} frames")

    results = []
    for i, frame_file in enumerate(frame_files):
        # frame filename encodes timestamp: frame_00042.jpg -> 42 seconds
        # (since we extracted at 1fps, frame number == second)
        frame_num = int(re.search(r'frame_(\d+)', frame_file.stem).group(1))
        timestamp_sec = frame_num - 1  # ffmpeg frame numbers start at 1

        # preprocess for better OCR
        processed = preprocess_for_ocr(frame_file)

        # get per-word data with confidence scores
        data = pytesseract.image_to_data(
            processed, lang="eng+hin",
            output_type=pytesseract.Output.DICT
        )

        # filter by confidence and token validity
        words = []
        for j, conf in enumerate(data["conf"]):
            try:
                c = int(conf)
            except (ValueError, TypeError):
                continue
            if c >= 50:
                word = data["text"][j].strip()
                if word and _is_valid_token(word):
                    words.append(word)

        text = " ".join(words)
        if text:
            results.append({
                "frame": frame_file.name,
                "timestamp_sec": timestamp_sec,
                "text": text,
            })

        # progress indicator every 100 frames
        if (i + 1) % 100 == 0:
            print(f"  [m2b] processed {i + 1}/{len(frame_files)} frames...")

    with open(ocr_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[m2b] kept {len(results)}/{len(frame_files)} frames with useful text -> {ocr_path}")
    return results


# ------------------------------------------------------------------
# 2c: frame-transcript aligner
# ------------------------------------------------------------------

def align_segments(asr_segments: list[dict], ocr_results: list[dict]) -> list[dict]:
    """
    for each asr segment, find all ocr frames that fall within its time window.
    merge their text as visual_context.
    output: [{start, end, spoken_text, visual_text}, ...]
    """
    aligned = []

    for seg in asr_segments:
        start, end = seg["start"], seg["end"]

        # collect all ocr frames within this segment's time window
        visual_texts = [
            r["text"] for r in ocr_results
            if start <= r["timestamp_sec"] <= end
        ]

        aligned.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "spoken_text": seg["text"],
            "visual_text": " | ".join(visual_texts) if visual_texts else "",
        })

    return aligned


def run(video_id: str, data_root: str = "data", model_size: str = "small") -> list[dict]:
    out_dir = Path(data_root) / video_id
    audio_path = out_dir / "audio.wav"
    frames_dir = out_dir / "frames"
    aligned_path = out_dir / "aligned_segments.json"

    if aligned_path.exists():
        print(f"[m2] aligned_segments already exists, loading: {aligned_path}")
        with open(aligned_path) as f:
            return json.load(f)

    asr_segments = run_asr(audio_path, model_size=model_size)
    ocr_results = run_ocr(frames_dir)
    aligned = align_segments(asr_segments, ocr_results)

    with open(aligned_path, "w", encoding="utf-8") as f:
        json.dump(aligned, f, ensure_ascii=False, indent=2)

    print(f"\n[m2] aligned {len(aligned)} segments -> {aligned_path}")
    print(f"[m2] segments with visual context: {sum(1 for s in aligned if s['visual_text'])}")
    return aligned


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id", help="video id (subfolder name under data/)")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--model", default="small", help="whisper model size")
    args = parser.parse_args()
    run(args.video_id, args.data_root, args.model)
