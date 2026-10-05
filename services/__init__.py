"""
Backend services. Shared singletons are created once here so the summary
engine, NLP engine and MCP client are not instantiated multiple times.
"""

from services.clinical_summary_engine import ClinicalSummaryEngine
from services.drug_photo_service import drug_photo_service

summary_engine = ClinicalSummaryEngine()
mcp_client = summary_engine.mcp_client
nlp_engine = summary_engine.nlp_engine

__all__ = ["summary_engine", "mcp_client", "nlp_engine", "drug_photo_service"]
