import time
import re
import dataclasses
import os
from typing import Callable, Optional

from .extraction import DocumentLoader
from .engines import EngineRegistry, EngineConfig
from .domain.document import Document, DocumentSource, DocumentContent, ExtractionInfo, ExtractionMethod
from .domain.comparison import ComparisonResult, MetadataWarning
from .utils import AssignmentAnalyzerError

ProgressCallback = Callable[[int, str], None]

class AssignmentAnalyzer:
    """
    Orchestrates the end-to-end analysis pipeline.
    """

    def __init__(
        self,
        progress_callback: Optional[ProgressCallback] = None,
        stages_callback: Optional[Callable[[list[str]], None]] = None,
        engine_id: str = "embedding_v1",
        config: Optional[EngineConfig] = None,
    ):
        self.progress_callback = progress_callback
        self.stages_callback = stages_callback
        self.engine_id = engine_id
        self.config = config or EngineConfig()
        self._loader = DocumentLoader()
        self.last_result: Optional[ComparisonResult] = None

    def analyze_one_to_one(
        self,
        file_path_1: str,
        file_path_2: str,
    ) -> dict:
        start_time = time.time()
        
        try:
            engine = EngineRegistry.get(self.engine_id)
        except Exception as e:
            return self._create_error_dict(file_path_1, file_path_2, str(e), start_time)

        self._progress(10, "Preparing assignments")
        
        try:
            doc_a = self._loader.load(
                file_path_1,
                self._sub_progress(10, 25, "Reading document 1")
            )
        except Exception as e:
            return self._create_error_dict(file_path_1, file_path_2, str(e), start_time)

        try:
            doc_b = self._loader.load(
                file_path_2,
                self._sub_progress(25, 40, "Reading document 2")
            )
        except Exception as e:
            return self._create_error_dict(file_path_1, file_path_2, str(e), start_time, doc_a)

        self._progress(40, "Validating documents")
        if doc_a.is_empty or doc_b.is_empty:
            elapsed = time.time() - start_time
            which = doc_a.file_name if doc_a.is_empty else doc_b.file_name
            res = ComparisonResult.error_result(
                doc_a, doc_b,
                f"Document '{which}' appears empty or contains no readable text.",
                self.engine_id, elapsed
            )
            self.last_result = res
            return res.to_legacy_dict()

        self._progress(45, "Checking metadata")
        metadata_warnings = self._check_metadata(doc_a, doc_b)

        self._progress(50, "Loading AI model and analyzing content")
        result = engine.compare(
            doc_a, doc_b, self.config,
            progress_callback=self._sub_progress(50, 90, "Comparing")
        )

        if result.error:
            self.last_result = result
            return result.to_legacy_dict()

        self._progress(90, "Generating summary")
        enriched = self._enrich(result, metadata_warnings, time.time() - start_time)

        self._progress(100, "Finished")
        
        self.last_result = enriched
        return enriched.to_legacy_dict()

    def _create_error_dict(self, path1: str, path2: str, msg: str, start_time: float, doc_a: Optional[Document] = None) -> dict:
        elapsed = time.time() - start_time
        if doc_a is None:
            doc_a = Document(
                source=DocumentSource(path1, os.path.basename(path1), "", 0, 0.0),
                content=DocumentContent("", (), 0, 0, 0),
                extraction_info=ExtractionInfo(ExtractionMethod.DIGITAL_TEXT, 0, 0, 0.0, ())
            )
        res = ComparisonResult.error_result(doc_a, None, msg, self.engine_id, elapsed)
        self.last_result = res
        return res.to_legacy_dict()

    def _enrich(
        self,
        result: ComparisonResult,
        warnings: tuple[MetadataWarning, ...],
        total_time: float,
    ) -> ComparisonResult:
        summary = self._generate_summary(result.statistics, len(result.matched_paragraphs), warnings)
        return dataclasses.replace(
            result,
            metadata_warnings=warnings,
            summary=summary,
            processing_time_s=total_time,
        )

    def _check_metadata(self, doc_a: Document, doc_b: Document) -> tuple[MetadataWarning, ...]:
        warnings = []
        head_a = doc_a.content.raw_text[:500].lower()
        head_b = doc_b.content.raw_text[:500].lower()

        ids_a = set(re.findall(r'\b\d{7,9}\b', head_a))
        ids_b = set(re.findall(r'\b\d{7,9}\b', head_b))
        for common_id in ids_a & ids_b:
            warnings.append(MetadataWarning(
                code="IDENTICAL_STUDENT_ID",
                severity="high",
                message=f"Identical Student ID detected: {common_id}",
            ))

        if doc_a.source.file_name.lower() == doc_b.source.file_name.lower():
            warnings.append(MetadataWarning(
                code="IDENTICAL_FILENAME",
                severity="medium",
                message=f"Both documents have the same filename: {doc_a.source.file_name}",
            ))

        return tuple(warnings)

    def _generate_summary(self, stats, num_matches, warnings) -> str:
        score = stats.score_percent
        summary_parts = []
        
        if score >= 70:
            summary_parts.append("The assignments share a highly significant amount of semantic meaning.")
            summary_parts.append(f"We found {num_matches} highly similar paragraphs indicating potential copying or heavy collaboration.")
        elif score >= 40:
            summary_parts.append("There is moderate overlap in the concepts discussed.")
            summary_parts.append(f"{num_matches} paragraphs show structural or semantic similarities.")
        else:
            summary_parts.append("The assignments appear to be largely independent.")
            if num_matches > 0:
                summary_parts.append(f"Only {num_matches} brief sections showed minor similarities.")
            else:
                summary_parts.append("No significant semantic overlap was detected.")

        if warnings:
            warn_msgs = [w.message for w in warnings]
            summary_parts.append("\nWarnings: " + " | ".join(warn_msgs))

        return " ".join(summary_parts)

    def _progress(self, percent: int, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(percent, message)

    def _sub_progress(self, start: int, end: int, prefix: str) -> ProgressCallback:
        def cb(pct: int, msg: str) -> None:
            if pct == -1:
                self._progress(-1, msg)
                return
            mapped = start + int((pct / 100) * (end - start))
            self._progress(mapped, f"{prefix}: {msg}")
        return cb
