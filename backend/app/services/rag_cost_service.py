"""
Cost grounding via retrieval-augmented generation.

Design decision: cost estimates are NEVER produced by asking the LLM to
"guess a typical cost" in the explanation prompt. That's exactly the
hallucination risk flagged during planning. Instead:

  1. Retrieve the most relevant chunk(s) from the cost-reference corpus
  2. Pass ONLY that retrieved text to the LLM and ask it to extract a
     range from it
  3. If nothing relevant is retrieved above the similarity threshold,
     return grounded=False rather than fabricating a number

Slice 1 uses TF-IDF similarity over local corpus files — zero extra
infra, good enough to validate the approach. Slice 2 swaps this for
pgvector + real embeddings once persistence is introduced, without
changing the public interface (`retrieve`) that callers depend on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "cost_reference_corpus"
SIMILARITY_THRESHOLD = 0.12


@dataclass
class RetrievedChunk:
    heading: str
    text: str
    score: float
    file_title: str = ""  # top-level heading of the source file, for context


class RAGCostService:
    def __init__(self, corpus_dir: Path = CORPUS_DIR) -> None:
        self._chunks = self._load_chunks(corpus_dir)
        self._vectorizer = TfidfVectorizer(stop_words="english")
        # Index on file_title + heading + body together: key terms like
        # "P0420" or "brakes" often live only in headings (the section's
        # own, or its parent file's), not repeated in the body text, so
        # body-only indexing under-matches queries using that vocabulary.
        corpus_texts = [
            f"{c.file_title}. {c.heading}. {c.text}" for c in self._chunks
        ]
        self._matrix = (
            self._vectorizer.fit_transform(corpus_texts) if corpus_texts else None
        )

    def retrieve(self, query: str, top_k: int = 2) -> list[RetrievedChunk]:
        if self._matrix is None:
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]

        ranked = sorted(
            zip(self._chunks, scores), key=lambda pair: pair[1], reverse=True
        )
        results = [
            RetrievedChunk(
                heading=c.heading,
                text=c.text,
                score=float(s),
                file_title=c.file_title,
            )
            for c, s in ranked[:top_k]
            if s >= SIMILARITY_THRESHOLD
        ]
        return results

    # ---- corpus loading ------------------------------------------------

    def _load_chunks(self, corpus_dir: Path) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        if not corpus_dir.exists():
            return chunks

        for path in corpus_dir.glob("*.md"):
            sections = re.split(r"\n## ", path.read_text(encoding="utf-8"))
            if not sections:
                continue

            # First section carries the file's top-level "# " title —
            # capture it once and stamp it onto every chunk from this
            # file, so a query for "brakes" still matches a "Notes on
            # urgency" sub-section that never says the word "brake".
            first_heading, *first_body = sections[0].strip().split("\n", 1)
            file_title = first_heading.lstrip("# ").strip()

            for section in sections:
                section = section.strip()
                if not section:
                    continue
                heading, *body = section.split("\n", 1)
                chunks.append(
                    RetrievedChunk(
                        heading=heading.lstrip("# ").strip(),
                        text=(body[0] if body else "").strip(),
                        score=0.0,
                        file_title=file_title,
                    )
                )
        return chunks
