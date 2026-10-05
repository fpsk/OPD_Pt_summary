"""
Configuration settings for the OPD Patient Clinical Summarizer.
Workspace: d:/Antigravity_workspace/Summaries
"""

import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

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

# Local LLM Server (LM Studio on port 1234)
LOCAL_LLM_HOST = os.getenv("LOCAL_LLM_HOST", "http://localhost:1234/v1")
LOCAL_LLM_DEFAULT_MODEL = os.getenv("LOCAL_LLM_DEFAULT_MODEL", "openai/gpt-oss-20b")

# SQLite Cache DB for NLP and Clinical Summaries
CACHE_DB_PATH = os.path.join(BASE_DIR, "summaries_cache.db")

# Query Timeframe: Maximum downloaded cloud data (3 years = 1095 days)
DEFAULT_DATERANGE = 1095

# Web Server Port
PORT = 5008
DEBUG = True
