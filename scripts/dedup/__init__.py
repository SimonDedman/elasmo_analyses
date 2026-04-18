"""Confidence-scored PDF deduplication (v8)."""
from .schema import PdfFeatures, EXTRACTOR_VERSION
from .cache import FeatureCache

__all__ = ["PdfFeatures", "FeatureCache", "EXTRACTOR_VERSION"]
