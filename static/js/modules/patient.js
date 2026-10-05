/**
 * Loading patient data from the API and rendering every panel.
 */
import { state } from "./state.js";
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
                const modelName = data.local_llm_model || 'openai/gpt-oss-20b';
                badge.innerHTML = '<span class="dot dot-success"></span><span>AI server (連線)</span>';
                badge.title = `本地 AI 伺服器連線正常: LM Studio [${modelName}]`;
            } else {
                badge.innerHTML = '<span class="dot" style="background:#94a3b8"></span><span>AI server (待命)</span>';
                badge.title = '本地 AI 服務 (LM Studio) 未啟動或連線中斷';
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

export async function loadPatientSummary(patientId, clinicDate) {
    const searchBtn = document.getElementById("searchBtn");
    searchBtn.disabled = true;
    searchBtn.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> 查詢中...';

    try {
        const res = await fetch(`/api/patient/${encodeURIComponent(patientId)}?date=${encodeURIComponent(clinicDate)}`);
        const data = await res.json();
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 查詢摘要';

        if (data.status === "not_found") {
            alert(data.message || "查無此病患資料");
            return;
        }

        state.currentPatientData = data;
        renderAll(data);
    } catch (e) {
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 查詢摘要';
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
