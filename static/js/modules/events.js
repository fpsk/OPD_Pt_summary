/**
 * Wires all static DOM event listeners (tabs, toggles, filters, modals, chat).
 */
import { state } from "./state.js";
import { formatRocDate, isValidRocDate } from "./utils.js";
import { clearChatHistory, sendChatMessage, toggleChatDock } from "./chat.js";
import { applyCorrelationPreset, renderCorrelationPlot, setAllCorrCheckboxes } from "./correlation.js";
import { closeDrugPhotoModal, initDrugModalDraggable, toggleDrugModalExpand } from "./drug-photo.js";
import { renderLabFlowsheet, renderLabTable } from "./labs.js";
import { loadPatientSummary } from "./patient.js";
import { renderMedications } from "./meds.js";
import { renderRadiologyReports } from "./reports.js";
import { toggleTheme } from "./theme.js";
import { switchWorkspaceView } from "./workspace.js";

export function commitClinicDate(rawVal) {
    const raw = String(rawVal ?? "").trim();
    if (!isValidRocDate(raw)) return null;
    const norm = formatRocDate(raw);
    const prevDate = state.lastQueryDate || "";
    const dateEl = document.getElementById("clinicDateInput");
    if (dateEl && dateEl.value !== norm) {
        dateEl.value = norm;
    }
    state.lastQueryDate = norm;
    try { localStorage.setItem("opd_last_query_date", norm); } catch (err) {}
    if (norm !== prevDate) {
        fetch("/api/clinic-date", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ date: norm }),
        }).catch(() => {});
    }
    return norm;
}

export function setupEventListeners() {
    // Roster dropdown select (if present) — keep current sticky visit date
    const rosterSelect = document.getElementById("rosterSelect");
    if (rosterSelect) {
        rosterSelect.addEventListener("change", (e) => {
            const pid = e.target.value;
            if (pid) {
                state.userInitiatedReview = true;
                document.getElementById("patientIdInput").value = pid;
                const rawDate = document.getElementById("clinicDateInput")?.value?.trim() || state.lastQueryDate || "1150721";
                const date = commitClinicDate(rawDate) || formatRocDate(rawDate);
                loadPatientSummary(pid, date);
            }
        });
    }

    // Search button & inputs
    const searchBtn = document.getElementById("searchBtn");
    const patientIdInput = document.getElementById("patientIdInput");
    const clinicDateInput = document.getElementById("clinicDateInput");

    if (searchBtn && patientIdInput && clinicDateInput) {
        searchBtn.addEventListener("click", () => {
            const pid = patientIdInput.value.trim();
            const rawDate = clinicDateInput.value.trim() || state.lastQueryDate || "1150721";
            const date = commitClinicDate(rawDate) || formatRocDate(rawDate);
            if (pid) {
                state.userInitiatedReview = true;
                loadPatientSummary(pid, date);
            }
        });

        clinicDateInput.addEventListener("change", () => {
            commitClinicDate(clinicDateInput.value);
        });
        clinicDateInput.addEventListener("blur", () => {
            commitClinicDate(clinicDateInput.value);
        });

        // Enter key triggers search
        patientIdInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") searchBtn.click();
        });
        clinicDateInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") searchBtn.click();
        });
    }

    // Theme toggle
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", toggleTheme);
    }

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

    // Workspace Switching (Labs vs Reports vs Medications vs Correlation)
    const topChoiceLabs = document.getElementById("topbarChoiceLabs");
    const topChoiceReports = document.getElementById("topbarChoiceReports");
    const topChoiceMeds = document.getElementById("topbarChoiceMeds");
    const topChoiceCorr = document.getElementById("topbarChoiceCorrelation");

    const wsChoiceLabs = document.getElementById("wsChoiceLabs");
    const wsChoiceReports = document.getElementById("wsChoiceReports");
    const wsChoiceMeds = document.getElementById("wsChoiceMeds");
    const wsChoiceCorr = document.getElementById("wsChoiceCorrelation");

    if (topChoiceLabs) topChoiceLabs.addEventListener("click", () => switchWorkspaceView("labs"));
    if (topChoiceReports) topChoiceReports.addEventListener("click", () => switchWorkspaceView("reports"));
    if (topChoiceMeds) topChoiceMeds.addEventListener("click", () => switchWorkspaceView("medications"));
    if (topChoiceCorr) topChoiceCorr.addEventListener("click", () => switchWorkspaceView("correlation"));

    if (wsChoiceLabs) wsChoiceLabs.addEventListener("click", () => switchWorkspaceView("labs"));
    if (wsChoiceReports) wsChoiceReports.addEventListener("click", () => switchWorkspaceView("reports"));
    if (wsChoiceMeds) wsChoiceMeds.addEventListener("click", () => switchWorkspaceView("medications"));
    if (wsChoiceCorr) wsChoiceCorr.addEventListener("click", () => switchWorkspaceView("correlation"));

    // Sidebar Toggle (Full-Width View Mode)
    const btnToggleSidebar = document.getElementById("btnToggleSidebar");
    if (btnToggleSidebar) {
        btnToggleSidebar.addEventListener("click", () => {
            const isCollapsed = document.body.classList.toggle("sidebar-collapsed");
            const btnText = document.getElementById("btnToggleSidebarText");
            const ind = document.getElementById("workspaceIndicatorText");
            if (isCollapsed) {
                if (btnText) btnText.textContent = "還原側邊欄";
                btnToggleSidebar.innerHTML = '<i class="bi bi-layout-sidebar"></i> <span id="btnToggleSidebarText">還原側邊欄</span>';
                btnToggleSidebar.title = "展開問題清單側邊欄";
                if (ind) ind.innerHTML = '<i class="bi bi-arrows-fullscreen text-primary"></i> 全寬檢視 (100% 版面)';
            } else {
                if (btnText) btnText.textContent = "全寬模式 (無側邊欄)";
                btnToggleSidebar.innerHTML = '<i class="bi bi-layout-sidebar-inset"></i> <span id="btnToggleSidebarText">全寬模式 (無側邊欄)</span>';
                btnToggleSidebar.title = "收合側邊欄以擴展檢驗與用藥至全螢幕寬度";
                if (ind) ind.innerHTML = '<i class="bi bi-layout-split"></i> 主要工作區 (2.5/3.5 版面)';
            }
        });
    }

    // Distinct Popout Window (No Sidebar)
    const openPopout = () => {
        const currentPid = document.getElementById("patientSelector")?.value || "B100134889";
        const rawDt = document.getElementById("clinicDateInput")?.value?.trim() || "1150721";
        const currentDt = formatRocDate(rawDt);
        const currentView = state.currentWorkspaceView || "labs";
        const url = `/?patient=${encodeURIComponent(currentPid)}&date=${encodeURIComponent(currentDt)}&view=${encodeURIComponent(currentView)}&standalone=1`;
        const popHeight = 1248; // 130% of previous 960px
        const win = window.open(
            url,
            `DistinctLabMed_${currentPid}`,
            `width=1650,height=${popHeight},menubar=no,toolbar=no,location=no,status=no,resizable=yes,scrollbars=yes`
        );
        if (win) {
            win.focus();
        }
    };

    const btnPopoutWindow = document.getElementById("btnPopoutWindow");
    if (btnPopoutWindow) {
        btnPopoutWindow.addEventListener("click", openPopout);
    }
    const topbarPopoutBtn = document.getElementById("topbarPopoutBtn");
    if (topbarPopoutBtn) {
        topbarPopoutBtn.addEventListener("click", openPopout);
    }

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
    const openEmrNoteBtn = document.getElementById("openEmrNoteBtn");
    if (openEmrNoteBtn) {
        openEmrNoteBtn.addEventListener("click", () => {
            if (!state.currentPatientData) return;
            const emrTextarea = document.getElementById("emrNoteTextarea");
            if (emrTextarea) emrTextarea.value = state.currentPatientData.emr_preconsult_note || "";
            const copyMsg = document.getElementById("copySuccessMsg");
            if (copyMsg) copyMsg.classList.add("d-none");
            const emrModal = document.getElementById("emrModal");
            if (emrModal) emrModal.classList.remove("d-none");
        });
    }

    const closeEmrModalBtn = document.getElementById("closeEmrModalBtn");
    if (closeEmrModalBtn) {
        closeEmrModalBtn.addEventListener("click", () => {
            const emrModal = document.getElementById("emrModal");
            if (emrModal) emrModal.classList.add("d-none");
        });
    }

    const copyEmrBtn = document.getElementById("copyEmrBtn");
    if (copyEmrBtn) {
        copyEmrBtn.addEventListener("click", () => {
            const emrTextarea = document.getElementById("emrNoteTextarea");
            const text = emrTextarea ? emrTextarea.value : "";
            navigator.clipboard.writeText(text).then(() => {
                const copyMsg = document.getElementById("copySuccessMsg");
                if (copyMsg) {
                    copyMsg.classList.remove("d-none");
                    setTimeout(() => {
                        copyMsg.classList.add("d-none");
                    }, 3000);
                }
            });
        });
    }

    // AI Modal close
    const closeAiModalBtn = document.getElementById("closeAiModalBtn");
    if (closeAiModalBtn) {
        closeAiModalBtn.addEventListener("click", () => {
            const aiModal = document.getElementById("aiModal");
            if (aiModal) aiModal.classList.add("d-none");
        });
    }

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
