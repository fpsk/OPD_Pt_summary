/**
 * Shared mutable UI state. Modules import this object and mutate its fields
 * (ES module bindings are read-only, so plain `let` globals can't be shared).
 */
function _safeStorageGet(key) {
    try {
        return (typeof localStorage !== "undefined" && localStorage.getItem(key)) || "";
    } catch {
        return "";
    }
}

export const state = {
    currentPatientData: null,
    lastQueryDate: _safeStorageGet("opd_last_query_date"),
    lastPatientId: _safeStorageGet("opd_last_patient_id"),
    userInitiatedReview: false,
    currentLabTab: "all",
    currentLabView: "flowsheet",  // Default to Flowsheet matrix table
    flowsheetFilterText: "",
    currentImagingTab: "all",
    currentMedView: "timeline",  // "timeline" (Default) or "list"
    currentMedFilter: "all",  // "all" (Default to show all drugs) or "active" or "6m"
    medSearchQuery: "",
    currentWorkspaceView: "labs",  // "labs", "reports", "medications", or "correlation"
    chatHistory: [],
    selectedCorrLabs: new Set(),
    selectedCorrMeds: new Set(),
    corrSelectorsInitialized: false,
};
