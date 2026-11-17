"""
Backend services. Shared singletons are created once here so the summary
engine, NLP engine, MCP client, and drug services are not instantiated multiple times.
"""

from services.clinical_summary_engine import ClinicalSummaryEngine
from services.drug_photo_service import DrugPhotoService, drug_photo_service
from services.drug_safety_service import DrugSafetyService, drug_safety_service
from services.patient_mcp_client import PatientMcpClient
from services.report_nlp_engine import ReportNlpEngine

summary_engine = ClinicalSummaryEngine()
mcp_client = summary_engine.mcp_client
nlp_engine = summary_engine.nlp_engine

__all__ = [
    # Classes
    "ClinicalSummaryEngine",
    "PatientMcpClient",
    "ReportNlpEngine",
    "DrugPhotoService",
    "DrugSafetyService",
    # Singletons
    "summary_engine",
    "mcp_client",
    "nlp_engine",
    "drug_photo_service",
    "drug_safety_service",
]
