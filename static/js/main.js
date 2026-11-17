/**
 * OPD Patient Clinical Summarizer - frontend entry point (bootstrap only).
 * Feature code lives in ./modules/*.js; shared mutable state in modules/state.js.
 */
import { setupEventListeners } from "./modules/events.js";
import { checkSystemHealth, loadPatientSummary, loadRoster } from "./modules/patient.js";
import { state } from "./modules/state.js";
import { initTheme } from "./modules/theme.js";
import { formatRocDate } from "./modules/utils.js";
import { switchWorkspaceView } from "./modules/workspace.js";
import { openDrugPhotoModalFromBtn } from "./modules/drug-photo.js";
import { setupDrugSafetyModalEvents, openDrugSafetyModalFromBtn } from "./modules/drug-safety.js";
import { toggleRawReport, triggerAiExtract } from "./modules/reports.js";

// Functions invoked from inline onclick="..." attributes in generated HTML.
// ES modules don't create globals, so expose exactly these on window.
Object.assign(window, { openDrugPhotoModalFromBtn, openDrugSafetyModalFromBtn, toggleRawReport, triggerAiExtract });

let sseEventSource = null;
let pendingLaunchData = null;
let lastHandledLaunchSignature = "";

function setSseStatus(connected) {
    const sseDot = document.getElementById("sseStatusDot");
    const sseText = document.getElementById("sseStatusText");
    if (connected) {
        if (sseDot) {
            sseDot.className = "dot dot-success";
            sseDot.style.background = "";
        }
        if (sseText) sseText.textContent = "Push: 連線就緒 (SSE)";
    } else {
        if (sseDot) {
            sseDot.className = "dot";
            sseDot.style.background = "#f59e0b";
        }
        if (sseText) sseText.textContent = "Push: 離線 (重連中)";
    }
}

function loadIncomingPatient(patientId, patientDate, launchMeta = {}) {
    const idInput = document.getElementById("patientIdInput");
    const dateInput = document.getElementById("clinicDateInput");
    const rosterSelect = document.getElementById("rosterSelect");
    const rocDt = formatRocDate(patientDate || state.lastQueryDate || (dateInput ? dateInput.value : "1150721"));
    if (idInput) idInput.value = patientId;
    if (dateInput) dateInput.value = rocDt;
    state.lastQueryDate = rocDt;
    if (patientId) state.lastPatientId = patientId;
    try {
        localStorage.setItem("opd_last_query_date", rocDt);
        if (patientId) localStorage.setItem("opd_last_patient_id", patientId);
    } catch (e) {}
    if (rosterSelect && rosterSelect.value !== patientId) {
        rosterSelect.value = "";
    }

    // Immediate banner update for chart number, age, and ID before full summary fetch completes
    const ptIdEl = document.getElementById("ptIdNo");
    if (ptIdEl && patientId) {
        ptIdEl.textContent = "ID: " + patientId;
    }
    const chartNoVal = launchMeta.chart_no || launchMeta.chartNo;
    if (chartNoVal) {
        const ptChartEl = document.getElementById("ptChartNo");
        if (ptChartEl) ptChartEl.textContent = "病歷號: " + chartNoVal;
    }
    if (launchMeta.age !== undefined && launchMeta.age !== null && launchMeta.age !== "") {
        const ptGenderAgeEl = document.getElementById("ptGenderAge");
        if (ptGenderAgeEl) {
            const g = launchMeta.gender || (patientId.length >= 2 ? (patientId[1] === "1" ? "男" : (patientId[1] === "2" ? "女" : "--")) : "--");
            ptGenderAgeEl.textContent = `${g} / ${launchMeta.age} 歲`;
        }
    }
    if (launchMeta.name) {
        const ptNameEl = document.getElementById("ptName");
        if (ptNameEl) ptNameEl.textContent = launchMeta.name;
    }

    loadPatientSummary(patientId, rocDt, launchMeta);
}

function dismissLaunchPrompt() {
    const promptEl = document.getElementById("sseLaunchPrompt");
    if (promptEl) promptEl.style.display = "none";
}

function showLaunchPrompt(patientId, patientDate) {
    const promptEl = document.getElementById("sseLaunchPrompt");
    const textEl = document.getElementById("sseLaunchPromptText");
    const btnAccept = document.getElementById("btnAcceptLaunchPrompt");
    const btnDismiss = document.getElementById("btnDismissLaunchPrompt");
    if (!promptEl) return;

    if (textEl) {
        textEl.innerHTML = `外部系統通知載入新病患 (門診日: ${patientDate})。<br>目前審查進行中，是否載入新病患？ (New patient received: load?)`;
    }
    promptEl.style.display = "block";

    if (btnAccept) {
        btnAccept.onclick = () => {
            dismissLaunchPrompt();
            if (pendingLaunchData) {
                loadIncomingPatient(pendingLaunchData.patient_id, pendingLaunchData.display_date, pendingLaunchData.raw || {});
                pendingLaunchData = null;
            }
        };
    }
    if (btnDismiss) {
        btnDismiss.onclick = () => {
            dismissLaunchPrompt();
            pendingLaunchData = null;
        };
    }
}

function handleIncomingLaunch(data) {
    if (!data || !data.patient_id) return;
    const newId = (data.patient_id || "").trim().toUpperCase();
    const displayDate = formatRocDate(data.patient_date || data.standard_date || state.lastQueryDate || "1150721");
    const sig = `${newId}|${displayDate}|${data.chart_no || data.chartNo || ""}|${data.age ?? ""}|${data.birth_date || data.birthdate || ""}|${data.launch_ts || ""}`;
    if (sig === lastHandledLaunchSignature && state.currentPatientData && state.currentPatientData.patient_id === newId) {
        return;
    }
    lastHandledLaunchSignature = sig;
    dismissLaunchPrompt();
    loadIncomingPatient(newId, displayDate, data);
}

function initSseConsumer() {
    if (typeof EventSource === "undefined") return;
    if (sseEventSource) {
        try { sseEventSource.close(); } catch (e) {}
    }
    try {
        sseEventSource = new EventSource("/api/events");
        sseEventSource.onopen = () => setSseStatus(true);
        sseEventSource.onerror = () => setSseStatus(false);
        sseEventSource.addEventListener("launch", (event) => {
            try {
                const data = JSON.parse(event.data);
                handleIncomingLaunch(data);
            } catch (err) {
                console.error("[SSE] Failed to parse launch event:", err);
            }
        });
    } catch (e) {
        setSseStatus(false);
    }
}

function bootstrap() {
    console.log("[Bootstrap] Initializing OPD Patient Clinical Summarizer...");
    try { initTheme(); } catch (e) { console.error("[Bootstrap] initTheme error:", e); }
    try { checkSystemHealth(); } catch (e) { console.error("[Bootstrap] checkSystemHealth error:", e); }
    try { loadRoster(); } catch (e) { console.error("[Bootstrap] loadRoster error:", e); }
    try { setupEventListeners(); } catch (e) { console.error("[Bootstrap] setupEventListeners error:", e); }
    try { setupDrugSafetyModalEvents(); } catch (e) { console.error("[Bootstrap] setupDrugSafetyModalEvents error:", e); }
    try { initSseConsumer(); } catch (e) { console.error("[Bootstrap] initSseConsumer error:", e); }

    const urlParams = new URLSearchParams(window.location.search);
    const explicitUrlPid = urlParams.get("patient") || urlParams.get("patientID") || urlParams.get("patient_id") || urlParams.get("idNo");
    if (explicitUrlPid) {
        state.userInitiatedReview = true;
    }
    const idInputEl = document.getElementById("patientIdInput");
    const dateInputEl = document.getElementById("clinicDateInput");
    const fallbackPid = state.lastPatientId || (idInputEl ? idInputEl.value.trim() : "") || "B100134889";
    const fallbackDt = state.lastQueryDate || (dateInputEl ? dateInputEl.value.trim() : "") || "1150721";
    const pid = explicitUrlPid || fallbackPid;
    const dt = formatRocDate(urlParams.get("date") || fallbackDt);
    const reqView = urlParams.get("view");
    const isStandalone = urlParams.get("standalone") === "1" || urlParams.get("standalone") === "true";
    const urlMeta = {
        chart_no: urlParams.get("chart_no") || urlParams.get("chartNo") || urlParams.get("hisno") || urlParams.get("mrn") || "",
        birth_date: urlParams.get("birth_date") || urlParams.get("birthdate") || urlParams.get("birthDate") || urlParams.get("birthday") || urlParams.get("dob") || "",
        age: urlParams.get("age") || urlParams.get("patientAge") || "",
        name: urlParams.get("name") || urlParams.get("patientName") || "",
        gender: urlParams.get("gender") || urlParams.get("sex") || "",
    };

    if (isStandalone) {
        document.body.classList.add("standalone-mode");
        const ind = document.getElementById("workspaceIndicatorText");
        if (ind) ind.innerHTML = '<i class="bi bi-arrows-fullscreen text-primary"></i> 獨立全寬檢視 (100% 版面)';
    }

    // Load initial patient: prefer explicit URL ?patient=..., then active /launch session, then last queried patient & date
    const applyInitialView = () => {
        if (reqView === "medications") {
            switchWorkspaceView("medications");
        } else if (reqView === "correlation") {
            switchWorkspaceView("correlation");
        } else if (reqView === "reports") {
            switchWorkspaceView("reports");
        } else if (reqView === "labs") {
            switchWorkspaceView("labs");
        }
    };

    if (explicitUrlPid) {
        loadPatientSummary(pid, dt, urlMeta).then(applyInitialView).catch(err => {
            console.error("[Bootstrap] loadPatientSummary error:", err);
        });
    } else {
        fetch("/api/launch/current", { cache: "no-store" })
            .then(r => r.json())
            .then(res => {
                if (res && res.last_query_date) {
                    state.lastQueryDate = formatRocDate(res.last_query_date);
                    try { localStorage.setItem("opd_last_query_date", state.lastQueryDate); } catch (e) {}
                }
                if (res && res.launch && res.launch.patient_id) {
                    handleIncomingLaunch(res.launch);
                    applyInitialView();
                } else if (!lastHandledLaunchSignature) {
                    const targetPid = state.lastPatientId || (res && res.last_patient_id) || pid;
                    const targetDt = formatRocDate(urlParams.get("date") || (res && res.last_query_date) || state.lastQueryDate || dt);
                    return loadPatientSummary(targetPid, targetDt, urlMeta).then(applyInitialView);
                }
            })
            .catch(() => {
                if (!lastHandledLaunchSignature) {
                    loadPatientSummary(pid, dt, urlMeta).then(applyInitialView).catch(err => {
                        console.error("[Bootstrap] loadPatientSummary error:", err);
                    });
                }
            });
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
} else {
    // DOM is already ready (e.g. cached module or deferred execution)
    bootstrap();
}
