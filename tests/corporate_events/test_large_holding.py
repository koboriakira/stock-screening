from __future__ import annotations

from stock_screener.corporate_events.domain.large_holding import LargeHoldingFiling


def _make_doc(
    doc_id: str = "S100ABC1",
    submit_date_time: str = "2025-01-15 09:00",
    filer_name: str | None = "テストファンド株式会社",
    sec_code: str | None = "72030",
    doc_type_code: str = "350",
    issuer_edinet_code: str | None = "E00004",
) -> dict:
    return {
        "docID": doc_id,
        "submitDateTime": submit_date_time,
        "filerName": filer_name,
        "secCode": sec_code,
        "docTypeCode": doc_type_code,
        "issuerEdinetCode": issuer_edinet_code,
    }


class TestLargeHoldingFilingFromEdinetDoc:
    def test_maps_all_fields(self):
        doc = _make_doc()

        filing = LargeHoldingFiling.from_edinet_doc(doc)

        assert filing.doc_id == "S100ABC1"
        assert filing.submitted_at == "2025-01-15 09:00"
        assert filing.filer_name == "テストファンド株式会社"
        assert filing.filer_sec_code == "72030"
        assert filing.doc_type_code == "350"

    def test_handles_missing_optional_fields(self):
        doc = _make_doc(filer_name=None, sec_code=None)

        filing = LargeHoldingFiling.from_edinet_doc(doc)

        assert filing.filer_name is None
        assert filing.filer_sec_code is None

    def test_is_frozen(self):
        filing = LargeHoldingFiling.from_edinet_doc(_make_doc())

        try:
            filing.doc_id = "changed"  # type: ignore[misc]
        except AttributeError:
            pass
        else:
            msg = "LargeHoldingFiling should be immutable"
            raise AssertionError(msg)
