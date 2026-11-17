/**
 * Loading patient data from the API and rendering every panel.
 */
import { state } from "./state.js";
import { formatRocDate } from "./utils.js";
import { renderPatientBanner } from "./banner.js";
import { renderConditions } from "./conditions.js";
import { initCorrelationSelectors } from "./correlation.js";
import { renderLabTable } from "./labs.js";
import { renderMedications } from "./meds.js";
import { renderRadiologyReports } from "./reports.js";

export async function checkSystemHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        const badge = document.getElementById("aiStatusBadge");
        if (badge) {
            if (data.local_llm_online) {
                const modelName = data.local_llm_model || 'gpt-oss-120b';
                const engineName = data.local_llm_engine || 'vLLM';
                badge.innerHTML = '<span class="dot dot-success"></span><span>AI server (連線)</span>';
                badge.title = `AI 伺服器連線正常: ${engineName} [${modelName}]`;
            } else {
                badge.innerHTML = '<span class="dot" style="background:#94a3b8"></span><span>AI server (待命)</span>';
                badge.title = 'AI 服務 (vLLM) 未啟動或連線中斷';
            }
        }
    } catch (e) {
        console.warn("Health check error:", e);
    }
}

export async function loadRoster() {
    const select = document.getElementById("rosterSelect");
    if (!select) return;
    try {
        const res = await fetch("/api/roster");
        const data = await res.json();
        if (data.status === "success" && data.patients.length > 0) {
            select.innerHTML = '<option value="">-- 請選擇門診病患 --</option>';
            data.patients.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id_no;
                opt.dataset.chartNo = p.chart_no;
                opt.dataset.clinicDate = p.clinic_date || "";
                opt.textContent = `${p.seq}. ${p.name} (${p.gender}, ${p.age}歲) - ${p.id_no}`;
                select.appendChild(opt);
            });
        } else {
            select.innerHTML = '<option value="">無門診名冊資料</option>';
        }
    } catch {
        select.innerHTML = '<option value="">名冊載入失敗</option>';
    }
}

let _latestLoadSeq = 0;

export async function loadPatientSummary(patientId, clinicDate, extraParams = {}) {
    const reqSeq = ++_latestLoadSeq;
    const cleanId = (patientId || "").trim().toUpperCase();
    const idInput = document.getElementById("patientIdInput");
    const dateInput = document.getElementById("clinicDateInput");
    const fallbackDate = state.lastQueryDate || (dateInput ? dateInput.value.trim() : "") || "1150721";
    const cleanDate = formatRocDate(clinicDate || fallbackDate);
    if (idInput && cleanId) idInput.value = cleanId;
    if (dateInput && cleanDate) dateInput.value = cleanDate;
    const searchBtn = document.getElementById("searchBtn");
    if (searchBtn) {
        searchBtn.disabled = true;
        searchBtn.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> 查詢中...';
    }

    const qs = new URLSearchParams({ date: cleanDate });
    if (extraParams && typeof extraParams === "object") {
        const chartNo = extraParams.chart_no || extraParams.chartNo;
        const birthDate = extraParams.birth_date || extraParams.birthdate;
        const ageVal = extraParams.age;
        const nameVal = extraParams.name;
        const genderVal = extraParams.gender;
        if (chartNo !== undefined && chartNo !== null && String(chartNo).trim() !== "") {
            qs.set("chart_no", String(chartNo).trim());
        }
        if (birthDate !== undefined && birthDate !== null && String(birthDate).trim() !== "") {
            qs.set("birthdate", String(birthDate).trim());
        }
        if (ageVal !== undefined && ageVal !== null && String(ageVal).trim() !== "") {
            qs.set("age", String(ageVal).trim());
        }
        if (nameVal !== undefined && nameVal !== null && String(nameVal).trim() !== "") {
            qs.set("name", String(nameVal).trim());
        }
        if (genderVal !== undefined && genderVal !== null && String(genderVal).trim() !== "") {
            qs.set("gender", String(genderVal).trim());
        }
    }
    qs.set("_ts", String(Date.now()));

    try {
        const res = await fetch(`/api/patient/${encodeURIComponent(cleanId)}?${qs.toString()}`, {
            cache: "no-store"
        });
        const data = await res.json();
        if (reqSeq !== _latestLoadSeq) {
            return;
        }
        if (searchBtn) {
            searchBtn.disabled = false;
            searchBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 查詢摘要';
        }

        if (data.status === "not_found") {
            alert(data.message || "查無此病患資料");
            return;
        }

        const resolvedDate = formatRocDate(data.clinic_date || cleanDate);
        if (dateInput) {
            dateInput.value = resolvedDate;
        }
        state.lastQueryDate = resolvedDate;
        if (cleanId) {
            state.lastPatientId = cleanId;
        }
        try {
            localStorage.setItem("opd_last_query_date", resolvedDate);
            if (cleanId) localStorage.setItem("opd_last_patient_id", cleanId);
        } catch (e) {}
        state.currentPatientData = data;
        renderAll(data);
    } catch (e) {
        if (reqSeq !== _latestLoadSeq) {
            return;
        }
        if (searchBtn) {
            searchBtn.disabled = false;
            searchBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 查詢摘要';
        }
        alert("連線或伺服器發生錯誤：" + e);
    }
}

export function renderAll(data) {
    renderPatientBanner(data);
    renderConditions(data.conditions);
    renderLabTable(data.findings.lab_panel, state.currentLabTab);
    renderRadiologyReports(data.findings.radiology_reports);
    renderMedications(data.medications);
    state.corrSelectorsInitialized = false;
    if (state.currentWorkspaceView === "correlation") {
        initCorrelationSelectors();
    }
}
