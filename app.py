#!/usr/bin/env python3
"""
OPD Patient Conditions, Findings, and Medications Summarizer App.
Flask server running on port 5008.
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify, render_template, Response

import config
from patient_mcp_client import PatientMcpClient, to_standard_date
from clinical_summary_engine import ClinicalSummaryEngine
from report_nlp_engine import ReportNlpEngine
from drug_photo_service import drug_photo_service

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OPD_Summaries")

app = Flask(
    __name__,
    template_folder=os.path.join(config.BASE_DIR, "templates"),
    static_folder=os.path.join(config.BASE_DIR, "static")
)
app.config['TEMPLATES_AUTO_RELOAD'] = True

mcp_client = PatientMcpClient()
summary_engine = ClinicalSummaryEngine()
nlp_engine = ReportNlpEngine()

@app.route("/")
def index():
    """Render main OPD clinical summary dashboard."""
    return render_template("index.html")

@app.route("/api/roster", methods=["GET"])
def get_roster():
    """Return outpatient roster loaded from Cloud_Data."""
    try:
        roster = mcp_client.load_patient_roster()
        return jsonify({"status": "success", "count": len(roster), "patients": roster})
    except Exception as e:
        logger.error(f"Error loading roster: {e}")
        return jsonify({"status": "error", "message": str(e), "patients": []}), 500

@app.route("/api/patient/<id_no>", methods=["GET"])
def get_patient_summary(id_no):
    """Generate and return full clinical summary for a patient."""
    clinic_date = request.args.get("date", "2026/09/01").strip()
    daterange = int(request.args.get("daterange", config.DEFAULT_DATERANGE))

    try:
        summary = summary_engine.generate_patient_summary(id_no, clinic_date, daterange)
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error generating summary for {id_no}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/drug_photo", methods=["GET"])
def get_drug_photo():
    """Stream pill photo from pills_jpeg_archive.zip or disk."""
    img_id = request.args.get("img_id", "").strip()
    code = request.args.get("code", "").strip()
    brand = request.args.get("brand", "").strip()

    stem = img_id
    if not stem:
        prod = drug_photo_service.find_drug_product(code, brand)
        if prod and prod.get("local_image_path"):
            stem = os.path.splitext(os.path.basename(prod["local_image_path"]))[0]

    if not stem:
        return Response("Photo not found", status=404, mimetype="text/plain")

    content, mime = drug_photo_service.get_photo_bytes(stem)
    if not content:
        return Response("Photo binary not found", status=404, mimetype="text/plain")

    return Response(
        content,
        mimetype=mime,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f"inline; filename={stem}.jpg"
        }
    )

@app.route("/api/drug_info", methods=["GET"])
def get_drug_info():
    """Return structured drug appearance details, NHI code, and photo URL."""
    code = request.args.get("code", "").strip()
    brand = request.args.get("brand", "").strip()
    generic = request.args.get("generic", "").strip()

    payload = drug_photo_service.get_drug_info_payload(code, brand, generic)
    return jsonify(payload)

@app.route("/api/extract_ai", methods=["POST"])
def extract_ai():
    """Trigger deep clinical extraction via local LLM on RTX A6000 (port 1234)."""
    data = request.get_json() or {}
    report_text = data.get("text", "").strip()
    modality = data.get("modality", "")

    if not report_text:
        return jsonify({"status": "error", "message": "Report text is required"}), 400

    try:
        res = nlp_engine.extract_with_local_llm(report_text, modality)
        return jsonify({"status": "success", "result": res})
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/chat", methods=["POST"])
def clinical_chat():
    """Handle interactive clinical inquiries about the current patient using RTX A6000 local LLM."""
    data = request.get_json() or {}
    patient_id = data.get("patient_id", "").strip()
    clinic_date = data.get("clinic_date", "2026/09/01").strip()
    user_query = data.get("message", "").strip()
    conversation_history = data.get("history", [])

    if not user_query:
        return jsonify({"status": "error", "message": "請輸入諮詢問題"}), 400

    try:
        # 1. Fetch current patient summary to ground LLM in truth
        summary = summary_engine.generate_patient_summary(patient_id, clinic_date, 180)
        profile = summary.get("profile", {})
        conditions = summary.get("conditions", {})
        findings = summary.get("findings", {})
        meds = summary.get("medications", {})

        # Format CT/MRI and other imaging reports & measurements
        ct_mri_texts = []
        rep_texts = []
        for rep in findings.get("radiology_reports", []):
            d = rep.get("date", "")
            study = rep.get("study_name") or rep.get("modality", "")
            lesion_items = [m.get("full_label") for m in rep.get("measurements", []) if m.get("full_label")]
            meas_str = f" [病灶發現: {', '.join(lesion_items[:4])}]" if lesion_items else ""
            findings_summary = "; ".join([f for flist in rep.get("findings_by_category", {}).values() for f in flist[:2]])
            imp = rep.get("sections", {}).get("impression", "")
            desc = imp or findings_summary or rep.get("raw_summary", "")[:70]
            line_str = f"• [{d}] {study}: {desc}{meas_str}"

            if rep.get("is_ct") or rep.get("is_mri"):
                ct_mri_texts.append(line_str)
            else:
                rep_texts.append(line_str)

        # Format active meds with brand name and generic ingredient
        med_texts = []
        for m in meds.get("active_medications", [])[:14]:
            ref_badge = "[慢箋]" if m.get("is_chronic_refill") else ""
            brand = m.get("brand_name") or m.get("medication")
            generic = m.get("generic_name") or m.get("ingredient")
            gen_str = f" [成分: {generic}]" if generic and generic.upper() not in brand.upper() else ""
            med_texts.append(f"• {brand}{gen_str} ({m.get('method')}) {ref_badge} - 剩餘 {m.get('days_remaining')} 天 (至 {m.get('end_date')})")

        badges_str = ", ".join([b.get("label", "") for b in profile.get("badges", [])])
        alerts_str = "\n".join([f"⚠️ {a}" for a in meds.get("safety_alerts", [])]) or "無特定警示"

        # Format chronic and acute problems
        chronic_texts = [f"• [{c.get('category', '').split(' ')[0]}] {c.get('name')} ({c.get('code')})" for c in conditions.get("chronic_diagnoses", [])[:7]]
        acute_texts = [f"• [{a.get('date', '近期')}] {a.get('name')} ({a.get('code')})" for a in conditions.get("acute_diagnoses", [])[:7]]

        # Format surgical and PTA procedures with execution dates
        surg_texts = []
        for s in conditions.get("surgical_procedures", []):
            if isinstance(s, dict):
                d_str = s.get("date", "歷史")
                n_str = s.get("name", "")
                det = f" ({s.get('detail')})" if s.get("detail") else ""
                surg_texts.append(f"• [{d_str}] {n_str}{det}")
            else:
                surg_texts.append(f"• {s}")

        # Build comprehensive clinical grounding context
        patient_context = (
            f"=== 目前病患完整臨床檔案 ===\n"
            f"病患識別: {patient_id} | 門診日期: {to_standard_date(clinic_date)}\n"
            f"主要標記: {badges_str or '無'}\n"
            f"主要數據: eGFR {profile.get('egfr', 'N/A')} mL/min, Cr {profile.get('creatinine', 'N/A')} mg/dL, "
            f"Hb {profile.get('hb', 'N/A')} g/dL, Glucose {profile.get('glucose', 'N/A')} mg/dL\n\n"
            f"問題清單 (慢性長期追蹤):\n"
            f"{chr(10).join(chronic_texts) if chronic_texts else '無特定慢性疾患'}\n\n"
            f"問題清單 (近期急性疾患 - 含就醫記錄日期):\n"
            f"{chr(10).join(acute_texts) if acute_texts else '近期無急性問題'}\n\n"
            f"手術與介入處置史 (含執行日期與PTA氣球/壓力尺寸):\n"
            f"{chr(10).join(surg_texts) if surg_texts else '無手術或處置紀錄'}\n\n"
            f"電腦斷層與磁振造影 (CT / MRI):\n"
            f"{chr(10).join(ct_mri_texts) if ct_mri_texts else '本就醫紀錄區間無 CT 或 MRI 檢查'}\n\n"
            f"其他影像與檢查 (內視鏡、X光、超音波等):\n"
            f"{chr(10).join(rep_texts[:5]) if rep_texts else '無其他近期報告'}\n\n"
            f"目前進行中用藥與慢箋:\n"
            f"{chr(10).join(med_texts) if med_texts else '無用藥'}\n\n"
            f"用藥安全警示:\n{alerts_str}\n"
            f"===================================="
        )

        system_prompt = (
            "你是一位資深的門診臨床 AI 協同醫師 (Clinical AI Co-pilot)，協助主治醫師在門診診間快速掌握病患狀況、回答醫療處置、用藥劑量與檢驗報告問題。\n"
            "請務必依據病患實際病歷資料精確回答：\n"
            "1. 條理分明、重點摘要、具備臨床依據。\n"
            "2. 若醫師詢問用藥或處方建議，請嚴格檢視病患目前的腎功能 (如 eGFR, Cr, 是否為 ESRD 血液透析)，提示劑量調整或禁忌症 (如 Metformin 乳酸中毒風險、NSAID 腎毒性、抗凝血劑出血風險)。\n"
            "3. 使用繁體中文回答，可保留標準臨床醫學英文簡稱 (如 CABG, ESRD, PTA, eGFR)。"
        )

        # Assemble messages compatible with MedGemma / Gemma / Llama strict alternating chat templates
        patient_intro = f"{system_prompt}\n\n{patient_context}\n\n"

        if not conversation_history:
            messages = [
                {"role": "user", "content": f"{patient_intro}【主治醫師諮詢問題】：\n{user_query}"}
            ]
        else:
            messages = [
                {"role": "user", "content": f"{patient_intro}請準備好回答此病患的後續臨床諮詢。"},
                {"role": "assistant", "content": "收到，我已掌握此病患之完整門診病歷、近期檢驗數值、影像與處置病灶、以及目前進行中處方與慢箋。請隨時提出您的問題。"}
            ]
            last_role = "assistant"
            for turn in conversation_history[-6:]:
                role = turn.get("role", "user")
                content = (turn.get("content") or "").strip()
                if role in ["user", "assistant"] and content and role != last_role:
                    messages.append({"role": role, "content": content})
                    last_role = role

            if last_role != "user":
                messages.append({"role": "user", "content": user_query})
            else:
                messages[-1]["content"] += f"\n\n【補充提問】：\n{user_query}"

        # Call local LLM on LM Studio (openai/gpt-oss-20b)
        payload = {
            "model": config.LOCAL_LLM_DEFAULT_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1500
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{config.LOCAL_LLM_HOST}/chat/completions",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=45) as resp:
            resp_json = json.loads(resp.read().decode("utf-8"))
            choice = resp_json.get("choices", [{}])[0]
            msg_obj = choice.get("message", {})
            reply_text = (msg_obj.get("content") or "").strip()
            if not reply_text:
                reply_text = (msg_obj.get("reasoning_content") or msg_obj.get("reasoning") or "").strip()

            return jsonify({
                "status": "success",
                "patient_id": patient_id,
                "reply": reply_text or "未能產生有效文字回答，請重試。"
            })

    except Exception as e:
        logger.warning(f"Local LLM offline or unreachable ({e}), generating deterministic clinical fallback reply.")
        q_lower = user_query.lower()
        if any(k in q_lower for k in ['ct', 'mri', '電腦斷層', '磁振造影', '病灶', '大小', '尺寸', '影像', '檢查', '超音波', 'x光', '內視鏡']):
            if ct_mri_texts:
                reply_text = "【電腦斷層與磁振造影 (CT / MRI) 病灶發現】：\n" + "\n".join(ct_mri_texts)
            else:
                reply_text = f"此病患於本紀錄區間無電腦斷層 (CT) 或磁振造影 (MRI) 檢查紀錄。\n\n【其他近期重要影像與檢查發現】：\n" + ("\n".join(rep_texts[:4]) if rep_texts else "無近期其他檢查。")
            return jsonify({
                "status": "success",
                "patient_id": patient_id,
                "reply": reply_text
            })
        elif any(k in q_lower for k in ['藥', '處方', '慢箋', 'med', '抗凝血', '降血壓', '降血糖']):
            reply_text = "【目前進行中處方與慢箋】：\n" + ("\n".join(med_texts) if med_texts else "無進行中用藥") + f"\n\n【用藥安全警示】：\n{alerts_str}"
            return jsonify({
                "status": "success",
                "patient_id": patient_id,
                "reply": reply_text
            })
        elif any(k in q_lower for k in ['問題', '診斷', '病史', '慢性', '急性', '手術', '處置', 'pta']):
            reply_text = "【慢性長期追蹤清單】：\n" + ("\n".join(chronic_texts) if chronic_texts else "無特定慢性病") + "\n\n【近期急性疾患】：\n" + ("\n".join(acute_texts) if acute_texts else "近期無急性問題") + "\n\n【手術與處置史】：\n" + ("\n".join(surg_texts) if surg_texts else "無紀錄")
            return jsonify({
                "status": "success",
                "patient_id": patient_id,
                "reply": reply_text
            })
        return jsonify({
            "status": "error",
            "message": f"AI 臨床諮詢服務回應異常 (本地 LLM 連線中斷): {str(e)}"
        }), 503

@app.route("/api/health", methods=["GET"])
def health_check():
    """Return system readiness of hospital REST API and local LLM."""
    llm_online = False
    try:
        import urllib.request
        with urllib.request.urlopen(f"{config.LOCAL_LLM_HOST}/models", timeout=2) as resp:
            if resp.status == 200:
                llm_online = True
    except Exception:
        pass

    return jsonify({
        "status": "online",
        "port": config.PORT,
        "hospital_api_host": config.HOSPITAL_API_HOST,
        "local_llm_online": llm_online,
        "local_llm_host": config.LOCAL_LLM_HOST,
        "local_llm_model": config.LOCAL_LLM_DEFAULT_MODEL,
        "local_llm_engine": "LM Studio",
        "gpu_device": "NVIDIA RTX A6000 (48GB VRAM)"
    })

if __name__ == "__main__":
    logger.info(f"Starting OPD Summarizer on http://127.0.0.1:{config.PORT}")
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
