"""services/documents — Document pipeline (spec/05).

fetch → classify → ocr → parse_przedmiar → chunk+embed
"""
from .fetch import fetch_documents
from .classify import classify_document, DocKind
from .ocr import extract_text
from .parse_przedmiar import parse_przedmiar, PrzedmiarItem
from .chunk import chunk_and_embed

__all__ = [
    "fetch_documents",
    "classify_document",
    "DocKind",
    "extract_text",
    "parse_przedmiar",
    "PrzedmiarItem",
    "chunk_and_embed",
]
