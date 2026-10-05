/**
 * OPD Patient Clinical Summarizer - frontend entry point (bootstrap only).
 * Feature code lives in ./modules/*.js; shared mutable state in modules/state.js.
 */
import { setupEventListeners } from "./modules/events.js";
import { checkSystemHealth, loadPatientSummary, loadRoster } from "./modules/patient.js";
import { initTheme } from "./modules/theme.js";
import { switchWorkspaceView } from "./modules/workspace.js";
import { openDrugPhotoModalFromBtn } from "./modules/drug-photo.js";
import { toggleRawReport, triggerAiExtract } from "./modules/reports.js";

// Functions invoked from inline onclick="..." attributes in generated HTML.
// ES modules don't create globals, so expose exactly these on window.
Object.assign(window, { openDrugPhotoModalFromBtn, toggleRawReport, triggerAiExtract });

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    checkSystemHealth();
    loadRoster();
    setupEventListeners();

    const urlParams = new URLSearchParams(window.location.search);
    const pid = urlParams.get("patient") || "B100134889";
    const dt = urlParams.get("date") || "2026/09/01";
    const reqView = urlParams.get("view");

    // Load initial patient (using international standard date)
    loadPatientSummary(pid, dt).then(() => {
        if (reqView === "medications") {
            switchWorkspaceView("medications");
        } else if (reqView === "correlation") {
            switchWorkspaceView("correlation");
        }
    });
});
