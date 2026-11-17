"""
Configuration settings for the OPD Patient Clinical Summarizer.
Workspace: d:/Antigravity_workspace/Summaries
"""

import os
import sys

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Secrets and host addresses live in .env (see .env.example)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Hospital REST API Endpoint
HOSPITAL_API_HOST = os.getenv("HOSPITAL_API_HOST", "")
HOSPITAL_AUTH_USER = os.getenv("HOSPITAL_AUTH_USER", "")
HOSPITAL_AUTH_PASS = os.getenv("HOSPITAL_AUTH_PASS", "")

# Advanced NHI Regulation MCP Workspace Path
ADVANCED_NHI_PATH = os.path.join(PARENT_DIR, "Advanced_NHI_Regulation")
CLOUD_DATA_PATH = os.path.join(PARENT_DIR, "Cloud_Data")

# OMOP CDM Database Configuration
OMOP_DB_HOST = os.getenv("OMOP_DB_HOST", "")
OMOP_DB_PORT = os.getenv("OMOP_DB_PORT", "5432")
OMOP_DB_NAME = os.getenv("OMOP_DB_NAME", "")
OMOP_DB_SCHEMA = os.getenv("OMOP_DB_SCHEMA", "")
OMOP_DB_USER = os.getenv("OMOP_DB_USER", "")
OMOP_DB_PASSWORD = os.getenv("OMOP_DB_PASSWORD", "")

# LLM Server (vLLM on port 8000)
LOCAL_LLM_HOST = os.getenv("LOCAL_LLM_HOST", "http://172.22.135.127:8000/v1")
LOCAL_LLM_DEFAULT_MODEL = os.getenv("LOCAL_LLM_DEFAULT_MODEL", "gpt-oss-120b")

# SQLite Cache DB for NLP and Clinical Summaries
CACHE_DB_PATH = os.path.join(BASE_DIR, "summaries_cache.db")

# Query Timeframe: Maximum downloaded cloud data (3 years = 1095 days)
DEFAULT_DATERANGE = 1095

# Web Server Port (Fixed Constant Port)
PORT = int(os.getenv("PORT", 5008))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1")
SIBLING_PORTS = tuple(int(p.strip()) for p in os.getenv("SIBLING_PORTS", "5007,5050").split(",") if p.strip())
