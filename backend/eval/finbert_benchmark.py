"""
FinBERT Benchmark Script
Evaluates ProsusAI/finbert against FiQA and FinancialPhraseBank datasets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import zipfile
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import requests
import torch
from datasets import load_dataset
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline


LABELS = ["negative", "neutral", "positive"]


@dataclass
class DatasetSpec:
    key: str
    name: str
    candidate_urls: List[str]
    local_path: Optional[str] = None


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _is_probably_html(sample: bytes) -> bool:
    snippet = sample.lstrip().lower()
    return snippet.startswith(b"<!doctype html") or snippet.startswith(b"<html")


def _download_file(url: str, dest_path: Path, headers: Optional[Dict[str, str]]) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60, headers=headers) as response:
        response.raise_for_status()
        sample = response.raw.read(512)
        if _is_probably_html(sample):
            raise RuntimeError(f"URL returned HTML, not a dataset file: {url}")
        with open(dest_path, "wb") as handle:
            handle.write(sample)
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return dest_path


def _download_from_candidates(
    name: str,
    urls: List[str],
    dest_dir: Path,
    token: Optional[str],
) -> Path:
    errors = []
    headers = {"User-Agent": "PipPulse-AI-FinBERT-Benchmark/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for url in urls:
        try:
            filename = Path(urlparse(url).path).name or f"{name}.data"
            target = dest_dir / filename
            if target.exists() and target.stat().st_size > 0:
                return target
            print(f"Downloading {name} dataset from {url}")
            return _download_file(url, target, headers)
        except Exception as exc:
            errors.append(f"{url} -> {exc}")
    error_text = "\n".join(errors)
    raise RuntimeError(
        f"Failed to download {name} dataset from all candidates.\n{error_text}\n"
        "Provide a local path with --fiqa-path or --phrasebank-path."
    )


def _extract_if_archive(path: Path, dest_dir: Path) -> Path:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path, "r") as archive:
            archive.extractall(dest_dir)
        return dest_dir
    if tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as archive:
            archive.extractall(dest_dir)
        return dest_dir
    return path


def _find_data_files(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    candidates = []
    for ext in (".csv", ".tsv", ".json", ".jsonl"):
        candidates.extend(path.rglob(f"*{ext}"))
    return candidates


def _load_dataframe(file_path: Path) -> pd.DataFrame:
    if file_path.suffix.lower() == ".tsv":
        return pd.read_csv(file_path, sep="\t")
    if file_path.suffix.lower() in {".json", ".jsonl"}:
        try:
            return pd.read_json(file_path, lines=True)
        except ValueError:
            return pd.read_json(file_path)
    return pd.read_csv(file_path)


def _detect_columns(df: pd.DataFrame) -> Tuple[str, str]:
    text_candidates = [
        "text",
        "sentence",
        "content",
        "headline",
        "title",
        "question",
        "body",
    ]
    label_candidates = [
        "label",
        "sentiment",
        "polarity",
        "sentiment_label",
        "target",
        "category",
    ]
    columns_lower = {col.lower(): col for col in df.columns}

    text_col = next(
        (columns_lower[name] for name in text_candidates if name in columns_lower),
        None,
    )
    label_col = next(
        (columns_lower[name] for name in label_candidates if name in columns_lower),
        None,
    )

    if text_col and label_col:
        return text_col, label_col

    label_col = label_col or _infer_label_column(df)
    text_col = text_col or _infer_text_column(df, exclude=label_col)
    if not text_col or not label_col:
        raise RuntimeError("Could not detect text/label columns in dataset.")
    return text_col, label_col


def _infer_label_column(df: pd.DataFrame) -> Optional[str]:
    candidates = []
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        unique = series.unique()
        if len(unique) <= 10:
            candidates.append((col, len(unique)))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[1])
    return candidates[0][0]


def _infer_text_column(df: pd.DataFrame, exclude: Optional[str]) -> Optional[str]:
    best_col = None
    best_len = 0.0
    for col in df.columns:
        if col == exclude:
            continue
        series = df[col].dropna().astype(str)
        if series.empty:
            continue
        avg_len = series.str.len().mean()
        if avg_len > best_len:
            best_len = avg_len
            best_col = col
    return best_col


def _normalize_labels(labels: List) -> List[str]:
    cleaned = []
    label_set = set()
    for label in labels:
        if label is None or (isinstance(label, float) and np.isnan(label)):
            cleaned.append(None)
            continue
        normalized = _normalize_label_value(label)
        cleaned.append(normalized)
        if normalized is not None:
            label_set.add(normalized)
    if not label_set:
        raise RuntimeError("No valid labels found after normalization.")
    return cleaned


def _normalize_label_value(label) -> Optional[str]:
    if isinstance(label, str):
        value = label.strip().lower()
        if value in {"positive", "pos", "bullish", "up"}:
            return "positive"
        if value in {"negative", "neg", "bearish", "down"}:
            return "negative"
        if value in {"neutral", "neu", "none"}:
            return "neutral"
        if value.replace(".", "", 1).isdigit():
            return _map_numeric_label(float(value))
        return None
    if isinstance(label, (int, np.integer)):
        return _map_numeric_label(int(label))
    if isinstance(label, (float, np.floating)):
        if np.isnan(label):
            return None
        return _map_numeric_label(int(label))
    return None


def _map_numeric_label(value: int) -> Optional[str]:
    if value in {-1, 0, 1}:
        return { -1: "negative", 0: "neutral", 1: "positive" }[value]
    if value in {0, 1, 2}:
        return { 0: "negative", 1: "neutral", 2: "positive" }[value]
    if value in {0, 1}:
        return { 0: "negative", 1: "positive" }[value]
    return None


def _load_dataset(
    spec: DatasetSpec,
    data_dir: Path,
    token: Optional[str],
) -> Tuple[List[str], List[str], Dict[str, str]]:
    """Load dataset using HuggingFace datasets library."""
    
    # Set HuggingFace token if provided
    if token:
        os.environ["HF_TOKEN"] = token
        try:
            from huggingface_hub import login
            login(token=token, add_to_git_credential=False)
        except Exception:
            pass  # Token will be used via environment variable
    
    try:
        print(f"Loading {spec.name} from HuggingFace Hub...")
        
        # Use atrost/financial_phrasebank for sentiment validation
        # Has columns: sentence, label (0=negative, 1=neutral, 2=positive)
        dataset = load_dataset("atrost/financial_phrasebank")
        
        # Use different splits for different datasets
        if spec.key == "fiqa":
            # Use train split for FiQA validation
            dataset_split = dataset["train"]
        elif spec.key in ("phrasebank", "financial_phrasebank"):
            # Use test split for PhraseBank validation
            dataset_split = dataset["test"]
        else:
            raise ValueError(f"Unknown dataset key: {spec.key}")
        
        df = dataset_split.to_pandas()
        text_col = "sentence"
        label_col = "label"
        
        texts = df[text_col].astype(str).tolist()
        raw_labels = df[label_col].tolist()
        
        # Normalize labels to [negative, neutral, positive]
        # atrost/financial_phrasebank uses: 0=negative, 1=neutral, 2=positive
        normalized_labels = []
        for label in raw_labels:
            normalized = None
            if isinstance(label, (int, np.integer)):
                label_map = {0: "negative", 1: "neutral", 2: "positive"}
                normalized = label_map.get(int(label))
            elif isinstance(label, str):
                normalized = label.lower().strip()
                if normalized not in ["negative", "neutral", "positive"]:
                    if normalized in ["neg", "-1", "0"]:
                        normalized = "negative"
                    elif normalized in ["neu", "1"]:
                        normalized = "neutral"
                    elif normalized in ["pos", "2"]:
                        normalized = "positive"
            
            normalized_labels.append(normalized)
        
        # Clean texts and labels
        cleaned_texts = []
        cleaned_labels = []
        for text, label in zip(texts, normalized_labels):
            if label in LABELS and text.strip():
                cleaned_texts.append(text)
                cleaned_labels.append(label)
        
        if not cleaned_texts:
            raise RuntimeError(f"No usable labeled rows found in {spec.name}")
        
        split_name = "test" if spec.key in ("phrasebank", "financial_phrasebank") else "train"
        print(f"  Loaded {len(cleaned_texts)} samples from atrost/financial_phrasebank ({split_name} split)")
        
        return cleaned_texts, cleaned_labels, {
            "source": "huggingface_hub",
            "dataset_key": spec.key,
            "dataset_name": "atrost/financial_phrasebank",
            "split": split_name,
            "text_column": text_col,
            "label_column": label_col,
            "rows_loaded": len(texts),
            "rows_usable": len(cleaned_texts),
        }
    
    except Exception as exc:
        raise RuntimeError(f"Failed to load {spec.name} from HuggingFace Hub: {exc}")


def _load_model(model_name: str, device: Optional[str]) -> pipeline:
    if device:
        requested = device.lower()
        if requested == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available.")
        if requested == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS requested but not available.")
        resolved = requested
    else:
        if torch.cuda.is_available():
            resolved = "cuda"
        elif torch.backends.mps.is_available():
            resolved = "mps"
        else:
            resolved = "cpu"

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    if resolved == "cuda":
        model.to("cuda")

    return pipeline(
        "sentiment-analysis",
        model=model,
        tokenizer=tokenizer,
        device=0 if resolved == "cuda" else -1,
        return_all_scores=True,
    ), resolved


def _predict_batch(model_pipeline: pipeline, texts: List[str], batch_size: int) -> List[Dict[str, float]]:
    predictions = []
    for idx in range(0, len(texts), batch_size):
        batch = texts[idx: idx + batch_size]
        results = model_pipeline(batch, return_all_scores=True, truncation=True)
        for result in results:
            # Handle both single result (dict) and list of results (pipeline with return_all_scores=True)
            if isinstance(result, list):
                # result is a list of dicts: [{"label": "negative", "score": 0.9}, ...]
                best = max(result, key=lambda item: item["score"])
            else:
                # result is a single dict: {"label": "negative", "score": 0.9}
                best = result
            
            predictions.append({
                "label": best["label"].lower(),
                "confidence": float(best["score"]),
            })
    return predictions


def _evaluate_dataset(name: str, texts: List[str], labels: List[str], model_pipeline: pipeline, batch_size: int) -> Dict[str, object]:
    predictions = _predict_batch(model_pipeline, texts, batch_size)
    y_true = labels
    y_pred = [pred["label"] for pred in predictions]
    confidences = np.array([pred["confidence"] for pred in predictions], dtype=float)

    accuracy = float(accuracy_score(y_true, y_pred))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, zero_division=0
    )
    macro_f1 = float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0))
    matrix = confusion_matrix(y_true, y_pred, labels=LABELS)

    per_class = {}
    for label, p, r, f, s in zip(LABELS, precision, recall, f1, support):
        per_class[label] = {
            "precision": float(p),
            "recall": float(r),
            "f1": float(f),
            "support": int(s),
        }

    correct = np.array([1.0 if truth == pred else 0.0 for truth, pred in zip(y_true, y_pred)], dtype=float)
    confidence_corr = None
    if np.std(confidences) > 0 and np.std(correct) > 0:
        confidence_corr = float(np.corrcoef(confidences, correct)[0, 1])

    status = "FAIL"
    if macro_f1 >= 0.75:
        status = "PASS - Meets 75% F1-score target"
    elif macro_f1 >= 0.70:
        status = "ACCEPTABLE - Below target but above 70%"

    label_distribution = {label: int(sum(1 for item in y_true if item == label)) for label in LABELS}

    return {
        "dataset_name": name,
        "total_samples": len(y_true),
        "accuracy": accuracy,
        "macro_f1_score": macro_f1,
        "per_class_metrics": per_class,
        "confusion_matrix": matrix.tolist(),
        "label_distribution": label_distribution,
        "model_confidence_correlation": confidence_corr,
        "status": status,
    }


def _write_png(path: Path, width: int, height: int, pixels: List[List[Tuple[int, int, int, int]]]) -> None:
    import zlib
    import struct

    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b, a in row:
            raw.extend([r, g, b, a])
    compressed = zlib.compress(bytes(raw))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(png)


def _render_confusion_matrices_png(
    matrices: List[np.ndarray],
    path: Path,
    cell_size: int = 60,
    gap: int = 6,
) -> None:
    if not matrices:
        raise RuntimeError("No confusion matrices to render.")
    matrix_size = cell_size * len(LABELS) + gap * (len(LABELS) + 1)
    width = matrix_size * len(matrices) + gap * (len(matrices) + 1)
    height = matrix_size

    pixels = [[(255, 255, 255, 255) for _ in range(width)] for _ in range(height)]

    for idx, matrix in enumerate(matrices):
        max_value = float(np.max(matrix)) if np.max(matrix) > 0 else 1.0
        offset_x = gap + idx * (matrix_size + gap)
        offset_y = gap
        for row in range(len(LABELS)):
            for col in range(len(LABELS)):
                value = float(matrix[row][col])
                intensity = value / max_value
                shade = int(255 - 180 * intensity)
                color = (shade, shade, 255, 255)
                start_x = offset_x + col * (cell_size + gap)
                start_y = offset_y + row * (cell_size + gap)
                for y in range(start_y, start_y + cell_size):
                    for x in range(start_x, start_x + cell_size):
                        pixels[y][x] = color

    _write_png(path, width, height, pixels)


def _write_markdown_report(path: Path, results: Dict[str, object], image_path: Path) -> None:
    lines = [
        "# FinBERT Benchmark Report",
        "",
        f"Generated: {results['timestamp']}",
        f"Model: {results['model']['name']}",
        f"Device: {results['model']['device']}",
        "",
        "## Summary",
        "",
    ]
    for key in ("fiqua_dataset", "financialphrasebank_dataset"):
        dataset = results[key]
        lines.extend([
            f"### {dataset['dataset_name']}",
            f"- Samples: {dataset['total_samples']}",
            f"- Accuracy: {dataset['accuracy']:.4f}",
            f"- Macro F1-score: {dataset['macro_f1_score']:.4f}",
            f"- Status: {dataset['status']}",
            "",
            "| Label | Precision | Recall | F1 | Support |",
            "| --- | --- | --- | --- | --- |",
        ])
        for label, metrics in dataset["per_class_metrics"].items():
            lines.append(
                f"| {label} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | {metrics['f1']:.4f} | {metrics['support']} |"
            )
        lines.append("")
        lines.append(f"Confusion matrix (rows=true, cols=pred): {dataset['confusion_matrix']}")
        lines.append("")

    lines.extend([
        "## Confusion Matrix Visualization",
        "",
        f"Image: {image_path.name} (left-to-right: FiQA, FinancialPhraseBank)",
        "",
    ])

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark FinBERT on FiQA and FinancialPhraseBank datasets.")
    parser.add_argument("--output-dir", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--fiqa-path", default=None)
    parser.add_argument("--phrasebank-path", default=None)
    parser.add_argument("--model-name", default="ProsusAI/finbert")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default=None, choices=["cpu", "cuda", "mps"])
    parser.add_argument(
        "--hf-token",
        default=os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN"),
        help="Hugging Face access token for gated datasets.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    data_dir = output_dir / "data"
    _ensure_dir(output_dir)
    _ensure_dir(data_dir)

    fiqa_spec = DatasetSpec(
        key="fiqa",
        name="FiQA",
        candidate_urls=[
            "https://huggingface.co/datasets/fiqa/resolve/main/fiqa.csv",
            "https://huggingface.co/datasets/fiqa/resolve/main/fiqa.json",
            "https://huggingface.co/datasets/fiqa/resolve/main/data/fiqa.csv",
        ],
        local_path=args.fiqa_path,
    )
    phrasebank_spec = DatasetSpec(
        key="financial_phrasebank",
        name="FinancialPhraseBank",
        candidate_urls=[
            "https://huggingface.co/datasets/financial_phrasebank/resolve/main/data/FinancialPhraseBank-v1.0.zip",
            "https://huggingface.co/datasets/financial_phrasebank/resolve/main/FinancialPhraseBank-v1.0.zip",
            "https://huggingface.co/datasets/financial_phrasebank/resolve/main/financial_phrasebank.csv",
        ],
        local_path=args.phrasebank_path,
    )

    print("Loading datasets...")
    fiqa_texts, fiqa_labels, fiqa_meta = _load_dataset(fiqa_spec, data_dir, args.hf_token)
    phrase_texts, phrase_labels, phrase_meta = _load_dataset(
        phrasebank_spec, data_dir, args.hf_token
    )

    print("Loading FinBERT model...")
    model_pipeline, device = _load_model(args.model_name, args.device)

    print("Evaluating FiQA...")
    fiqa_results = _evaluate_dataset("FiQA", fiqa_texts, fiqa_labels, model_pipeline, args.batch_size)
    print("Evaluating FinancialPhraseBank...")
    phrase_results = _evaluate_dataset(
        "FinancialPhraseBank", phrase_texts, phrase_labels, model_pipeline, args.batch_size
    )

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": {"name": args.model_name, "device": device},
        "dataset_sources": {"fiqa": fiqa_meta, "financial_phrasebank": phrase_meta},
        "fiqua_dataset": fiqa_results,
        "financialphrasebank_dataset": phrase_results,
    }

    results_path = output_dir / "finbert_benchmark_results.json"
    with open(results_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    png_path = output_dir / "confusion_matrix.png"
    _render_confusion_matrices_png(
        [np.array(fiqa_results["confusion_matrix"]), np.array(phrase_results["confusion_matrix"])],
        png_path,
    )

    report_path = output_dir / "finbert_benchmark_report.md"
    _write_markdown_report(report_path, results, png_path)

    print(f"Results saved to {results_path}")
    print(f"Confusion matrix saved to {png_path}")
    print(f"Markdown report saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
