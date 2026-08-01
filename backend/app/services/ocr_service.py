"""
OCR service: file bytes -> raw text.

Tesseract is the default engine (easy local setup, no GPU). PaddleOCR is
wired in as a swap-in for when accuracy on noisy scans matters more than
setup simplicity — swap OCR_ENGINE in config, nothing downstream changes,
since both paths return the same OCRResult shape.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

from app.core.config import get_settings

settings = get_settings()


@dataclass
class OCRResult:
    text: str
    mean_confidence: float  # 0-1, averaged across recognized words/pages
    page_count: int


class OCRService:
    def extract(self, file_bytes: bytes, filename: str) -> OCRResult:
        images = self._to_images(file_bytes, filename)

        if settings.OCR_ENGINE == "paddleocr":
            return self._run_paddleocr(images)
        return self._run_tesseract(images)

    # ---- helpers -----------------------------------------------------

    def _to_images(self, file_bytes: bytes, filename: str) -> list[Image.Image]:
        if filename.lower().endswith(".pdf"):
            return convert_from_bytes(file_bytes, dpi=300)
        return [Image.open(io.BytesIO(file_bytes)).convert("RGB")]

    def _run_tesseract(self, images: list[Image.Image]) -> OCRResult:
        texts: list[str] = []
        confidences: list[float] = []

        for image in images:
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT
            )
            page_text = " ".join(w for w in data["text"] if w.strip())
            texts.append(page_text)

            word_confidences = [
                float(c) for c in data["conf"] if c not in ("-1", -1)
            ]
            if word_confidences:
                confidences.append(sum(word_confidences) / len(word_confidences) / 100)

        mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return OCRResult(
            text="\n\n".join(texts),
            mean_confidence=round(mean_confidence, 3),
            page_count=len(images),
        )

    def _run_paddleocr(self, images: list[Image.Image]) -> OCRResult:
        # Lazy import: PaddleOCR is a heavy optional dependency, only
        # required if OCR_ENGINE=paddleocr is actually selected.
        from paddleocr import PaddleOCR
        import numpy as np

        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        texts: list[str] = []
        confidences: list[float] = []

        for image in images:
            result = ocr.ocr(np.array(image), cls=True)
            lines = result[0] if result else []
            page_words = [line[1][0] for line in lines]
            page_confidences = [line[1][1] for line in lines]

            texts.append(" ".join(page_words))
            confidences.extend(page_confidences)

        mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return OCRResult(
            text="\n\n".join(texts),
            mean_confidence=round(mean_confidence, 3),
            page_count=len(images),
        )
