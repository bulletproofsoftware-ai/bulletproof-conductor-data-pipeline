"""
Conductor Data Pipeline -- Compliance Module.

Provides GDPR Article 30 processing record generation from pipeline lineage
events. Maps lineage fields to Article 30 fields per SPEC Section 13.5.
"""

from compliance.gdpr_article30 import Article30Generator, Article30Record

__all__ = [
    "Article30Generator",
    "Article30Record",
]
