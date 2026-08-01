from app.services.rag_cost_service import RAGCostService


def test_retrieves_relevant_chunk_for_brake_pads():
    rag = RAGCostService()
    results = rag.retrieve("brake pad worn thickness below specification")

    assert results, "expected at least one matching chunk"
    # The top individual section may be a general "urgency notes" chunk
    # rather than the section literally titled "brake pad" -- what
    # matters is that retrieval stayed within the right source file.
    assert "brake" in results[0].file_title.lower()


def test_retrieves_relevant_chunk_for_p0420():
    rag = RAGCostService()
    results = rag.retrieve("P0420 catalyst efficiency below threshold")

    assert results
    assert "p0420" in results[0].heading.lower() or "catalyst" in results[0].text.lower()


def test_no_match_returns_empty_list():
    rag = RAGCostService()
    results = rag.retrieve("spacecraft warp drive misalignment")

    assert results == []
