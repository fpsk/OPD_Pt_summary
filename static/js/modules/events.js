/**
 * Wires all static DOM event listeners (tabs, toggles, filters, modals, chat).
 */
import { state } from "./state.js";
import { clearChatHistory, sendChatMessage, toggleChatDock } from "./chat.js";
import { applyCorrelationPreset, renderCorrelationPlot, setAllCorrCheckboxes } from "./correlation.js";
import { closeDrugPhotoModal, initDrugModalDraggable, toggleDrugModalExpand } from "./drug-photo.js";
import { renderLabFlowsheet, renderLabTable } from "./labs.js";
import { loadPatientSummary } from "./patient.js";
import { renderMedications } from "./meds.js";
import { renderRadiologyReports } from "./reports.js";
import { toggleTheme } from "./theme.js";
import { switchWorkspaceView } from "./workspace.js";

export function setupEventListeners() {
    // Roster dropdown select (if present)
    const rosterSelect = document.getElementById("rosterSelect");
    if (rosterSelect) {
        rosterSelect.addEventListener("change", (e) => {
            const pid = e.target.value;
            if (pid) {
                document.getElementById("patientIdInput").value = pid;
                const date = document.getElementById("clinicDateInput").value.trim() || "2026/09/01";
                loadPatientSummary(pid, date);
            }
        });
    }

    // Search button
    document.getElementById("searchBtn").addEventListener("click", () => {
        const pid = document.getElementById("patientIdInput").value.trim();
        const date = document.getElementById("clinicDateInput").value.trim() || "2026/09/01";
        if (pid) {
            loadPatientSummary(pid, date);
        }
    });

    // Enter key triggers search
    document.getElementById("patientIdInput").addEventListener("keypress", (e) => {
        if (e.key === "Enter") document.getElementById("searchBtn").click();
    });
    document.getElementById("clinicDateInput").addEventListener("keypress", (e) => {
        if (e.key === "Enter") document.getElementById("searchBtn").click();
    });

    // Theme toggle
    document.getElementById("themeToggleBtn").addEventListener("click", toggleTheme);

    // Lab tabs (6 Physiological Systems + All)
    document.querySelectorAll("#labTabs .tab-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const targetBtn = e.target.closest(".tab-btn") || e.target;
            document.querySelectorAll("#labTabs .tab-btn").forEach(b => b.classList.remove("active"));
            targetBtn.classList.add("active");
            state.currentLabTab = targetBtn.dataset.tab || "all";
            if (state.currentPatientData && state.currentPatientData.findings) {
                renderLabTable(state.currentPatientData.findings.lab_panel, state.currentLabTab);
            }
        });
    });

    // Lab View Mode Toggle: Flowsheet (時序矩陣) vs List (清單檢視)
    const btnFlowsheet = document.getElementById("btnLabFlowsheet");
    const btnList = document.getElementById("btnLabList");
    const flowsheetWrapper = document.getElementById("labFlowsheetWrapper");
    const listWrapper = document.getElementById("labListWrapper");

    if (btnFlowsheet && btnList) {
        btnFlowsheet.addEventListener("click", () => {
            btnFlowsheet.classList.add("active");
            btnList.classList.remove("active");
            state.currentLabView = "flowsheet";
            if (flowsheetWrapper) flowsheetWrapper.classList.remove("d-none");
            if (listWrapper) listWrapper.classList.add("d-none");
            if (state.currentPatientData && state.currentPatientData.findings) {
                renderLabTable(state.currentPatientData.findings.lab_panel, state.currentLabTab);
            }
        });

        btnList.addEventListener("click", () => {
            btnList.classList.add("active");
            btnFlowsheet.classList.remove("active");
            state.currentLabView = "list";
            if (flowsheetWrapper) flowsheetWrapper.classList.add("d-none");
            if (listWrapper) listWrapper.classList.remove("d-none");
            if (state.currentPatientData && state.currentPatientData.findings) {
                renderLabTable(state.currentPatientData.findings.lab_panel, state.currentLabTab);
            }
        });
    }

    // Flowsheet Analyte Search Filter
    const flowsheetSearch = document.getElementById("flowsheetSearchInput");
    if (flowsheetSearch) {
        flowsheetSearch.addEventListener("input", (e) => {
            state.flowsheetFilterText = (e.target.value || "").trim().toLowerCase();
            if (state.currentPatientData && state.currentPatientData.findings && state.currentPatientData.findings.lab_panel) {
                renderLabFlowsheet(state.currentPatientData.findings.lab_panel.flowsheet, state.currentLabTab, state.flowsheetFilterText);
            }
        });
    }

    // Flowsheet Horizontal Quick Scrolling (Left: earlier results, Right: newest reports)
    const btnScrollLeft = document.getElementById("btnScrollLeft");
    const btnScrollRight = document.getElementById("btnScrollRight");
    const flowsheetContainer = document.getElementById("labFlowsheetContainer");
    const topTrack = document.getElementById("flowsheetTopScrollTrack");

    if (btnScrollLeft && flowsheetContainer) {
        btnScrollLeft.addEventListener("click", () => {
            flowsheetContainer.scrollTo({ left: 0, behavior: "smooth" });
        });
    }
    if (btnScrollRight && flowsheetContainer) {
        btnScrollRight.addEventListener("click", () => {
            flowsheetContainer.scrollTo({ left: flowsheetContainer.scrollWidth, behavior: "smooth" });
        });
    }

    // Two-way synchronization between Top Scroll Bar and Bottom Flowsheet Container
    if (topTrack && flowsheetContainer) {
        let isSyncingTop = false;
        let isSyncingBottom = false;

        topTrack.addEventListener("scroll", () => {
            if (isSyncingTop) {
                isSyncingTop = false;
                return;
            }
            isSyncingBottom = true;
            flowsheetContainer.scrollLeft = topTrack.scrollLeft;
        }, { passive: true });

        flowsheetContainer.addEventListener("scroll", () => {
            if (isSyncingBottom) {
                isSyncingBottom = false;
                return;
            }
            isSyncingTop = true;
            topTrack.scrollLeft = flowsheetContainer.scrollLeft;
        }, { passive: true });

        if (window.ResizeObserver) {
            const ro = new ResizeObserver(() => {
                const table = flowsheetContainer.querySelector(".table-flowsheet");
                const topDummy = document.getElementById("flowsheetTopScrollDummy");
                const topScrollBox = document.getElementById("flowsheetTopScrollContainer");
                if (table && topDummy) {
                    const totalW = table.scrollWidth || table.offsetWidth;
                    topDummy.style.width = totalW + "px";
                    if (topScrollBox) {
                        topScrollBox.style.display = totalW > flowsheetContainer.clientWidth ? "flex" : "none";
                    }
                }
            });
            ro.observe(flowsheetContainer);
        }
    }

    // Workspace Switching (Reports vs Medications vs Correlation)
    const topChoiceReports = document.getElementById("topbarChoiceReports");
    const topChoiceMeds = document.getElementById("topbarChoiceMeds");
    const topChoiceCorr = document.getElementById("topbarChoiceCorrelation");
    const wsChoiceReports = document.getElementById("wsChoiceReports");
    const wsChoiceMeds = document.getElementById("wsChoiceMeds");
    const wsChoiceCorr = document.getElementById("wsChoiceCorrelation");

    if (topChoiceReports) topChoiceReports.addEventListener("click", () => switchWorkspaceView("reports"));
    if (topChoiceMeds) topChoiceMeds.addEventListener("click", () => switchWorkspaceView("medications"));
    if (topChoiceCorr) topChoiceCorr.addEventListener("click", () => switchWorkspaceView("correlation"));
    if (wsChoiceReports) wsChoiceReports.addEventListener("click", () => switchWorkspaceView("reports"));
    if (wsChoiceMeds) wsChoiceMeds.addEventListener("click", () => switchWorkspaceView("medications"));
    if (wsChoiceCorr) wsChoiceCorr.addEventListener("click", () => switchWorkspaceView("correlation"));

    // Imaging tabs (All vs CT/MRI vs Endoscopy/PTA vs X-ray/Sono)
    document.querySelectorAll("#imagingTabs .tab-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll("#imagingTabs .tab-btn").forEach(b => b.classList.remove("active"));
            const target = e.currentTarget || e.target;
            target.classList.add("active");
            state.currentImagingTab = target.dataset.tab || "all";
            if (state.currentPatientData && state.currentPatientData.findings) {
                renderRadiologyReports(state.currentPatientData.findings.radiology_reports);
            }
        });
    });

    // Medication View Toggle: Timeline Graph vs List View
    const btnMedTimeline = document.getElementById("btnMedViewTimeline");
    const btnMedList = document.getElementById("btnMedViewList");
    const medTimelineWrapper = document.getElementById("medTimelineWrapper");
    const medListWrapper = document.getElementById("medListWrapper");

    if (btnMedTimeline && btnMedList) {
        btnMedTimeline.addEventListener("click", () => {
            btnMedTimeline.classList.add("active");
            btnMedList.classList.remove("active");
            state.currentMedView = "timeline";
            if (medTimelineWrapper) medTimelineWrapper.classList.remove("d-none");
            if (medListWrapper) medListWrapper.classList.add("d-none");
            if (state.currentPatientData && state.currentPatientData.medications) {
                renderMedications(state.currentPatientData.medications);
            }
        });

        btnMedList.addEventListener("click", () => {
            btnMedList.classList.add("active");
            btnMedTimeline.classList.remove("active");
            state.currentMedView = "list";
            if (medTimelineWrapper) medTimelineWrapper.classList.add("d-none");
            if (medListWrapper) medListWrapper.classList.remove("d-none");
            if (state.currentPatientData && state.currentPatientData.medications) {
                renderMedications(state.currentPatientData.medications);
            }
        });
    }

    // Medication Scope Filter Buttons (Active vs 6M vs All)
    document.querySelectorAll("#medFilterScopeGroup .tab-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll("#medFilterScopeGroup .tab-btn").forEach(b => b.classList.remove("active"));
            const target = e.currentTarget || e.target;
            target.classList.add("active");
            state.currentMedFilter = target.dataset.filter || "active";
            if (state.currentPatientData && state.currentPatientData.medications) {
                renderMedications(state.currentPatientData.medications);
            }
        });
    });

    // Real-time medication search filter
    const medSearchInput = document.getElementById("medSearchInput");
    if (medSearchInput) {
        medSearchInput.addEventListener("input", (e) => {
            state.medSearchQuery = (e.target.value || "").trim().toLowerCase();
            if (state.currentPatientData && state.currentPatientData.medications) {
                renderMedications(state.currentPatientData.medications);
            }
        });
    }

    // Medication Timeline Top Scrollbar Synchronization
    const medTopTrack = document.getElementById("medTopScrollTrack");
    const medContainer = document.getElementById("medTimelineContainer");
    if (medTopTrack && medContainer) {
        let isSyncingMedTop = false;
        let isSyncingMedBottom = false;

        medTopTrack.addEventListener("scroll", () => {
            if (isSyncingMedTop) {
                isSyncingMedTop = false;
                return;
            }
            isSyncingMedBottom = true;
            medContainer.scrollLeft = medTopTrack.scrollLeft;
        }, { passive: true });

        medContainer.addEventListener("scroll", () => {
            if (isSyncingMedBottom) {
                isSyncingMedBottom = false;
                return;
            }
            isSyncingMedTop = true;
            medTopTrack.scrollLeft = medContainer.scrollLeft;
        }, { passive: true });

        if (window.ResizeObserver) {
            const roMed = new ResizeObserver(() => {
                const table = medContainer.querySelector(".med-timeline-table");
                const topDummy = document.getElementById("medTopScrollDummy");
                const topScrollBox = document.getElementById("medTopScrollContainer");
                if (table && topDummy) {
                    const totalW = table.scrollWidth || table.offsetWidth;
                    topDummy.style.width = totalW + "px";
                    if (topScrollBox) {
                        topScrollBox.style.display = totalW > medContainer.clientWidth ? "flex" : "none";
                    }
                }
            });
            roMed.observe(medContainer);
        }
    }

    // Correlation Presets
    const btnPreGluc = document.getElementById("btnPresetGlucose");
    const btnPreRenal = document.getElementById("btnPresetRenal");
    const btnPreAnti = document.getElementById("btnPresetAntithrombotic");
    const btnPreLiv = document.getElementById("btnPresetLiver");
    const btnPreClr = document.getElementById("btnPresetClear");

    if (btnPreGluc) btnPreGluc.addEventListener("click", () => applyCorrelationPreset("glucose"));
    if (btnPreRenal) btnPreRenal.addEventListener("click", () => applyCorrelationPreset("renal"));
    if (btnPreAnti) btnPreAnti.addEventListener("click", () => applyCorrelationPreset("antithrombotic"));
    if (btnPreLiv) btnPreLiv.addEventListener("click", () => applyCorrelationPreset("liver"));
    if (btnPreClr) btnPreClr.addEventListener("click", () => applyCorrelationPreset("clear"));

    // Selection buttons
    const btnSelAllLabs = document.getElementById("btnSelectAllLabs");
    const btnClrLabs = document.getElementById("btnClearLabs");
    const btnSelAllMeds = document.getElementById("btnSelectAllMeds");
    const btnClrMeds = document.getElementById("btnClearMeds");

    if (btnSelAllLabs) btnSelAllLabs.addEventListener("click", () => setAllCorrCheckboxes("labs", true));
    if (btnClrLabs) btnClrLabs.addEventListener("click", () => setAllCorrCheckboxes("labs", false));
    if (btnSelAllMeds) btnSelAllMeds.addEventListener("click", () => setAllCorrCheckboxes("meds", true));
    if (btnClrMeds) btnClrMeds.addEventListener("click", () => setAllCorrCheckboxes("meds", false));

    // Execution button
    const btnExec = document.getElementById("btnExecuteCorrelationPlot");
    if (btnExec) btnExec.addEventListener("click", () => renderCorrelationPlot());

    // Toggle collapse button
    const btnToggleCollapse = document.getElementById("btnToggleSelectorCollapse");
    const corrSelectorBody = document.getElementById("corrSelectorBody");
    if (btnToggleCollapse && corrSelectorBody) {
        btnToggleCollapse.addEventListener("click", () => {
            corrSelectorBody.classList.toggle("collapsed");
            const isCol = corrSelectorBody.classList.contains("collapsed");
            btnToggleCollapse.innerHTML = isCol ? '<i class="bi bi-chevron-down"></i> 展開選單' : '<i class="bi bi-chevron-up"></i> 收合選單';
        });
    }

    // Search filters in selector
    const labSearch = document.getElementById("corrLabSearchInput");
    if (labSearch) {
        labSearch.addEventListener("input", (e) => {
            const q = (e.target.value || "").trim().toLowerCase();
            document.querySelectorAll("#corrLabListContainer .corr-var-label").forEach(lbl => {
                const name = lbl.dataset.name || "";
                lbl.style.display = (!q || name.includes(q)) ? "flex" : "none";
            });
        });
    }

    const medSearch = document.getElementById("corrMedSearchInput");
    if (medSearch) {
        medSearch.addEventListener("input", (e) => {
            const q = (e.target.value || "").trim().toLowerCase();
            document.querySelectorAll("#corrMedListContainer .corr-var-label").forEach(lbl => {
                const name = lbl.dataset.name || "";
                lbl.style.display = (!q || name.includes(q)) ? "flex" : "none";
            });
        });
    }

    // Synchronize Top Scrollbar for Correlation Timeline
    const corrTopTrack = document.getElementById("corrTopScrollTrack");
    const corrContainer = document.getElementById("corrTimelineContainer");
    if (corrTopTrack && corrContainer) {
        let isSyncingCorrTop = false;
        let isSyncingCorrBottom = false;

        corrTopTrack.addEventListener("scroll", () => {
            if (isSyncingCorrTop) {
                isSyncingCorrTop = false;
                return;
            }
            isSyncingCorrBottom = true;
            corrContainer.scrollLeft = corrTopTrack.scrollLeft;
        }, { passive: true });

        corrContainer.addEventListener("scroll", () => {
            if (isSyncingCorrBottom) {
                isSyncingCorrBottom = false;
                return;
            }
            isSyncingCorrTop = true;
            corrTopTrack.scrollLeft = corrContainer.scrollLeft;
        }, { passive: true });

        if (window.ResizeObserver) {
            const roCorr = new ResizeObserver(() => {
                const table = corrContainer.querySelector(".med-timeline-table");
                const topDummy = document.getElementById("corrTopScrollDummy");
                const topScrollBox = document.getElementById("corrTopScrollContainer");
                if (table && topDummy) {
                    const totalW = table.scrollWidth || table.offsetWidth;
                    topDummy.style.width = totalW + "px";
                    if (topScrollBox) {
                        topScrollBox.style.display = totalW > corrContainer.clientWidth ? "flex" : "none";
                    }
                }
            });
            roCorr.observe(corrContainer);
        }
    }

    // EMR Note Modal
    document.getElementById("openEmrNoteBtn").addEventListener("click", () => {
        if (!state.currentPatientData) return;
        document.getElementById("emrNoteTextarea").value = state.currentPatientData.emr_preconsult_note || "";
        document.getElementById("copySuccessMsg").classList.add("d-none");
        document.getElementById("emrModal").classList.remove("d-none");
    });
    document.getElementById("closeEmrModalBtn").addEventListener("click", () => {
        document.getElementById("emrModal").classList.add("d-none");
    });
    document.getElementById("copyEmrBtn").addEventListener("click", () => {
        const text = document.getElementById("emrNoteTextarea").value;
        navigator.clipboard.writeText(text).then(() => {
            document.getElementById("copySuccessMsg").classList.remove("d-none");
            setTimeout(() => {
                document.getElementById("copySuccessMsg").classList.add("d-none");
            }, 3000);
        });
    });

    // AI Modal close
    document.getElementById("closeAiModalBtn").addEventListener("click", () => {
        document.getElementById("aiModal").classList.add("d-none");
    });

    // Drug Photo Modal close & controls
    const closeDrugBtn = document.getElementById("closeDrugPhotoModalBtn");
    if (closeDrugBtn) closeDrugBtn.addEventListener("click", closeDrugPhotoModal);
    const closeDrugFooterBtn = document.getElementById("closeDrugPhotoModalFooterBtn");
    if (closeDrugFooterBtn) closeDrugFooterBtn.addEventListener("click", closeDrugPhotoModal);
    const expandDrugBtn = document.getElementById("expandDrugPhotoModalBtn");
    if (expandDrugBtn) expandDrugBtn.addEventListener("click", toggleDrugModalExpand);
    initDrugModalDraggable();

    // Keyboard ESC to close floating drug photo window
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            const drugModal = document.getElementById("drugPhotoModal");
            if (drugModal && !drugModal.classList.contains("d-none")) {
                closeDrugPhotoModal();
            }
        }
    });

    // Condition Tabs (Acute vs Chronic vs All)
    const tabAcute = document.getElementById("tabAcuteCond");
    const tabChronic = document.getElementById("tabChronicCond");
    const tabAll = document.getElementById("tabAllCond");
    const acuteSec = document.getElementById("acuteSection");
    const chronicSec = document.getElementById("chronicSection");
    const acuteSecHeader = document.getElementById("acuteSectionHeader");
    const chronicSecHeader = document.getElementById("chronicSectionHeader");

    if (tabAcute && tabChronic && tabAll) {
        tabAcute.addEventListener("click", () => {
            tabAcute.classList.add("active");
            tabChronic.classList.remove("active");
            tabAll.classList.remove("active");
            if (acuteSec) acuteSec.classList.remove("d-none");
            if (chronicSec) chronicSec.classList.add("d-none");
            if (acuteSecHeader) acuteSecHeader.classList.add("d-none");
        });
        tabChronic.addEventListener("click", () => {
            tabChronic.classList.add("active");
            tabAcute.classList.remove("active");
            tabAll.classList.remove("active");
            if (acuteSec) acuteSec.classList.add("d-none");
            if (chronicSec) chronicSec.classList.remove("d-none");
            if (chronicSecHeader) chronicSecHeader.classList.add("d-none");
        });
        tabAll.addEventListener("click", () => {
            tabAll.classList.add("active");
            tabAcute.classList.remove("active");
            tabChronic.classList.remove("active");
            if (acuteSec) acuteSec.classList.remove("d-none");
            if (chronicSec) chronicSec.classList.remove("d-none");
            if (acuteSecHeader) acuteSecHeader.classList.remove("d-none");
            if (chronicSecHeader) chronicSecHeader.classList.remove("d-none");
        });
    }

    // Clinical Chat Dock Controls
    const chatDockHeader = document.getElementById("chatDockHeader");
    if (chatDockHeader) {
        chatDockHeader.addEventListener("click", (e) => {
            if (e.target.closest("#clearChatBtn") || e.target.closest(".chat-btn-action:not(#toggleChatBtn)")) {
                return; // Don't toggle dock if action button clicked
            }
            toggleChatDock();
        });
    }

    const clearChatBtn = document.getElementById("clearChatBtn");
    if (clearChatBtn) {
        clearChatBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            clearChatHistory();
        });
    }

    const sendChatBtn = document.getElementById("sendChatBtn");
    if (sendChatBtn) {
        sendChatBtn.addEventListener("click", sendChatMessage);
    }

    const chatInput = document.getElementById("chatInput");
    if (chatInput) {
        chatInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                sendChatMessage();
            }
        });
    }

    // Quick Inquiry Chips
    document.querySelectorAll(".chat-chip").forEach(chip => {
        chip.addEventListener("click", (e) => {
            const query = e.target.dataset.query;
            if (query) {
                toggleChatDock(true); // Ensure expanded
                const input = document.getElementById("chatInput");
                if (input) input.value = query;
                sendChatMessage();
            }
        });
    });
}
