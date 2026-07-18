from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LargeHoldingFiling:
    """EDINET大量保有報告書(docTypeCode 350/360)のメタデータ。

    訂正・変更報告(parentDocID連鎖)の解決は行わず、EDINET APIレスポンスの
    生データをそのままマッピングする。
    """

    doc_id: str
    submitted_at: str
    filer_name: str | None
    filer_sec_code: str | None
    doc_type_code: str

    @classmethod
    def from_edinet_doc(cls, doc: dict) -> LargeHoldingFiling:
        """EDINET APIレスポンスの1書類分の辞書から LargeHoldingFiling を組み立てる。"""
        return cls(
            doc_id=doc["docID"],
            submitted_at=doc.get("submitDateTime", ""),
            filer_name=doc.get("filerName"),
            filer_sec_code=doc.get("secCode"),
            doc_type_code=doc.get("docTypeCode", ""),
        )
