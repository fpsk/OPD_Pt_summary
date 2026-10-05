"""
Clinical AI chat: grounds the local LLM in the current patient's summary.

Flow: summary -> ChatContext (formatted bullet lists) -> chat messages -> LLM.
If the LLM is unreachable, a deterministic keyword-based reply is built from
the same ChatContext so the clinician still gets useful information.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from services import llm_client
from services.patient_mcp_client import to_standard_date

CHAT_SUMMARY_DATERANGE = 180   # days of history used to ground chat answers
HISTORY_TURNS = 6              # most recent conversation turns sent to the LLM

SYSTEM_PROMPT = (
    "你是一位資深的門診臨床 AI 協同醫師 (Clinical AI Co-pilot)，協助主治醫師在門診診間快速掌握病患狀況、回答醫療處置、用藥劑量與檢驗報告問題。\n"
    "請務必依據病患實際病歷資料精確回答：\n"
    "1. 條理分明、重點摘要、具備臨床依據。\n"
    "2. 若醫師詢問用藥或處方建議，請嚴格檢視病患目前的腎功能 (如 eGFR, Cr, 是否為 ESRD 血液透析)，提示劑量調整或禁忌症 (如 Metformin 乳酸中毒風險、NSAID 腎毒性、抗凝血劑出血風險)。\n"
    "3. 使用繁體中文回答，可保留標準臨床醫學英文簡稱 (如 CABG, ESRD, PTA, eGFR)。"
)

ASSISTANT_ACK = "收到，我已掌握此病患之完整門診病歷、近期檢驗數值、影像與處置病灶、以及目前進行中處方與慢箋。請隨時提出您的問題。"

IMAGING_KEYWORDS = ['ct', 'mri', '電腦斷層', '磁振造影', '病灶', '大小', '尺寸', '影像', '檢查', '超音波', 'x光', '內視鏡']
MED_KEYWORDS = ['藥', '處方', '慢箋', 'med', '抗凝血', '降血壓', '降血糖']
PROBLEM_KEYWORDS = ['問題', '診斷', '病史', '慢性', '急性', '手術', '處置', 'pta']


@dataclass
class ChatContext:
    ct_mri: List[str] = field(default_factory=list)
    other_reports: List[str] = field(default_factory=list)
    meds: List[str] = field(default_factory=list)
    chronic: List[str] = field(default_factory=list)
    acute: List[str] = field(default_factory=list)
    surgical: List[str] = field(default_factory=list)
    alerts: str = "無特定警示"
    text: str = ""   # full grounding block sent to the LLM


def _lines(items: List[str], empty: str) -> str:
    return "\n".join(items) if items else empty


def build_context(summary: Dict[str, Any], patient_id: str, clinic_date: str) -> ChatContext:
    profile = summary.get("profile", {})
    conditions = summary.get("conditions", {})
    findings = summary.get("findings", {})
    meds = summary.get("medications", {})
    ctx = ChatContext()

    # Imaging reports & lesion measurements (CT/MRI separated from the rest)
    for rep in findings.get("radiology_reports", []):
        study = rep.get("study_name") or rep.get("modality", "")
        lesion_items = [m.get("full_label") for m in rep.get("measurements", []) if m.get("full_label")]
        meas_str = f" [病灶發現: {', '.join(lesion_items[:4])}]" if lesion_items else ""
        findings_summary = "; ".join(f for flist in rep.get("findings_by_category", {}).values() for f in flist[:2])
        imp = rep.get("sections", {}).get("impression", "")
        desc = imp or findings_summary or rep.get("raw_summary", "")[:70]
        line = f"• [{rep.get('date', '')}] {study}: {desc}{meas_str}"
        (ctx.ct_mri if rep.get("is_ct") or rep.get("is_mri") else ctx.other_reports).append(line)

    # Active medications with generic ingredient when it differs from brand
    for m in meds.get("active_medications", [])[:14]:
        ref_badge = "[慢箋]" if m.get("is_chronic_refill") else ""
        brand = m.get("brand_name") or m.get("medication")
        generic = m.get("generic_name") or m.get("ingredient")
        gen_str = f" [成分: {generic}]" if generic and generic.upper() not in brand.upper() else ""
        ctx.meds.append(f"• {brand}{gen_str} ({m.get('method')}) {ref_badge} - 剩餘 {m.get('days_remaining')} 天 (至 {m.get('end_date')})")

    ctx.alerts = "\n".join(f"⚠️ {a}" for a in meds.get("safety_alerts", [])) or "無特定警示"
    ctx.chronic = [f"• [{c.get('category', '').split(' ')[0]}] {c.get('name')} ({c.get('code')})" for c in conditions.get("chronic_diagnoses", [])[:7]]
    ctx.acute = [f"• [{a.get('date', '近期')}] {a.get('name')} ({a.get('code')})" for a in conditions.get("acute_diagnoses", [])[:7]]

    for s in conditions.get("surgical_procedures", []):
        if isinstance(s, dict):
            det = f" ({s.get('detail')})" if s.get("detail") else ""
            ctx.surgical.append(f"• [{s.get('date', '歷史')}] {s.get('name', '')}{det}")
        else:
            ctx.surgical.append(f"• {s}")

    badges_str = ", ".join(b.get("label", "") for b in profile.get("badges", []))
    ctx.text = (
        f"=== 目前病患完整臨床檔案 ===\n"
        f"病患識別: {patient_id} | 門診日期: {to_standard_date(clinic_date)}\n"
        f"主要標記: {badges_str or '無'}\n"
        f"主要數據: eGFR {profile.get('egfr', 'N/A')} mL/min, Cr {profile.get('creatinine', 'N/A')} mg/dL, "
        f"Hb {profile.get('hb', 'N/A')} g/dL, Glucose {profile.get('glucose', 'N/A')} mg/dL\n\n"
        f"問題清單 (慢性長期追蹤):\n{_lines(ctx.chronic, '無特定慢性疾患')}\n\n"
        f"問題清單 (近期急性疾患 - 含就醫記錄日期):\n{_lines(ctx.acute, '近期無急性問題')}\n\n"
        f"手術與介入處置史 (含執行日期與PTA氣球/壓力尺寸):\n{_lines(ctx.surgical, '無手術或處置紀錄')}\n\n"
        f"電腦斷層與磁振造影 (CT / MRI):\n{_lines(ctx.ct_mri, '本就醫紀錄區間無 CT 或 MRI 檢查')}\n\n"
        f"其他影像與檢查 (內視鏡、X光、超音波等):\n{_lines(ctx.other_reports[:5], '無其他近期報告')}\n\n"
        f"目前進行中用藥與慢箋:\n{_lines(ctx.meds, '無用藥')}\n\n"
        f"用藥安全警示:\n{ctx.alerts}\n"
        f"===================================="
    )
    return ctx


def build_messages(ctx: ChatContext, user_query: str, history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Strictly alternating user/assistant turns (required by Gemma/Llama-style chat templates)."""
    intro = f"{SYSTEM_PROMPT}\n\n{ctx.text}\n\n"
    if not history:
        return [{"role": "user", "content": f"{intro}【主治醫師諮詢問題】：\n{user_query}"}]

    messages = [
        {"role": "user", "content": f"{intro}請準備好回答此病患的後續臨床諮詢。"},
        {"role": "assistant", "content": ASSISTANT_ACK},
    ]
    last_role = "assistant"
    for turn in history[-HISTORY_TURNS:]:
        role = turn.get("role", "user")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content and role != last_role:
            messages.append({"role": role, "content": content})
            last_role = role

    if last_role != "user":
        messages.append({"role": "user", "content": user_query})
    else:
        messages[-1]["content"] += f"\n\n【補充提問】：\n{user_query}"
    return messages


def fallback_reply(ctx: ChatContext, user_query: str) -> Optional[str]:
    """Deterministic answer from structured data when the LLM is offline."""
    q = user_query.lower()
    if any(k in q for k in IMAGING_KEYWORDS):
        if ctx.ct_mri:
            return "【電腦斷層與磁振造影 (CT / MRI) 病灶發現】：\n" + "\n".join(ctx.ct_mri)
        return ("此病患於本紀錄區間無電腦斷層 (CT) 或磁振造影 (MRI) 檢查紀錄。\n\n【其他近期重要影像與檢查發現】：\n"
                + _lines(ctx.other_reports[:4], "無近期其他檢查。"))
    if any(k in q for k in MED_KEYWORDS):
        return "【目前進行中處方與慢箋】：\n" + _lines(ctx.meds, "無進行中用藥") + f"\n\n【用藥安全警示】：\n{ctx.alerts}"
    if any(k in q for k in PROBLEM_KEYWORDS):
        return ("【慢性長期追蹤清單】：\n" + _lines(ctx.chronic, "無特定慢性病")
                + "\n\n【近期急性疾患】：\n" + _lines(ctx.acute, "近期無急性問題")
                + "\n\n【手術與處置史】：\n" + _lines(ctx.surgical, "無紀錄"))
    return None


def answer(summary_engine, patient_id: str, clinic_date: str, user_query: str,
           history: List[Dict[str, Any]], logger=None) -> Tuple[Dict[str, Any], int]:
    """Returns (json_body, http_status)."""
    try:
        summary = summary_engine.generate_patient_summary(patient_id, clinic_date, CHAT_SUMMARY_DATERANGE)
        ctx = build_context(summary, patient_id, clinic_date)
    except Exception as e:
        if logger:
            logger.error(f"Chat context build failed for {patient_id}: {e}", exc_info=True)
        return {"status": "error", "message": f"無法載入病患資料以供 AI 諮詢: {e}"}, 503

    try:
        reply = llm_client.chat_completion(build_messages(ctx, user_query, history),
                                           temperature=0.2, max_tokens=1500, timeout=45)
        return {"status": "success", "patient_id": patient_id,
                "reply": reply or "未能產生有效文字回答，請重試。"}, 200
    except Exception as e:
        if logger:
            logger.warning(f"Local LLM offline or unreachable ({e}), generating deterministic clinical fallback reply.")
        reply = fallback_reply(ctx, user_query)
        if reply:
            return {"status": "success", "patient_id": patient_id, "reply": reply}, 200
        return {"status": "error", "message": f"AI 臨床諮詢服務回應異常 (本地 LLM 連線中斷): {str(e)}"}, 503
