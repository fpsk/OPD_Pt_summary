/**
 * Switches the main 2.5/3.5 workspace between Labs, Reports, Medications and Correlation.
 */
import { state } from "./state.js";
import { initCorrelationSelectors } from "./correlation.js";

/**
 * Switch workspace view between Labs, Reports, Medications, and Correlation Plot
 */
export function switchWorkspaceView(view) {
    state.currentWorkspaceView = view;
    const wsLabs = document.getElementById("workspaceLabs");
    const wsReports = document.getElementById("workspaceReports");
    const wsMeds = document.getElementById("workspaceMedications");
    const wsCorr = document.getElementById("workspaceCorrelation");

    const topChoiceLabs = document.getElementById("topbarChoiceLabs");
    const topChoiceReports = document.getElementById("topbarChoiceReports");
    const topChoiceMeds = document.getElementById("topbarChoiceMeds");
    const topChoiceCorr = document.getElementById("topbarChoiceCorrelation");

    const wsChoiceLabs = document.getElementById("wsChoiceLabs");
    const wsChoiceReports = document.getElementById("wsChoiceReports");
    const wsChoiceMeds = document.getElementById("wsChoiceMeds");
    const wsChoiceCorr = document.getElementById("wsChoiceCorrelation");

    // Hide all panes
    if (wsLabs) wsLabs.classList.add("d-none");
    if (wsReports) wsReports.classList.add("d-none");
    if (wsMeds) wsMeds.classList.add("d-none");
    if (wsCorr) wsCorr.classList.add("d-none");

    // Reset button states
    [topChoiceLabs, topChoiceReports, topChoiceMeds, topChoiceCorr,
     wsChoiceLabs, wsChoiceReports, wsChoiceMeds, wsChoiceCorr].forEach(btn => {
        if (btn) btn.classList.remove("active");
    });

    if (view === "labs") {
        if (wsLabs) wsLabs.classList.remove("d-none");
        if (topChoiceLabs) topChoiceLabs.classList.add("active");
        if (wsChoiceLabs) wsChoiceLabs.classList.add("active");

        const flowsheetContainer = document.getElementById("labFlowsheetContainer");
        const topTrack = document.getElementById("flowsheetTopScrollTrack");
        if (flowsheetContainer) {
            setTimeout(() => {
                flowsheetContainer.scrollLeft = flowsheetContainer.scrollWidth;
                if (topTrack) topTrack.scrollLeft = topTrack.scrollWidth;
            }, 50);
        }
    } else if (view === "reports") {
        if (wsReports) wsReports.classList.remove("d-none");
        if (topChoiceReports) topChoiceReports.classList.add("active");
        if (wsChoiceReports) wsChoiceReports.classList.add("active");
    } else if (view === "medications") {
        if (wsMeds) wsMeds.classList.remove("d-none");
        if (topChoiceMeds) topChoiceMeds.classList.add("active");
        if (wsChoiceMeds) wsChoiceMeds.classList.add("active");

        const medContainer = document.getElementById("medTimelineContainer");
        const medTopTrack = document.getElementById("medTopScrollTrack");
        if (medContainer) {
            setTimeout(() => {
                medContainer.scrollLeft = medContainer.scrollWidth;
                if (medTopTrack) medTopTrack.scrollLeft = medTopTrack.scrollWidth;
            }, 50);
        }
    } else if (view === "correlation") {
        if (wsCorr) wsCorr.classList.remove("d-none");
        if (topChoiceCorr) topChoiceCorr.classList.add("active");
        if (wsChoiceCorr) wsChoiceCorr.classList.add("active");

        if (!state.corrSelectorsInitialized && state.currentPatientData) {
            initCorrelationSelectors();
        }

        const corrContainer = document.getElementById("corrTimelineContainer");
        const corrTopTrack = document.getElementById("corrTopScrollTrack");
        if (corrContainer) {
            setTimeout(() => {
                corrContainer.scrollLeft = corrContainer.scrollWidth;
                if (corrTopTrack) corrTopTrack.scrollLeft = corrTopTrack.scrollWidth;
            }, 50);
        }
    }
}
