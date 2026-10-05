/**
 * Shared mutable UI state. Modules import this object and mutate its fields
 * (ES module bindings are read-only, so plain `let` globals can't be shared).
 */
export const state = {
    currentPatientData: null,
    currentLabTab: "all",
    currentLabView: "flowsheet",  // Default to Flowsheet matrix table
    flowsheetFilterText: "",
    currentImagingTab: "all",
    currentMedView: "timeline",  // "timeline" (Default) or "list"
    currentMedFilter: "all",  // "all" (Default to show all drugs) or "active" or "6m"
    medSearchQuery: "",
    currentWorkspaceView: "reports",  // "reports", "medications", or "correlation"
    chatHistory: [],
    selectedCorrLabs: new Set(),
    selectedCorrMeds: new Set(),
    corrSelectorsInitialized: false,
};
