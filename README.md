# OPD Patient Clinical Summarizer (門診病患綜合摘要系統)

A high-speed clinical pre-consultation and review web application designed for outpatient department (OPD) physicians.

It synthesizes **Patient Conditions**, **Objective Findings (Labs & Narrative Radiology)**, and **Current Medications (with 慢箋 Chronic Refill tracking)** by interfacing with the local hospital MCP server, OMOP CDM database, and local NVIDIA RTX A6000 AI.

---

## 🚀 Key Features

1. **Outpatient Roster Quick Switcher**:
   - Automatically loads OPD schedules from `Cloud_Data` (`patient_list_20260804.csv`, `patient_list_20260804A.csv`, `Pt_ID_Table.xlsx`).
   - Doctors can switch patients with a single click.

2. **3-Column Clinical Consultation Grid**:
   - **Column 1: Conditions & Problem List**:
     - Active diagnoses extracted from ICD impressions and prescription diagnoses.
     - Surgical & intervention history (e.g., *s/p CABG, Left brachiocephalic AV fistula, PTA/thrombectomy*).
     - Clinical alert badges (*ESRD on H/D, CAD s/p CABG, Type 2 DM, HTN, Anemia*).
   - **Column 2: Objective Findings (Labs & Radiology)**:
     - Grouped lab panels (Renal, CBC, Biochem) with abnormal/critical highlighting (Cr, eGFR, BUN, Hb, Glucose).
     - Narrative radiology & procedure reports parser:
       - Extracts lesion sizes and device dimensions (e.g., `Mustang 7*40mm`, `6 Fr introducer`, `4 ATM balloon pressure`).
       - Dual-engine: deterministic regex extraction (<10ms) + on-demand local AI deep extraction via NVIDIA RTX A6000 (port 1234).
   - **Column 3: Current Medications & 慢箋**:
     - Categorized by clinical specialty (Cardiovascular, Endocrine, Renal/Dialysis, Antithrombotic, CNS).
     - 3-month continuous refill (`慢箋`) tracking with remaining days countdown and expiration date.
     - Renal contraindication alerts (e.g., Metformin in ESRD).

3. **1-Click EMR Pre-Consultation SOAP Note**:
   - Formats complete clinical synthesis into standardized hospital EMR text.
   - 1-click clipboard copy ready to paste into the hospital chart.

4. **Interactive Clinical AI Co-Pilot Chat Box (Bottom Dock)**:
   - Docked at the bottom of the screen for rapid inquiry during consultation.
   - Powered by on-premise **NVIDIA RTX A6000 (port 1234)** with zero cloud privacy exposure.
   - Fully grounded in the currently loaded patient's verified EHR (eGFR, Cr, active medications, 慢箋 days, surgical history, and radiology findings).
   - Quick inquiry prompt chips:
     - 🩺 主要臨床風險 (Major clinical risks summary)
     - 💊 腎功能用藥安全檢視 (Renal contraindications & dose conflicts)
     - 🩻 影像與病灶處置摘要 (Latest imaging, lesion, and device sizing)
     - 🩸 抗血栓與出血風險 (Bleeding risk assessment for Plavix/Cofarin)
     - 📝 門診衛教叮嚀重點 (Patient education and follow-up guidance)

---

## 🛠️ Architecture & Port Configuration

- **Port**: `http://localhost:5008` (Dedicated port, avoiding conflict with FDCs on 5007)
- **Hospital MCP REST Gateway / OMOP CDM DB**: configured in `.env` (never committed)
- **Local AI LLM Server**: LM Studio, `http://localhost:1234/v1`, model `openai/gpt-oss-20b` (NVIDIA RTX A6000, 48GB VRAM)
- **Cache**: Local SQLite database (`summaries_cache.db`) for caching NLP and AI extractions.

### Setup

```
copy .env.example .env      # then fill in hospital API / OMOP credentials
pip install flask python-dotenv
python app.py
```

---

## 📂 File Structure

```
d:/Antigravity_workspace/Summaries/
├── app.py                          # Flask app factory (port 5008)
├── config.py                       # Settings; secrets loaded from .env
├── .env.example                    # Template for required environment variables
├── services/                       # Backend logic (no Flask imports)
│   ├── __init__.py                 # Shared singletons (summary/NLP engines, MCP client, photos)
│   ├── patient_mcp_client.py       # REST API, OMOP DB & Cloud_Data roster loader
│   ├── clinical_summary_engine.py  # Multi-domain clinical synthesis & EMR note generator
│   ├── report_nlp_engine.py        # Deterministic report extractor + LLM deep extraction
│   ├── drug_photo_service.py       # Pill photo / appearance lookup (Medication_Info)
│   ├── llm_client.py               # Single LM Studio (OpenAI-compatible) client
│   └── clinical_chat.py            # Chat grounding, prompts, offline fallback
├── routes/                         # Flask blueprints (thin HTTP wrappers)
│   ├── pages.py  patient.py  drugs.py  ai.py  system.py
├── templates/index.html            # Clinical dashboard template
└── static/
    ├── css/styles.css              # Medical UI styling & dark/light theme
    └── js/
        ├── main.js                 # Entry point (ES module bootstrap)
        └── modules/                # state, utils, patient, banner, conditions, labs,
                                    # reports, meds, drug-photo, chat, correlation,
                                    # workspace, theme, events
```
