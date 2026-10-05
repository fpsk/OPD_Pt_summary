/**
 * OPD Patient Clinical Summarizer - Frontend Controller
 * Workspace: d:/Antigravity_workspace/Summaries
 */

let currentPatientData = null;
let currentLabTab = "all";
let currentLabView = "flowsheet"; // Default to Flowsheet matrix table
let flowsheetFilterText = "";
let currentImagingTab = "all";
let showActiveMeds = true;
let currentMedView = "timeline"; // "timeline" (Default) or "list"
let currentMedFilter = "all"; // "all" (Default to show all drugs) or "active" or "6m"
let medSearchQuery = "";
let currentWorkspaceView = "reports"; // "reports", "medications", or "correlation"
let chatHistory = [];
let selectedCorrLabs = new Set();
let selectedCorrMeds = new Set();
let corrSelectorsInitialized = false;

/**
 * Parse lab reference range string (e.g. "[70][100]", "0.6-1.2", "< 140", "> 60")
 */
function parseRefRange(refStr) {
    if (!refStr) return { low: null, high: null };
    const s = String(refStr).trim();
    let m = s.match(/\[([0-9.]+)\s*\]\s*\[([0-9.]+)\s*\]/);
    if (m) return { low: parseFloat(m[1]), high: parseFloat(m[2]) };
    m = s.match(/([0-9.]+)\s*[-~至–—]\s*([0-9.]+)/);
    if (m) return { low: parseFloat(m[1]), high: parseFloat(m[2]) };
    m = s.match(/(?:<=|[<≤])\s*([0-9.]+)/);
    if (m) return { low: 0, high: parseFloat(m[1]) };
    m = s.match(/(?:>=|[>≥])\s*([0-9.]+)/);
    if (m) return { low: parseFloat(m[1]), high: null };
    return { low: null, high: null };
}

/**
 * Parse standard YYYY/MM/DD or other date string to JavaScript Date object
 */
function parseStandardDate(str) {
    if (!str) return null;
    const std = formatStandardDate(str);
    if (!std) return null;
    const parts = std.split("/");
    if (parts.length === 3) {
        const y = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10) - 1;
        const d = parseInt(parts[2], 10);
        if (!isNaN(y) && !isNaN(m) && !isNaN(d)) {
            const dt = new Date(y, m, d);
            return isNaN(dt.getTime()) ? null : dt;
        }
    }
    const dt = new Date(str);
    return isNaN(dt.getTime()) ? null : dt;
}

/**
 * Format any date string or ROC year to International Standard (YYYY/MM/DD or YYYY)
 */
function formatStandardDate(d) {
    if (!d) return "";
    let s = String(d).trim();
    if (/^\d{4}[\/\-]\d{2}[\/\-]\d{2}$/.test(s)) {
        return s.replace(/-/g, "/");
    }
    if (/^\d{4}$/.test(s)) {
        return s;
    }
    if (/^\d{8}$/.test(s)) {
        return `${s.substring(0, 4)}/${s.substring(4, 6)}/${s.substring(6, 8)}`;
    }
    if (/^\d{7}$/.test(s)) {
        const y = parseInt(s.substring(0, 3), 10) + 1911;
        return `${y}/${s.substring(3, 5)}/${s.substring(5, 7)}`;
    }
    if (/^\d{6}$/.test(s)) {
        const y = parseInt(s.substring(0, 2), 10) + 1911;
        return `${y}/${s.substring(2, 4)}/${s.substring(4, 6)}`;
    }
    const rocSlash = s.match(/^(\d{2,3})[\/\-](\d{1,2})[\/\-](\d{1,2})$/);
    if (rocSlash) {
        const y = parseInt(rocSlash[1], 10) + 1911;
        const m = rocSlash[2].padStart(2, "0");
        const day = rocSlash[3].padStart(2, "0");
        return `${y}/${m}/${day}`;
    }
    if (/^\d{2,3}$/.test(s)) {
        return String(parseInt(s, 10) + 1911);
    }
    return s;
}

/**
 * Format date dropping the century '20' (e.g. 2026/06/11 -> 26/06/11)
 */
function formatShortDate(d) {
    if (!d) return "";
    let std = formatStandardDate(d);
    return std.replace(/^20(\d{2})[\/\-]/, '$1/');
}

/**
 * Switch workspace view between Reports (2/3 width), Medications (2/3 width), and Correlation Plot (2/3 width)
 */
function switchWorkspaceView(view) {
    currentWorkspaceView = view;
    const wsReports = document.getElementById("workspaceReports");
    const wsMeds = document.getElementById("workspaceMedications");
    const wsCorr = document.getElementById("workspaceCorrelation");
    const topChoiceReports = document.getElementById("topbarChoiceReports");
    const topChoiceMeds = document.getElementById("topbarChoiceMeds");
    const topChoiceCorr = document.getElementById("topbarChoiceCorrelation");
    const wsChoiceReports = document.getElementById("wsChoiceReports");
    const wsChoiceMeds = document.getElementById("wsChoiceMeds");
    const wsChoiceCorr = document.getElementById("wsChoiceCorrelation");

    // Hide all panes
    if (wsReports) wsReports.classList.add("d-none");
    if (wsMeds) wsMeds.classList.add("d-none");
    if (wsCorr) wsCorr.classList.add("d-none");

    // Reset button states
    [topChoiceReports, topChoiceMeds, topChoiceCorr, wsChoiceReports, wsChoiceMeds, wsChoiceCorr].forEach(btn => {
        if (btn) btn.classList.remove("active");
    });

    if (view === "reports") {
        if (wsReports) wsReports.classList.remove("d-none");
        if (topChoiceReports) topChoiceReports.classList.add("active");
        if (wsChoiceReports) wsChoiceReports.classList.add("active");

        const flowsheetContainer = document.getElementById("labFlowsheetContainer");
        const topTrack = document.getElementById("flowsheetTopScrollTrack");
        if (flowsheetContainer) {
            setTimeout(() => {
                flowsheetContainer.scrollLeft = flowsheetContainer.scrollWidth;
                if (topTrack) topTrack.scrollLeft = topTrack.scrollWidth;
            }, 50);
        }
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

        if (!corrSelectorsInitialized && currentPatientData) {
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

function initTheme() {
    const savedTheme = localStorage.getItem("opd_theme") || "theme-light";
    document.body.className = savedTheme;
    const toggleBtn = document.getElementById("themeToggleBtn");
    if (toggleBtn) {
        toggleBtn.innerHTML = savedTheme === "theme-dark" ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
    }
}

function toggleTheme() {
    const isDark = document.body.classList.contains("theme-dark");
    const newTheme = isDark ? "theme-light" : "theme-dark";
    document.body.className = newTheme;
    localStorage.setItem("opd_theme", newTheme);
    const toggleBtn = document.getElementById("themeToggleBtn");
    if (toggleBtn) {
        toggleBtn.innerHTML = newTheme === "theme-dark" ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
    }
}

async function checkSystemHealth() {
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

async function loadRoster() {
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
    } catch (e) {
        select.innerHTML = '<option value="">名冊載入失敗</option>';
    }
}

function setupEventListeners() {
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
            currentLabTab = targetBtn.dataset.tab || "all";
            if (currentPatientData && currentPatientData.findings) {
                renderLabTable(currentPatientData.findings.lab_panel, currentLabTab);
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
            currentLabView = "flowsheet";
            if (flowsheetWrapper) flowsheetWrapper.classList.remove("d-none");
            if (listWrapper) listWrapper.classList.add("d-none");
            if (currentPatientData && currentPatientData.findings) {
                renderLabTable(currentPatientData.findings.lab_panel, currentLabTab);
            }
        });

        btnList.addEventListener("click", () => {
            btnList.classList.add("active");
            btnFlowsheet.classList.remove("active");
            currentLabView = "list";
            if (flowsheetWrapper) flowsheetWrapper.classList.add("d-none");
            if (listWrapper) listWrapper.classList.remove("d-none");
            if (currentPatientData && currentPatientData.findings) {
                renderLabTable(currentPatientData.findings.lab_panel, currentLabTab);
            }
        });
    }

    // Flowsheet Analyte Search Filter
    const flowsheetSearch = document.getElementById("flowsheetSearchInput");
    if (flowsheetSearch) {
        flowsheetSearch.addEventListener("input", (e) => {
            flowsheetFilterText = (e.target.value || "").trim().toLowerCase();
            if (currentPatientData && currentPatientData.findings && currentPatientData.findings.lab_panel) {
                renderLabFlowsheet(currentPatientData.findings.lab_panel.flowsheet, currentLabTab, flowsheetFilterText);
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
            currentImagingTab = target.dataset.tab || "all";
            if (currentPatientData && currentPatientData.findings) {
                renderRadiologyReports(currentPatientData.findings.radiology_reports);
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
            currentMedView = "timeline";
            if (medTimelineWrapper) medTimelineWrapper.classList.remove("d-none");
            if (medListWrapper) medListWrapper.classList.add("d-none");
            if (currentPatientData && currentPatientData.medications) {
                renderMedications(currentPatientData.medications);
            }
        });

        btnMedList.addEventListener("click", () => {
            btnMedList.classList.add("active");
            btnMedTimeline.classList.remove("active");
            currentMedView = "list";
            if (medTimelineWrapper) medTimelineWrapper.classList.add("d-none");
            if (medListWrapper) medListWrapper.classList.remove("d-none");
            if (currentPatientData && currentPatientData.medications) {
                renderMedications(currentPatientData.medications);
            }
        });
    }

    // Medication Scope Filter Buttons (Active vs 6M vs All)
    document.querySelectorAll("#medFilterScopeGroup .tab-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll("#medFilterScopeGroup .tab-btn").forEach(b => b.classList.remove("active"));
            const target = e.currentTarget || e.target;
            target.classList.add("active");
            currentMedFilter = target.dataset.filter || "active";
            if (currentPatientData && currentPatientData.medications) {
                renderMedications(currentPatientData.medications);
            }
        });
    });

    // Real-time medication search filter
    const medSearchInput = document.getElementById("medSearchInput");
    if (medSearchInput) {
        medSearchInput.addEventListener("input", (e) => {
            medSearchQuery = (e.target.value || "").trim().toLowerCase();
            if (currentPatientData && currentPatientData.medications) {
                renderMedications(currentPatientData.medications);
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
        if (!currentPatientData) return;
        document.getElementById("emrNoteTextarea").value = currentPatientData.emr_preconsult_note || "";
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

async function loadPatientSummary(patientId, clinicDate) {
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

        currentPatientData = data;
        renderAll(data);
    } catch (e) {
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 查詢摘要';
        alert("連線或伺服器發生錯誤：" + e);
    }
}

function renderAll(data) {
    renderPatientBanner(data);
    renderConditions(data.conditions);
    renderLabTable(data.findings.lab_panel, currentLabTab);
    renderRadiologyReports(data.findings.radiology_reports);
    renderMedications(data.medications);
    corrSelectorsInitialized = false;
    if (currentWorkspaceView === "correlation") {
        initCorrelationSelectors();
    }
}

function renderPatientBanner(data) {
    const prof = data.profile || {};
    const rosterSelect = document.getElementById("rosterSelect");
    const selectedOption = rosterSelect ? rosterSelect.options[rosterSelect.selectedIndex] : null;

    let name = prof.name ? prof.name : ("病患 " + data.patient_id);
    let genderAge = (prof.gender || prof.age) ? `${prof.gender || ''} / ${prof.age || ''} 歲` : ("身分證號: " + data.patient_id);
    let chartNo = prof.chart_no ? ("病歷號: " + prof.chart_no) : ("門診日: " + formatStandardDate(data.clinic_date));

    if (selectedOption && selectedOption.value === data.patient_id) {
        const match = selectedOption.textContent.match(/^\d+\.\s*(.*?)\s*\((.*?)\)\s*-\s*(.*)$/);
        if (match) {
            name = match[1] || name;
            genderAge = match[2] || genderAge;
            chartNo = "病歷號: " + (selectedOption.dataset.chartNo || prof.chart_no || "--");
        }
    }

    document.getElementById("ptName").textContent = name;
    document.getElementById("ptGenderAge").textContent = genderAge;
    document.getElementById("ptChartNo").textContent = chartNo;
    document.getElementById("ptIdNo").textContent = "ID: " + data.patient_id;

    // Update Chat Patient Pill
    const chatPill = document.getElementById("chatPatientPill");
    if (chatPill) {
        chatPill.textContent = `病患: ${data.patient_id} (${name})`;
    }

    // Render clinical badges
    const badgesContainer = document.getElementById("clinicalBadgesContainer");
    badgesContainer.innerHTML = "";
    (prof.badges || []).forEach(b => {
        const span = document.createElement("span");
        span.className = `badge badge-${b.color || 'primary'}`;
        span.textContent = b.label;
        badgesContainer.appendChild(span);
    });

    // Render Key Metrics
    updateMetricCard("metricEgfr", prof.egfr, "mL/min", prof.egfr !== null && prof.egfr < 15);
    updateMetricCard("metricCr", prof.creatinine, "mg/dL", prof.creatinine !== null && prof.creatinine > 1.3);
    updateMetricCard("metricHb", prof.hb, "g/dL", prof.hb !== null && prof.hb < 10.0);
    updateMetricCard("metricGlucose", prof.glucose, "mg/dL", prof.glucose !== null && prof.glucose > 140);
}

function updateMetricCard(elemId, value, unit, isCritical) {
    const card = document.getElementById(elemId);
    if (!card) return;
    const valElem = card.querySelector(".metric-value");
    if (value !== undefined && value !== null) {
        valElem.textContent = value;
        if (isCritical) {
            card.classList.add("metric-critical");
        } else {
            card.classList.remove("metric-critical");
        }
    } else {
        valElem.textContent = "--";
        card.classList.remove("metric-critical");
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatIcd(code) {
    if (!code) return "";
    let c = String(code).trim().toUpperCase();
    if (/^[A-Z][0-9]{3,}$/.test(c) && !c.includes(".")) {
        return c.substring(0, 3) + "." + c.substring(3);
    }
    return c;
}

function renderConditions(conditions) {
    const acuteList = document.getElementById("acuteConditionList");
    const chronicList = document.getElementById("chronicConditionList");
    const surgList = document.getElementById("surgeryList");

    if (acuteList) acuteList.innerHTML = "";
    if (chronicList) chronicList.innerHTML = "";
    if (surgList) surgList.innerHTML = "";

    const acuteItems = conditions.acute_diagnoses || [];
    const chronicItems = conditions.chronic_diagnoses || [];
    const surgeries = conditions.surgical_procedures || [];

    const acuteCountElem = document.getElementById("acuteCount");
    const chronicCountElem = document.getElementById("chronicCount");
    const totalCountElem = document.getElementById("totalDiagCount");
    if (acuteCountElem) acuteCountElem.textContent = acuteItems.length;
    if (chronicCountElem) chronicCountElem.textContent = chronicItems.length;
    if (totalCountElem) totalCountElem.textContent = acuteItems.length + chronicItems.length;
    const surgCountElem = document.getElementById("surgeryCount");
    if (surgCountElem) surgCountElem.textContent = surgeries.length;

    // 1. Render Acute Diagnoses: Compact Date Badge + Detail Description + ICD-10 (No extra category badges)
    if (acuteList) {
        if (acuteItems.length === 0) {
            acuteList.innerHTML = '<li class="empty-state">近期無急性診斷紀錄</li>';
        } else {
            acuteItems.forEach(a => {
                const li = document.createElement("li");
                li.className = "diag-row diag-acute-row";
                const icd = formatIcd(a.code);
                const diagDate = formatStandardDate(a.date) || '近期';
                const inst = a.hospital || a.institute || (a.hospitals && a.hospitals.length > 0 ? a.hospitals[0] : "");
                const otherInsts = (a.hospitals && a.hospitals.length > 1) ? ` (曾開立院所: ${a.hospitals.join('、')})` : '';

                const tooltipLines = [
                    `【急性診斷】${a.name}`,
                    `診斷/開立院所 (Institute): ${inst || '本院門診'}${otherInsts}`,
                    `就診/記錄日 (Date): ${diagDate}`,
                    `專科類別 (Category): ${a.category || '急性'}`,
                    `ICD-10 診斷碼: ${icd || '-'}`
                ];
                li.title = tooltipLines.join('\n');
                if (inst) li.dataset.institute = inst;

                li.innerHTML = `
                    <span class="diag-date-badge">${escapeHtml(diagDate)}</span>
                    <span class="diag-desc-text">${escapeHtml(a.name)}</span>
                    ${icd ? `<span class="diag-icd-badge">${escapeHtml(icd)}</span>` : ''}
                `;
                acuteList.appendChild(li);
            });
        }
    }

    // 2. Render Chronic Diagnoses: Compact Bullet + Detail Description + ICD-10 (grouped by specialty)
    if (chronicList) {
        if (chronicItems.length === 0) {
            chronicList.innerHTML = '<li class="empty-state">尚無慢性診斷清單</li>';
        } else {
            // Group by specialty category
            const groups = {};
            chronicItems.forEach(c => {
                const cat = c.category || '一般慢性追蹤';
                if (!groups[cat]) groups[cat] = [];
                groups[cat].push(c);
            });

            for (const [catName, items] of Object.entries(groups)) {
                // Slim specialty subheader
                const headerLi = document.createElement("li");
                headerLi.className = "diag-group-header";
                headerLi.innerHTML = `<i class="bi bi-tag-fill"></i> ${escapeHtml(catName)}`;
                chronicList.appendChild(headerLi);

                items.forEach(c => {
                    const li = document.createElement("li");
                    li.className = "diag-row diag-chronic-row";
                    const icd = formatIcd(c.code);
                    const latestDate = formatStandardDate(c.latest_date) || '-';
                    const inst = c.hospital || c.institute || (c.hospitals && c.hospitals.length > 0 ? c.hospitals[0] : "");
                    const otherInsts = (c.hospitals && c.hospitals.length > 1) ? ` (曾開立院所: ${c.hospitals.join('、')})` : '';

                    const tooltipLines = [
                        `【慢性問題】${c.name}`,
                        `診斷/開立院所 (Institute): ${inst || '本院門診'}${otherInsts}`,
                        `專科分類 (Category): ${catName}`,
                        `最近記錄 (Date): ${latestDate}`,
                        `ICD-10 診斷碼: ${icd || '-'}`
                    ];
                    li.title = tooltipLines.join('\n');
                    if (inst) li.dataset.institute = inst;

                    li.innerHTML = `
                        <span class="diag-bullet">•</span>
                        <span class="diag-desc-text">${escapeHtml(c.name)}</span>
                        ${icd ? `<span class="diag-icd-badge">${escapeHtml(icd)}</span>` : ''}
                    `;
                    chronicList.appendChild(li);
                });
            }
        }
    }

    // 3. Render Surgical & Interventional Procedures Timeline (with execution dates)
    if (surgList) {
        if (surgeries.length === 0) {
            surgList.innerHTML = '<li class="empty-state">尚無處置手術紀錄</li>';
        } else {
            surgeries.forEach(s => {
                const li = document.createElement("li");
                li.className = "surg-row";

                const rawDate = (typeof s === "object") ? (s.date || "歷史") : "歷史";
                const date = formatStandardDate(rawDate);
                const name = (typeof s === "object") ? s.name : s;
                const detail = (typeof s === "object") ? s.detail : "";
                const cat = (typeof s === "object") ? s.category : "手術處置";
                const inst = (typeof s === "object") ? (s.hospital || s.institute || "") : "";

                const tooltipLines = [
                    `【處置手術】${name}`,
                    inst ? `執行/記錄院所 (Institute): ${inst}` : '',
                    `執行/記錄日期 (Date): ${date}`,
                    `處置類別 (Category): ${cat}`,
                    detail ? `處置細節 (Detail): ${detail}` : ''
                ].filter(Boolean);
                li.title = tooltipLines.join('\n');
                if (inst) li.dataset.institute = inst;

                li.innerHTML = `
                    <span class="surg-date-badge">${escapeHtml(date)}</span>
                    <div class="surg-info">
                        <span class="surg-name">${escapeHtml(name)}</span>
                        ${detail ? `<span class="surg-detail">${escapeHtml(detail)}</span>` : ''}
                    </div>
                `;
                surgList.appendChild(li);
            });
        }
    }
}

function renderLabTable(labPanel, tab) {
    if (!labPanel) return;

    const flowsheetWrapper = document.getElementById("labFlowsheetWrapper");
    const listWrapper = document.getElementById("labListWrapper");
    const btnFlowsheet = document.getElementById("btnLabFlowsheet");
    const btnList = document.getElementById("btnLabList");

    // Manage container view toggles
    if (currentLabView === "flowsheet") {
        if (flowsheetWrapper) flowsheetWrapper.classList.remove("d-none");
        if (listWrapper) listWrapper.classList.add("d-none");
        if (btnFlowsheet) btnFlowsheet.classList.add("active");
        if (btnList) btnList.classList.remove("active");
    } else {
        if (flowsheetWrapper) flowsheetWrapper.classList.add("d-none");
        if (listWrapper) listWrapper.classList.remove("d-none");
        if (btnList) btnList.classList.add("active");
        if (btnFlowsheet) btnFlowsheet.classList.remove("active");
    }

    const grouped = labPanel.grouped || {};

    // Update dynamic count badges across the 6 physiological systems
    const allCount = (grouped.all || []).length || (labPanel.total_labs || 0);
    const liverCount = (grouped.liver || []).length;
    const hematologicalCount = (grouped.hematological || grouped.cbc || []).length;
    const renalCount = (grouped.renal || []).length;
    const metabolicCount = (grouped.metabolic || grouped.biochem || []).length;
    const immunologicalCount = (grouped.immunological || []).length;
    const othersCount = (grouped.others || []).length;

    const labAllCountElem = document.getElementById("labAllCount");
    const labLiverCountElem = document.getElementById("labLiverCount");
    const labHematologicalCountElem = document.getElementById("labHematologicalCount") || document.getElementById("labCbcCount");
    const labRenalCountElem = document.getElementById("labRenalCount");
    const labMetabolicCountElem = document.getElementById("labMetabolicCount") || document.getElementById("labBiochemCount");
    const labImmunologicalCountElem = document.getElementById("labImmunologicalCount");
    const labOthersCountElem = document.getElementById("labOthersCount");

    if (labAllCountElem) labAllCountElem.textContent = allCount;
    if (labLiverCountElem) labLiverCountElem.textContent = liverCount;
    if (labHematologicalCountElem) labHematologicalCountElem.textContent = hematologicalCount;
    if (labRenalCountElem) labRenalCountElem.textContent = renalCount;
    if (labMetabolicCountElem) labMetabolicCountElem.textContent = metabolicCount;
    if (labImmunologicalCountElem) labImmunologicalCountElem.textContent = immunologicalCount;
    if (labOthersCountElem) labOthersCountElem.textContent = othersCount;

    // Render Dedicated Liver Assessment Box (FIB-4, APRI, AST/ALT Ratio)
    const liverCard = document.getElementById("liverAssessmentCard");
    const liverAss = labPanel.liver_assessment;
    if (liverCard && liverAss && liverAss.has_scores) {
        if (tab === "liver" || tab === "all") {
            liverCard.classList.remove("d-none");
        } else {
            liverCard.classList.add("d-none");
        }

        // FIB-4
        const fib4 = liverAss.fib4;
        const fib4ValElem = document.getElementById("fib4Value");
        const fib4BadgeElem = document.getElementById("fib4Badge");
        const fib4DescElem = document.getElementById("fib4Desc");
        if (fib4 && fib4ValElem) {
            fib4ValElem.textContent = fib4.value.toFixed(2);
            fib4BadgeElem.className = `badge badge-${fib4.badge_color || 'primary'}`;
            fib4BadgeElem.textContent = fib4.status_label || '';
            fib4DescElem.textContent = fib4.interpretation || '';
        }

        // APRI
        const apri = liverAss.apri;
        const apriValElem = document.getElementById("apriValue");
        const apriBadgeElem = document.getElementById("apriBadge");
        const apriDescElem = document.getElementById("apriDesc");
        if (apri && apriValElem) {
            apriValElem.textContent = apri.value.toFixed(2);
            apriBadgeElem.className = `badge badge-${apri.badge_color || 'primary'}`;
            apriBadgeElem.textContent = apri.status_label || '';
            apriDescElem.textContent = apri.interpretation || '';
        }

        // AST/ALT Ratio
        const ratio = liverAss.ast_alt_ratio;
        const ratioValElem = document.getElementById("astAltRatioValue");
        const ratioBadgeElem = document.getElementById("astAltRatioBadge");
        const ratioDescElem = document.getElementById("astAltRatioDesc");
        if (ratio && ratioValElem) {
            ratioValElem.textContent = ratio.value.toFixed(2);
            ratioBadgeElem.className = `badge badge-${ratio.badge_color || 'primary'}`;
            ratioBadgeElem.textContent = ratio.value > 2.0 ? '偏高 (>2.0)' : (ratio.value > 1.0 ? '進行性纖維化警訊' : '正常 (<1.0)');
            ratioDescElem.textContent = ratio.interpretation || '';
        }

        // Age Adjusted Note
        const seniorElem = document.getElementById("liverSeniorNote");
        if (seniorElem) {
            if (liverAss.fib4 && liverAss.fib4.is_age_adjusted) {
                seniorElem.textContent = `年齡 ${liverAss.age_used || '--'} 歲校正切點 (< 2.0)`;
                seniorElem.className = "badge badge-warning";
            } else {
                seniorElem.textContent = "標準門檻 (< 1.30)";
                seniorElem.className = "badge badge-meta";
            }
        }

        // Biomarkers Strip
        const strip = document.getElementById("liverBiomarkersStrip");
        if (strip) {
            strip.innerHTML = "";
            const pills = [];
            if (liverAss.ast) pills.push(`AST: <strong>${liverAss.ast.val}</strong> ${liverAss.ast.unit}`);
            if (liverAss.alt) pills.push(`ALT: <strong>${liverAss.alt.val}</strong> ${liverAss.alt.unit}`);
            if (liverAss.platelet) pills.push(`PLT: <strong>${liverAss.platelet.val}</strong> ${liverAss.platelet.unit}`);
            if (liverAss.albumin) pills.push(`Albumin: <strong>${liverAss.albumin.val}</strong> ${liverAss.albumin.unit}`);
            if (liverAss.total_bilirubin) pills.push(`T-Bil: <strong>${liverAss.total_bilirubin.val}</strong> ${liverAss.total_bilirubin.unit}`);
            if (liverAss.alk_p) pills.push(`Alk-P: <strong>${liverAss.alk_p.val}</strong> ${liverAss.alk_p.unit}`);
            if (liverAss.r_gt) pills.push(`r-GT: <strong>${liverAss.r_gt.val}</strong> ${liverAss.r_gt.unit}`);
            if (liverAss.afp) pills.push(`AFP: <strong>${liverAss.afp.val}</strong> ${liverAss.afp.unit}`);

            pills.forEach(p => {
                const s = document.createElement("span");
                s.className = "liver-pill";
                s.innerHTML = p;
                strip.appendChild(s);
            });
        }
    } else if (liverCard) {
        liverCard.classList.add("d-none");
    }

    // 1. Render Flowsheet Matrix View
    if (labPanel.flowsheet) {
        renderLabFlowsheet(labPanel.flowsheet, tab, flowsheetFilterText);
    }

    // 2. Render List View (Traditional table)
    const tbody = document.getElementById("labTableBody");
    if (tbody) {
        tbody.innerHTML = "";
        const items = grouped[tab] || [];

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">此分類近期無檢驗紀錄</td></tr>';
        } else {
            items.forEach(item => {
                const tr = document.createElement("tr");

                let valClass = "";
                let arrow = "";
                const tag = item.status_tag || "";
                if (tag === "critical_high" || tag === "high" || tag === "severe_high") {
                    valClass = "val-text-high";
                    arrow = " ▲";
                } else if (tag === "critical_low" || tag === "low" || tag === "severe_low") {
                    valClass = "val-text-low";
                    arrow = " ▼";
                } else if (item.abnormal) {
                    valClass = "val-text-high";
                    arrow = " ▲";
                }

                tr.innerHTML = `
                    <td><strong>${escapeHtml(item.item)}</strong></td>
                    <td class="${valClass}"><strong>${escapeHtml(item.value_str || '-')}${arrow}</strong> ${item.comment ? `(${escapeHtml(item.comment)})` : ''}</td>
                    <td>${escapeHtml(item.unit || '-')}</td>
                    <td>${escapeHtml(item.ref || '-')}</td>
                    <td>${formatShortDate(item.date) || '-'}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    }
}

/**
 * Render Laboratory Longitudinal Flowsheet Matrix Table
 * X-axis: Time / Dates (Scrollable horizontally with sticky date header)
 * Y-axis: Analytes grouped by 6 Physiological Systems (Scrollable vertically with sticky item column)
 */
function renderLabFlowsheet(flowsheet, activeTab, filterText) {
    const container = document.getElementById("labFlowsheetContainer");
    if (!container) return;

    if (!flowsheet || !flowsheet.dates || flowsheet.dates.length === 0 || !flowsheet.categories || flowsheet.categories.length === 0) {
        container.innerHTML = '<div class="empty-state p-4 text-center">尚無檢驗時序資料</div>';
        const stats = document.getElementById("flowsheetStatsBadge");
        if (stats) stats.textContent = "0 項 • 0 日期";
        return;
    }

    const dates = flowsheet.dates || [];
    const filter = (filterText || "").toLowerCase().trim();

    // Filter categories by activeTab
    let categoriesToShow = flowsheet.categories;
    if (activeTab && activeTab !== "all") {
        categoriesToShow = flowsheet.categories.filter(c => c.id === activeTab);
    }

    // Filter items within categories by filter text
    let totalItemsCount = 0;
    const filteredCategories = [];

    categoriesToShow.forEach(cat => {
        let items = cat.items || [];
        if (filter) {
            items = items.filter(it => {
                const name = (it.item || "").toLowerCase();
                const unit = (it.unit || "").toLowerCase();
                return name.includes(filter) || unit.includes(filter);
            });
        }
        if (items.length > 0) {
            totalItemsCount += items.length;
            filteredCategories.push({
                ...cat,
                items: items
            });
        }
    });

    // Update stats badge & date span
    const statsBadge = document.getElementById("flowsheetStatsBadge");
    if (statsBadge) {
        statsBadge.textContent = `${totalItemsCount} 項檢驗 • ${dates.length} 個就診日期`;
    }
    const dateSpan = document.getElementById("flowsheetDateSpan");
    if (dateSpan && dates.length > 0) {
        dateSpan.textContent = `範圍: ${formatShortDate(dates[0])} ~ ${formatShortDate(dates[dates.length - 1])}`;
    }

    if (filteredCategories.length === 0) {
        container.innerHTML = '<div class="empty-state p-4 text-center">查無符合搜尋條件之檢驗項目</div>';
        return;
    }

    // Build Table
    const table = document.createElement("table");
    table.className = "table-flowsheet";

    // 1. Table Header (Corner cell + Date headers)
    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");

    const thCorner = document.createElement("th");
    thCorner.className = "flowsheet-corner-cell";
    thCorner.innerHTML = `
        <div class="corner-header-box">
            <div class="corner-title"><i class="bi bi-card-checklist text-primary"></i> 檢驗項目 (Analyte)</div>
            <div class="corner-sub">單位與參考區間 (Unit / Ref)</div>
        </div>
    `;
    trHead.appendChild(thCorner);

    dates.forEach(d => {
        const th = document.createElement("th");
        const shortDate = formatShortDate(d);
        const fullDate = formatStandardDate(d);
        th.textContent = shortDate;
        th.title = `檢驗就診日: ${fullDate} (${shortDate})`;
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    table.appendChild(thead);

    // 2. Table Body (Category subheaders + Item rows)
    const tbody = document.createElement("tbody");

    filteredCategories.forEach(cat => {
        // Group Header Row
        const trGroup = document.createElement("tr");
        trGroup.className = "flowsheet-group-row";
        const tdGroup = document.createElement("td");
        tdGroup.colSpan = dates.length + 1;
        tdGroup.innerHTML = `
            <i class="bi bi-diagram-3-fill text-primary"></i>
            <strong>${escapeHtml(cat.name)}</strong>
            <span class="flowsheet-group-badge">${cat.items.length} 項</span>
        `;
        trGroup.appendChild(tdGroup);
        tbody.appendChild(trGroup);

        // Item Rows
        cat.items.forEach(it => {
            const trItem = document.createElement("tr");
            if (it.is_calculated) {
                trItem.className = "row-calculated";
            }

            // Sticky Left Item Cell
            const tdItem = document.createElement("td");
            tdItem.className = "flowsheet-item-cell";
            const unitRefText = [it.unit, it.ref ? `Ref: ${it.ref}` : ''].filter(Boolean).join(" • ");
            trItem.title = `${it.item} ${unitRefText ? `(${unitRefText})` : ''}`;
            tdItem.innerHTML = `
                <div class="flowsheet-item-name">${escapeHtml(it.item)}</div>
                ${unitRefText ? `<div class="flowsheet-item-meta">${escapeHtml(unitRefText)}</div>` : ''}
            `;
            trItem.appendChild(tdItem);

            // Date value cells
            dates.forEach(d => {
                const tdVal = document.createElement("td");
                tdVal.className = "flowsheet-val-cell";
                const valObj = it.values ? it.values[d] : null;

                if (!valObj || valObj.val === undefined || valObj.val === null || valObj.val === "") {
                    tdVal.classList.add("val-empty");
                    tdVal.textContent = "-";
                } else {
                    const valStr = String(valObj.val).trim();

                    const tooltip = [
                        `${it.item}`,
                        `就診日: ${formatShortDate(d)}`,
                        `數值: ${valStr} ${it.unit || ''}`,
                        it.ref ? `參考區間: ${it.ref}` : '',
                        valObj.comment ? `臨床備註: ${valObj.comment}` : ''
                    ].filter(Boolean).join(" | ");

                    let statusClass = "val-normal";
                    let arrowIcon = "";
                    const tag = valObj.status_tag || "";

                    if (tag === "critical_high") {
                        statusClass = "val-critical-high";
                        arrowIcon = '<span class="val-arrow val-arrow-up">▲</span>';
                    } else if (tag === "high" || tag === "severe_high") {
                        statusClass = "val-high";
                        arrowIcon = '<span class="val-arrow val-arrow-up">▲</span>';
                    } else if (tag === "critical_low") {
                        statusClass = "val-critical-low";
                        arrowIcon = '<span class="val-arrow val-arrow-down">▼</span>';
                    } else if (tag === "low" || tag === "severe_low") {
                        statusClass = "val-low";
                        arrowIcon = '<span class="val-arrow val-arrow-down">▼</span>';
                    } else if (valObj.abnormal) {
                        statusClass = "val-high";
                        arrowIcon = '<span class="val-arrow val-arrow-up">▲</span>';
                    }

                    tdVal.innerHTML = `
                        <span class="val-badge ${statusClass}" title="${escapeHtml(tooltip)}">
                            ${arrowIcon}<strong>${escapeHtml(valStr)}</strong>
                        </span>
                    `;
                }

                trItem.appendChild(tdVal);
            });

            tbody.appendChild(trItem);
        });
    });

    table.appendChild(tbody);
    container.innerHTML = "";
    container.appendChild(table);

    // Synchronize Extra Top Horizontal Scrollbar width
    const topScrollBox = document.getElementById("flowsheetTopScrollContainer");
    const topTrack = document.getElementById("flowsheetTopScrollTrack");
    const topDummy = document.getElementById("flowsheetTopScrollDummy");

    if (topDummy && topTrack) {
        const totalW = table.scrollWidth || table.offsetWidth;
        topDummy.style.width = totalW + "px";
        if (topScrollBox) {
            topScrollBox.style.display = totalW > container.clientWidth ? "flex" : "none";
        }
    }

    // Automatically scroll container horizontally to the far right edge so newest report is visible at the right edge
    setTimeout(() => {
        container.scrollLeft = container.scrollWidth;
        if (topTrack) {
            topTrack.scrollLeft = topTrack.scrollWidth;
        }
    }, 0);
}

function renderRadiologyReports(reports) {
    const container = document.getElementById("reportsContainer");
    if (!container) return;
    container.innerHTML = "";

    const allReports = reports || [];

    // Calculate category counts
    const totalCount = allReports.length;
    let ctMriCount = 0;
    let pathologyCount = 0;
    let endoCount = 0;
    let xrayCount = 0;

    allReports.forEach(r => {
        const cat = r.modality_category || "";
        if (r.is_ct || r.is_mri || cat === "ct_mri") {
            ctMriCount++;
        } else if (r.is_pathology || cat === "pathology") {
            pathologyCount++;
        } else if (cat === "endoscopy_pta") {
            endoCount++;
        } else if (cat === "xray_sono") {
            xrayCount++;
        }
    });

    const reportCountElem = document.getElementById("reportCount");
    const ctMriCountElem = document.getElementById("ctMriCount");
    const pathologyCountElem = document.getElementById("pathologyCount");
    const endoCountElem = document.getElementById("endoCount");
    const xrayCountElem = document.getElementById("xrayCount");

    if (reportCountElem) reportCountElem.textContent = totalCount;
    if (ctMriCountElem) ctMriCountElem.textContent = ctMriCount;
    if (pathologyCountElem) pathologyCountElem.textContent = pathologyCount;
    if (endoCountElem) endoCountElem.textContent = endoCount;
    if (xrayCountElem) xrayCountElem.textContent = xrayCount;

    if (totalCount === 0) {
        container.innerHTML = '<div class="empty-state">無影像或病理報告紀錄</div>';
        return;
    }

    // Filter reports based on active tab
    const filteredReports = allReports.filter(r => {
        if (currentImagingTab === "all") return true;
        const cat = r.modality_category || "";
        if (currentImagingTab === "ct_mri") {
            return r.is_ct || r.is_mri || cat === "ct_mri";
        }
        if (currentImagingTab === "pathology") {
            return r.is_pathology || cat === "pathology";
        }
        if (currentImagingTab === "endoscopy_pta") {
            return cat === "endoscopy_pta";
        }
        if (currentImagingTab === "xray_sono") {
            return cat === "xray_sono";
        }
        return true;
    });

    if (filteredReports.length === 0) {
        container.innerHTML = '<div class="empty-state">此篩選類別無相關報告紀錄</div>';
        return;
    }

    filteredReports.forEach((rep) => {
        const origIdx = allReports.indexOf(rep);
        const card = document.createElement("div");
        const isCtMri = rep.is_ct || rep.is_mri || rep.modality_category === "ct_mri";
        const isPath = rep.is_pathology || rep.modality_category === "pathology";
        card.className = `report-card ${isCtMri ? 'card-ct-mri' : ''} ${isPath ? 'card-pathology' : ''}`;

        // Choose appropriate icon
        let modalityIcon = "bi-file-earmark-medical";
        if (rep.is_ct) modalityIcon = "bi-disc";
        else if (rep.is_mri) modalityIcon = "bi-magnet";
        else if (isPath) modalityIcon = "bi-journal-medical";
        else if (rep.modality_category === "endoscopy_pta") modalityIcon = "bi-bezier2";
        else if (rep.modality_category === "xray_sono") modalityIcon = "bi-aspect-ratio";

        // Badges strip
        let badgesHtml = `
            <span class="badge-study-modality ${isPath ? 'badge-pathology' : ''}">
                <i class="bi ${modalityIcon}"></i> ${escapeHtml(rep.modality || (isPath ? '外科病理' : '檢查'))}
            </span>
        `;

        if (isPath && rep.malignancy_status) {
            badgesHtml += `
                <span class="badge badge-${rep.malignancy_badge || 'info'}">
                    ${escapeHtml(rep.malignancy_status)}
                </span>
            `;
        }

        if (rep.contrast_status) {
            const hasContrast = rep.contrast_status.includes("有") || rep.contrast_status.toLowerCase().includes("with");
            badgesHtml += `
                <span class="badge-study-contrast ${hasContrast ? 'with-contrast' : 'no-contrast'}">
                    <i class="bi ${hasContrast ? 'bi-droplet-fill' : 'bi-droplet'}"></i> ${escapeHtml(rep.contrast_status)}
                </span>
            `;
        }

        if (rep.body_site) {
            badgesHtml += `
                <span class="badge-study-site">
                    <i class="bi bi-geo-alt"></i> ${escapeHtml(rep.body_site)}
                </span>
            `;
        }

        if (rep.nhi_code) {
            badgesHtml += `<span class="badge-study-code">${escapeHtml(rep.nhi_code)}</span>`;
        }

        // Alerts badges
        let alertHtml = "";
        (rep.alerts || []).forEach(a => {
            alertHtml += `<span class="badge badge-danger" style="margin-right:4px;">${escapeHtml(a)}</span>`;
        });

        // Procedure Name (for pathology / biopsy / intervention)
        let procedureHtml = "";
        if (rep.procedure_name) {
            procedureHtml = `
                <div class="report-indication-row">
                    <i class="bi bi-scissors text-purple"></i> <strong>切片/處置 (Procedure):</strong> ${escapeHtml(rep.procedure_name)}
                </div>
            `;
        }

        // Indication (適應症)
        let indicationHtml = "";
        if (isPath && rep.clinical_diagnosis) {
            indicationHtml = `
                <div class="report-indication-row">
                    <i class="bi bi-info-circle text-muted"></i> <strong>送檢臨床診斷 (Clinical Diagnosis):</strong> ${escapeHtml(rep.clinical_diagnosis)}
                </div>
            `;
        } else if (rep.sections && rep.sections.indication) {
            indicationHtml = `
                <div class="report-indication-row">
                    <i class="bi bi-info-circle text-muted"></i> <strong>適應症 (Indication):</strong> ${escapeHtml(rep.sections.indication)}
                </div>
            `;
        }

        // Pathological Diagnosis Box (for pathology)
        let pathDiagHtml = "";
        if (isPath && rep.pathological_diagnosis) {
            pathDiagHtml = `
                <div class="pathology-diag-box">
                    <div class="pathology-diag-title">
                        <span><i class="bi bi-clipboard2-pulse"></i> 病理組織診斷 (Pathological Diagnosis)</span>
                    </div>
                    <div class="pathology-diag-content">${escapeHtml(rep.pathological_diagnosis)}</div>
                </div>
            `;
        }

        // Findings bullets (non-pathology)
        let findingsHtml = "";
        if (!isPath) {
            for (const [cat, fList] of Object.entries(rep.findings_by_category || {})) {
                (fList || []).forEach(f => {
                    findingsHtml += `<div class="finding-bullet"><i class="bi bi-chevron-right text-primary"></i> ${escapeHtml(f)}</div>`;
                });
            }
            if (!findingsHtml && rep.sections && rep.sections.findings) {
                findingsHtml = `<div class="finding-bullet"><i class="bi bi-chevron-right text-primary"></i> ${escapeHtml(rep.sections.findings)}</div>`;
            }
        }

        // Impression / Conclusion Box (for non-pathology)
        let impressionHtml = "";
        if (!isPath && rep.sections && rep.sections.impression) {
            impressionHtml = `
                <div class="report-impression-box">
                    <div class="report-impression-title"><i class="bi bi-card-checklist"></i> 診斷/印象 (Impression & Conclusion)</div>
                    <div>${escapeHtml(rep.sections.impression)}</div>
                </div>
            `;
        }

        // Specific Lesion Findings and Measurements Pills
        let measHtml = "";
        (rep.measurements || []).forEach(m => {
            const lesionName = m.lesion_name || m.type || "Lesion Finding";
            let site = m.site || "";
            if (site) {
                site = site.replace(/\s*\([^)]*\)/, '').trim();
            }
            const dim = m.dimension || "";
            // Only show site pill if site is not empty and not redundant with lesionName
            const showSite = site && !lesionName.toLowerCase().includes(site.toLowerCase()) && !site.toLowerCase().includes(lesionName.toLowerCase());
            measHtml += `
                <div class="lesion-finding-pill" title="${escapeHtml(m.context || '')}">
                    <span class="pill-lesion-name"><i class="bi bi-bullseye"></i> ${escapeHtml(lesionName)}</span>
                    ${showSite ? `<span class="pill-lesion-site"><i class="bi bi-geo-alt"></i> ${escapeHtml(site)}</span>` : ''}
                    <span class="pill-lesion-size"><strong>${escapeHtml(dim)}</strong></span>
                </div>
            `;
        });
        if (rep.lesion_findings && rep.lesion_findings.length > 0 && (!rep.measurements || rep.measurements.length === 0)) {
            rep.lesion_findings.forEach(lf => {
                measHtml += `
                    <div class="lesion-finding-pill">
                        <span class="pill-lesion-name"><i class="bi bi-bullseye"></i> ${escapeHtml(lf)}</span>
                    </div>
                `;
            });
        }

        const reportRawId = `raw-rep-${origIdx}-${Math.random().toString(36).substring(2, 7)}`;
        const studyTitle = rep.study_name || rep.modality || "影像檢查報告";

        card.innerHTML = `
            <div class="report-card-header">
                <div class="report-title-group">
                    <div class="report-study-title">${escapeHtml(studyTitle)}</div>
                    <div class="report-badges-strip">${badgesHtml}</div>
                </div>
                <div class="report-meta">
                    <div><strong>${formatStandardDate(rep.date)}</strong></div>
                    <div class="text-muted">${escapeHtml((rep.hospital || '').split('|')[0])}</div>
                    <button class="btn-ai-extract" onclick="triggerAiExtract(${origIdx})" style="margin-top:4px;">
                        <i class="bi bi-stars"></i> AI 萃取
                    </button>
                </div>
            </div>
            ${alertHtml ? `<div style="margin-bottom:6px;">${alertHtml}</div>` : ''}
            ${procedureHtml}
            ${indicationHtml}
            ${pathDiagHtml}
            ${findingsHtml ? `<div class="report-findings-box">${findingsHtml}</div>` : ''}
            ${impressionHtml}
            ${measHtml ? `<div class="measurements-container">${measHtml}</div>` : ''}
            <div>
                <button class="raw-toggle-btn" onclick="toggleRawReport('${reportRawId}')">
                    <i class="bi bi-file-earmark-text"></i> 查看原始報告內容 (Raw Report)
                </button>
                <pre id="${reportRawId}" class="raw-report-view">${escapeHtml(rep.raw_summary || '')}</pre>
            </div>
        `;
        container.appendChild(card);
    });
}

window.toggleRawReport = function(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.toggle("show");
    }
};

function renderMedications(meds) {
    if (!meds) return;

    const activeList = meds.active_medications || [];
    const completedList = meds.completed_medications || [];
    const totalCount = activeList.length + completedList.length;

    // Update count badges
    const activeCountEl = document.getElementById("activeMedCount");
    if (activeCountEl) activeCountEl.textContent = activeList.length;
    const completedCountEl = document.getElementById("completedMedCount");
    if (completedCountEl) completedCountEl.textContent = completedList.length;
    const totalMedCountEl = document.getElementById("totalMedCount");
    if (totalMedCountEl) totalMedCountEl.textContent = totalCount;

    // Update 6-month count
    const clinicDt = parseStandardDate(meds.timeline?.clinic_date || "2026/09/01") || new Date();
    const sixMonthsAgo = clinicDt.getTime() - (180 * 86400000);
    const sixMCount = (meds.timeline?.drugs || []).filter(d => {
        if (d.is_active_now) return true;
        return (d.episodes || []).some(ep => {
            const epEnd = parseStandardDate(ep.end_date);
            return epEnd && epEnd.getTime() >= sixMonthsAgo;
        });
    }).length;
    const sixMBtn = document.getElementById("medFilter6M");
    if (sixMBtn) sixMBtn.innerHTML = `近 6 個月 (<span id="sixMonthsMedCount">${sixMCount}</span>)`;

    // Update topbar and workspace navigation badges
    const topbarMedBadge = document.getElementById("topbarMedBadge");
    if (topbarMedBadge) topbarMedBadge.textContent = activeList.length;
    const wsMedCount = document.getElementById("wsMedCount");
    if (wsMedCount) wsMedCount.textContent = activeList.length;

    // Safety alerts
    const alertsBox = document.getElementById("safetyAlertsBox");
    const alertsList = document.getElementById("safetyAlertsList");
    if (alertsBox && alertsList) {
        alertsList.innerHTML = "";
        if (meds.safety_alerts && meds.safety_alerts.length > 0) {
            alertsBox.classList.remove("d-none");
            meds.safety_alerts.forEach(a => {
                const li = document.createElement("li");
                li.textContent = a;
                alertsList.appendChild(li);
            });
        } else {
            alertsBox.classList.add("d-none");
        }
    }

    // Render Timeline View
    if (meds.timeline) {
        renderMedicationTimeline(meds.timeline, currentMedFilter, medSearchQuery);
    }

    // Render Traditional List View
    renderMedicationList(meds, currentMedFilter, medSearchQuery);
}

/**
 * Render Medication Timeline Matrix:
 * X-axis: Time / Dates (earliest on left, most current on right edge)
 * Red Dotted Line: Current Visit Date (Clinic Date)
 * Green Striped Portion: Drug Remains (殘藥量) past the dotted line
 * Y-axis: Sticky left column with Generic Name, Brand Name, Dose, and Frequency
 */
function renderMedicationTimeline(timeline, filterMode, searchQuery) {
    const container = document.getElementById("medTimelineContainer");
    if (!container) return;

    if (!timeline || !timeline.drugs || timeline.drugs.length === 0) {
        container.innerHTML = '<div class="empty-state p-4 text-center">尚無用藥時序資料</div>';
        return;
    }

    const clinicDateStr = timeline.clinic_date || "2026/09/01";
    const clinicDt = parseStandardDate(clinicDateStr) || new Date();
    const clinicTime = clinicDt.getTime();

    // 1. Filter drugs by scope (Active vs 6 Months vs All)
    let filteredDrugs = timeline.drugs.slice();

    if (filterMode === "active") {
        filteredDrugs = filteredDrugs.filter(d => d.is_active_now);
    } else if (filterMode === "6m") {
        const sixMonthsAgo = clinicTime - (180 * 86400000);
        filteredDrugs = filteredDrugs.filter(d => {
            if (d.is_active_now) return true;
            return (d.episodes || []).some(ep => {
                const epEnd = parseStandardDate(ep.end_date);
                return epEnd && epEnd.getTime() >= sixMonthsAgo;
            });
        });
    }

    // 2. Real-time Search Query Filter
    if (searchQuery) {
        const q = searchQuery.toLowerCase();
        filteredDrugs = filteredDrugs.filter(d => {
            const gen = (d.generic_name || "").toLowerCase();
            const brand = (d.brand_name || "").toLowerCase();
            const brandFull = (d.brand_full || "").toLowerCase();
            const dose = (d.dose || "").toLowerCase();
            const method = (d.method || "").toLowerCase();
            const cat = (d.category || "").toLowerCase();
            const nhicodes = (d.episodes || []).map(ep => (ep.nhicode || "").toLowerCase()).join(" ");
            return gen.includes(q) || brand.includes(q) || brandFull.includes(q) || dose.includes(q) || method.includes(q) || cat.includes(q) || nhicodes.includes(q);
        });
    }

    // Update stats badge
    const statsBadge = document.getElementById("medTimelineStatsBadge");
    const activeCount = filteredDrugs.filter(d => d.is_active_now).length;
    if (statsBadge) {
        statsBadge.textContent = `${filteredDrugs.length} 項藥品 / ${activeCount} 項進行中`;
    }

    if (filteredDrugs.length === 0) {
        container.innerHTML = `<div class="empty-state p-4 text-center">${searchQuery ? '未找到符合關鍵字的用藥紀錄' : '此篩選範圍內無處方紀錄'}</div>`;
        return;
    }

    // 3. Determine time boundaries (minDate & maxDate) for the visible episodes
    let minTime = clinicTime - (90 * 86400000); // at least 90 days before clinic date
    let maxTime = clinicTime + (30 * 86400000); // at least 30 days after clinic date

    filteredDrugs.forEach(d => {
        (d.episodes || []).forEach(ep => {
            const s = parseStandardDate(ep.start_date);
            const e = parseStandardDate(ep.end_date);
            if (s && s.getTime() < minTime) minTime = s.getTime();
            if (e && e.getTime() > maxTime) maxTime = e.getTime();
        });
    });

    // Add 7 days padding at the end so drug remains have right margin
    maxTime += (7 * 86400000);

    const minDt = new Date(minTime);
    const maxDt = new Date(maxTime);
    const totalDays = Math.max(Math.round((maxTime - minTime) / 86400000), 30);

    // Update Date Span Label
    const dateSpanLabel = document.getElementById("medTimelineDateSpan");
    if (dateSpanLabel) {
        const minStd = `${minDt.getFullYear()}/${String(minDt.getMonth() + 1).padStart(2, '0')}/${String(minDt.getDate()).padStart(2, '0')}`;
        const maxStd = `${maxDt.getFullYear()}/${String(maxDt.getMonth() + 1).padStart(2, '0')}/${String(maxDt.getDate()).padStart(2, '0')}`;
        dateSpanLabel.textContent = `範圍: ${formatShortDate(minStd)} ~ ${formatShortDate(maxStd)} (共 ${totalDays} 天)`;
    }

    // 4. Coordinate System (pixels per day and track width)
    const pxPerDay = Math.max(5.5, Math.min(9.0, 1600 / totalDays));
    const trackWidth = Math.round(totalDays * pxPerDay);

    function getX(dt) {
        if (!dt) return 0;
        const diff = dt.getTime() - minTime;
        return Math.round((diff / 86400000) * pxPerDay);
    }

    const currentDateX = getX(clinicDt);

    // 5. Generate Month Segments for sticky header and vertical grid lines
    const months = [];
    const gridLines = [];

    let curYear = minDt.getFullYear();
    let curMonth = minDt.getMonth();
    const endYear = maxDt.getFullYear();
    const endMonth = maxDt.getMonth();

    while (curYear < endYear || (curYear === endYear && curMonth <= endMonth)) {
        const mStart = new Date(curYear, curMonth, 1);
        const mEnd = new Date(curYear, curMonth + 1, 0, 23, 59, 59);

        const clampedStart = mStart.getTime() < minTime ? new Date(minTime) : mStart;
        const clampedEnd = mEnd.getTime() > maxTime ? new Date(maxTime) : mEnd;

        const leftPx = getX(clampedStart);
        const rightPx = getX(clampedEnd) + pxPerDay;
        const widthPx = Math.max(rightPx - leftPx, 24);

        const shortYear = String(curYear).slice(-2);
        const monthNum = String(curMonth + 1).padStart(2, "0");
        const monthLabel = `${shortYear}/${monthNum}`;
        const monthDays = Math.round((clampedEnd.getTime() - clampedStart.getTime()) / 86400000) + 1;

        months.push({
            label: monthLabel,
            days: monthDays,
            left: leftPx,
            width: widthPx
        });

        if (leftPx > 0) {
            gridLines.push(leftPx);
        }

        curMonth++;
        if (curMonth > 11) {
            curMonth = 0;
            curYear++;
        }
    }

    const gridLinesHtml = gridLines.map(x => `<div class="med-grid-line" style="left: ${x}px;"></div>`).join("");

    // 6. Build Month Headers in the Top Sticky Row
    const monthHeadersHtml = months.map(m => `
        <div style="position: absolute; left: ${m.left}px; width: ${m.width}px; height: 100%; border-right: 1px solid var(--border-color); display: flex; flex-direction: column; justify-content: center; align-items: center; user-select: none;">
            <span style="font-weight: 700; font-size: 11.5px; color: var(--text-primary); font-family: var(--font-mono);">${m.label}</span>
            <span style="font-size: 9px; color: var(--text-muted);">${m.days}天</span>
        </div>
    `).join("");

    // 7. Group visible drugs by therapeutic category and sort
    const byCategory = {};
    filteredDrugs.forEach(d => {
        const cat = d.category || "其他藥物";
        if (!byCategory[cat]) byCategory[cat] = [];
        byCategory[cat].push(d);
    });

    // Sort categories: categories with active drugs first, descending by active count
    const sortedCategories = Object.keys(byCategory).sort((a, b) => {
        const aActive = byCategory[a].filter(d => d.is_active_now).length;
        const bActive = byCategory[b].filter(d => d.is_active_now).length;
        if (aActive !== bActive) return bActive - aActive;
        return a.localeCompare(b);
    });

    // 8. Build Table Body Rows
    let tbodyHtml = "";

    for (const catName of sortedCategories) {
        const catDrugs = byCategory[catName] || [];

        // Sort drugs inside category: active drugs first, then by latest episode date
        catDrugs.sort((a, b) => {
            if (a.is_active_now !== b.is_active_now) {
                return a.is_active_now ? -1 : 1;
            }
            const aLatest = Math.max(...(a.episodes || []).map(e => parseStandardDate(e.end_date)?.getTime() || 0));
            const bLatest = Math.max(...(b.episodes || []).map(e => parseStandardDate(e.end_date)?.getTime() || 0));
            return bLatest - aLatest;
        });

        // Category Separator Row
        tbodyHtml += `
            <tr class="med-timeline-group-row">
                <td colspan="2">
                    <i class="bi bi-tag-fill"></i> ${escapeHtml(catName)} (${catDrugs.length})
                </td>
            </tr>
        `;

        catDrugs.forEach(d => {
            const episodes = d.episodes || [];

            // Multi-lane allocation to prevent bar collisions if same drug has overlapping episodes
            const lanes = [];
            const epLanes = [];

            episodes.forEach(ep => {
                const sDt = parseStandardDate(ep.start_date);
                const eDt = parseStandardDate(ep.end_date);
                const sTime = sDt ? sDt.getTime() : 0;
                const eTime = eDt ? eDt.getTime() : 0;

                let placedLane = -1;
                for (let i = 0; i < lanes.length; i++) {
                    if (sTime >= lanes[i]) {
                        placedLane = i;
                        lanes[i] = eTime;
                        break;
                    }
                }
                if (placedLane === -1) {
                    placedLane = lanes.length;
                    lanes.push(eTime);
                }
                epLanes.push(placedLane);
            });

            const numLanes = Math.max(lanes.length, 1);
            const rowHeight = numLanes === 1 ? 42 : (numLanes * 32 + 10);

            // Build Prescription Bars HTML
            let barsHtml = "";
            episodes.forEach((ep, epIdx) => {
                const sDt = parseStandardDate(ep.start_date);
                const eDt = parseStandardDate(ep.end_date);
                if (!sDt || !eDt) return;

                const barLeft = getX(sDt);
                const barRight = getX(eDt) + pxPerDay;
                const barWidth = Math.max(barRight - barLeft, 22);
                const lane = epLanes[epIdx] || 0;
                const topOffset = numLanes === 1 ? 7 : (lane * 32 + 6);
                const barHeight = numLanes === 1 ? 28 : 26;

                // Tooltip Details
                const tooltipText = [
                    `【${d.brand_name}】(${d.generic_name})`,
                    `劑量頻率: ${ep.dose || d.dose || '--'} | ${ep.method || d.method || '--'}`,
                    `處方區間: ${formatShortDate(ep.start_date)} ~ ${formatShortDate(ep.end_date)} (共 ${ep.total_days} 日份)`,
                    ep.is_chronic_refill ? '★ 慢性病連續處方箋 (慢箋)' : '一般門診處方',
                    ep.is_active ? `★ 進行中處方：至門診日已服 ${ep.consumed} 天，尚餘藥量 ${ep.remains} 天份` : (ep.remains > 0 ? `預約處方 (剩餘 ${ep.remains} 天)` : `已於 ${formatShortDate(ep.end_date)} 服畢`),
                    ep.diagnosis ? `診斷適應症: ${ep.diagnosis}` : '',
                    ep.nhicode ? `健保代碼: ${ep.nhicode}` : '',
                    ep.contraindicated ? `⚠️ 安全警示: ${ep.contra_reason}` : ''
                ].filter(Boolean).join('\n');

                if (ep.is_active || (barLeft <= currentDateX && currentDateX <= barRight)) {
                    // Active Prescription: Split cleanly at Current Date Line
                    const consumedW = Math.max(currentDateX - barLeft, 0);
                    const remainsW = Math.max(barWidth - consumedW, 0);

                    barsHtml += `
                        <div class="med-bar active" style="left: ${barLeft}px; width: ${barWidth}px; top: ${topOffset}px; height: ${barHeight}px;" title="${escapeHtml(tooltipText)}">
                            ${consumedW > 0 ? `
                                <div class="med-bar-consumed" style="width: ${consumedW}px;">
                                    ${ep.total_days}d ${escapeHtml(ep.method || '')}
                                </div>
                            ` : ''}
                            ${remainsW > 0 ? `
                                <div class="med-bar-remains" style="width: ${remainsW}px;">
                                    <span class="med-remains-pill-text">
                                        <i class="bi bi-hourglass-split"></i> 餘 ${ep.remains}天
                                    </span>
                                </div>
                            ` : ''}
                        </div>
                    `;
                } else if (barRight < currentDateX) {
                    // Past Completed Prescription
                    barsHtml += `
                        <div class="med-bar completed" style="left: ${barLeft}px; width: ${barWidth}px; top: ${topOffset}px; height: ${barHeight}px;" title="${escapeHtml(tooltipText)}">
                            <div class="med-bar-consumed" style="width: 100%;">
                                ${ep.total_days}d ${escapeHtml(ep.method || '')} (服畢)
                            </div>
                        </div>
                    `;
                } else {
                    // Future / Scheduled Prescription
                    barsHtml += `
                        <div class="med-bar future" style="left: ${barLeft}px; width: ${barWidth}px; top: ${topOffset}px; height: ${barHeight}px;" title="${escapeHtml(tooltipText)}">
                            <div class="med-bar-remains" style="width: 100%;">
                                <span class="med-remains-pill-text">預約 ${ep.total_days}日份</span>
                            </div>
                        </div>
                    `;
                }
            });

            // Sticky Y-Axis Cell (Generic name, brand name, dose, frequency, remains badge)
            const brandDisplay = d.brand_name || d.medication || "";
            const genericDisplay = d.generic_name || "Unknown Generic";
            const doseBadge = d.dose ? `<span class="med-dose-badge" title="單次劑量">${escapeHtml(d.dose)}</span>` : '';
            const freqBadge = d.method ? `<span class="med-freq-badge" title="給藥頻率">${escapeHtml(d.method)}</span>` : '';
            const remainsPill = (d.is_active_now && d.current_remains > 0)
                ? `<span class="med-remains-summary-pill" title="本次門診日尚餘藥量"><i class="bi bi-hourglass-split"></i> 餘 ${d.current_remains}天</span>`
                : '';
            const contraBadge = d.contraindicated
                ? `<span class="badge badge-danger" style="font-size:10px;" title="${escapeHtml(d.contra_reason || '用藥安全警示')}"><i class="bi bi-exclamation-triangle-fill"></i> 禁忌</span>`
                : '';

            const epCodes = (d.episodes || []).map(ep => ep.nhicode).filter(Boolean);
            const primaryCode = epCodes[0] || '';
            const photoBtn = `<button type="button" class="med-photo-btn" data-brand="${escapeHtml(d.brand_name || brandDisplay)}" data-code="${escapeHtml(primaryCode)}" data-generic="${escapeHtml(genericDisplay)}" onclick="openDrugPhotoModalFromBtn(this, event)" title="查看藥品外觀照片"><i class="bi bi-card-image"></i></button>`;

            tbodyHtml += `
                <tr>
                    <td class="med-y-cell" style="height: ${rowHeight}px;">
                        <div class="med-generic-title" title="${escapeHtml(genericDisplay)}">
                            <span class="${d.is_active_now ? 'med-active-dot' : 'med-past-dot'}" title="${d.is_active_now ? '目前進行中' : '歷史處方'}"></span>
                            <span class="med-generic-text">${escapeHtml(genericDisplay)}</span>
                        </div>
                        <div class="med-meta-line">
                            <span class="med-brand-name" title="${escapeHtml(d.brand_full || brandDisplay)}">${escapeHtml(brandDisplay)}</span>${photoBtn}
                            ${doseBadge}
                            ${freqBadge}
                            ${remainsPill}
                            ${contraBadge}
                        </div>
                    </td>
                    <td class="med-timeline-track-cell" style="width: ${trackWidth}px; min-width: ${trackWidth}px; height: ${rowHeight}px;">
                        ${gridLinesHtml}
                        <div class="med-current-date-line" style="left: ${currentDateX}px;"></div>
                        ${barsHtml}
                    </td>
                </tr>
            `;
        });
    }

    // 9. Assemble Complete Table HTML
    const tableHtml = `
        <table class="med-timeline-table">
            <thead>
                <tr>
                    <th class="med-y-corner-cell">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span>藥品名稱 / 劑量 / 頻率</span>
                            <span style="font-size:10px; font-weight:normal; color:var(--text-muted);">Y-軸</span>
                        </div>
                    </th>
                    <th class="med-time-header-cell" style="width: ${trackWidth}px; min-width: ${trackWidth}px; height: 42px; position: relative; padding: 0;">
                        <div style="position: relative; width: 100%; height: 100%;">
                            ${monthHeadersHtml}
                            <div class="med-current-date-marker" style="left: ${currentDateX}px;" title="本次門診基準日: ${clinicDateStr}">
                                <i class="bi bi-geo-alt-fill"></i> 本次門診 ${formatShortDate(clinicDateStr)}
                            </div>
                        </div>
                    </th>
                </tr>
            </thead>
            <tbody>
                ${tbodyHtml}
            </tbody>
        </table>
    `;

    container.innerHTML = tableHtml;

    // 10. Synchronize Top Scrollbar and Auto-scroll to the Right Edge (Latest Medication)
    setTimeout(() => {
        const topDummy = document.getElementById("medTopScrollDummy");
        const topScrollBox = document.getElementById("medTopScrollContainer");
        const medTopTrack = document.getElementById("medTopScrollTrack");
        const table = container.querySelector(".med-timeline-table");

        if (table && topDummy) {
            const totalW = table.scrollWidth || table.offsetWidth;
            topDummy.style.width = totalW + "px";
            if (topScrollBox) {
                topScrollBox.style.display = totalW > container.clientWidth ? "flex" : "none";
            }
        }

        // Auto-scroll timeline to the right edge so current medication is immediately visible
        container.scrollLeft = container.scrollWidth;
        if (medTopTrack) {
            medTopTrack.scrollLeft = medTopTrack.scrollWidth;
        }
    }, 60);
}

/**
 * Render Traditional List View for Medications (Secondary / Card View)
 */
function renderMedicationList(meds, filterMode, searchQuery) {
    const container = document.getElementById("medicationsContainer");
    if (!container) return;
    container.innerHTML = "";

    const activeList = meds.active_medications || [];
    const completedList = meds.completed_medications || [];

    let targetList = [];
    if (filterMode === "active") {
        targetList = activeList.slice();
    } else if (filterMode === "6m") {
        targetList = activeList.concat(completedList.slice(0, 15));
    } else {
        targetList = activeList.concat(completedList);
    }

    if (searchQuery) {
        const q = searchQuery.toLowerCase();
        targetList = targetList.filter(m => {
            const brand = (m.brand_name || m.medication || "").toLowerCase();
            const generic = (m.generic_name || m.ingredient || "").toLowerCase();
            const dose = (m.dose || "").toLowerCase();
            const nhi = (m.nhicode || "").toLowerCase();
            const cat = (m.category || "").toLowerCase();
            return brand.includes(q) || generic.includes(q) || dose.includes(q) || nhi.includes(q) || cat.includes(q);
        });
    }

    if (targetList.length === 0) {
        container.innerHTML = `<div class="empty-state">${searchQuery ? '未找到符合關鍵字的藥物或成分' : (filterMode === 'active' ? '目前無進行中處方' : '無用藥處方紀錄')}</div>`;
        return;
    }

    // Group by category
    const byCat = {};
    targetList.forEach(m => {
        const cat = m.category || "其他藥物";
        if (!byCat[cat]) byCat[cat] = [];
        byCat[cat].push(m);
    });

    for (const [catName, medItems] of Object.entries(byCat)) {
        const catTitle = document.createElement("div");
        catTitle.className = "med-category-title";
        catTitle.innerHTML = `<i class="bi bi-tag-fill"></i> ${escapeHtml(catName)} (${medItems.length})`;
        container.appendChild(catTitle);

        medItems.forEach(m => {
            const item = document.createElement("div");
            item.className = `med-item-card ${m.contraindicated ? 'contraindicated' : ''}`;

            const brand = m.brand_name || m.medication || "";
            const generic = m.generic_name || m.ingredient || "";
            const hasGeneric = generic && generic.trim().length > 0;
            const doseText = m.dose ? `<span class="med-dose-badge" style="margin-left:6px;">${escapeHtml(m.dose)}</span>` : '';

            const photoBtn = `<button type="button" class="med-photo-btn" data-brand="${escapeHtml(brand)}" data-code="${escapeHtml(m.nhicode || '')}" data-generic="${escapeHtml(generic)}" onclick="openDrugPhotoModalFromBtn(this, event)" title="查看藥品外觀照片"><i class="bi bi-card-image"></i></button>`;

            item.innerHTML = `
                <div class="med-header-row">
                    <div class="med-title-block">
                        <div class="med-brand-row">
                            <span class="med-brand-name">${escapeHtml(brand)}</span>${photoBtn}
                            ${doseText}
                        </div>
                        ${hasGeneric ? `
                            <div class="med-generic-row">
                                <span class="med-generic-tag"><i class="bi bi-capsule"></i> 成分 (Generic)</span>
                                <span class="med-generic-name">${escapeHtml(generic)}</span>
                            </div>
                        ` : ''}
                    </div>
                    <span class="med-freq-badge">${escapeHtml(m.method || '')}</span>
                </div>
                <div class="med-sub-row">
                    <span>${m.is_chronic_refill ? '<span class="badge badge-primary">慢箋</span>' : ''} ${m.total_days}日份 ${m.nhicode ? `<span class="text-muted" style="margin-left:4px;">(${escapeHtml(m.nhicode)})</span>` : ''}</span>
                    <span>預計服至: ${formatShortDate(m.end_date)} ${m.is_active ? `<span class="days-remain-badge">(餘 ${m.days_remaining} 天)</span>` : ''}</span>
                </div>
                ${m.contraindicated ? `<div class="text-danger" style="font-size:11px; margin-top:4px;"><strong>警示:</strong> ${escapeHtml(m.contra_reason)}</div>` : ''}
            `;
            container.appendChild(item);
        });
    }
}

/**
 * Open Drug Photo & Identification Modal
 */
async function openDrugPhotoModal(brand, code, generic, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    const modal = document.getElementById("drugPhotoModal");
    const dialog = document.getElementById("drugPhotoModalDialog");
    const titleEl = document.getElementById("drugPhotoModalTitle");
    const bodyEl = document.getElementById("drugPhotoModalBody");
    if (!modal || !bodyEl) return;

    modal.classList.remove("d-none");
    modal.style.display = "flex";
    if (titleEl) {
        titleEl.textContent = brand ? `${brand}` : "藥品實體照片與辨識特徵";
    }

    // Default positioning on first open if user hasn't moved it yet
    if (dialog && !dialog.dataset.userPositioned) {
        const winW = window.innerWidth;
        const winH = window.innerHeight;
        const dialogW = dialog.classList.contains("is-expanded") ? 960 : 640;
        const initialLeft = Math.max(15, Math.floor((winW - Math.min(dialogW, winW - 30)) / 2));
        const initialTop = Math.max(40, Math.floor((winH - 580) / 2));
        dialog.style.position = "fixed";
        dialog.style.left = `${initialLeft}px`;
        dialog.style.top = `${initialTop}px`;
        dialog.style.margin = "0";
    }

    bodyEl.innerHTML = `
        <div class="loading-spinner" style="text-align:center; padding:28px;">
            <i class="bi bi-arrow-repeat spin" style="font-size:24px; color:var(--brand-primary);"></i>
            <p style="margin-top:10px; font-weight:600;">正在檢索藥品實體外觀圖資與辨識特徵...</p>
            <p style="font-size:12px; color:var(--text-muted);">${escapeHtml(brand || '')} ${code ? `(${escapeHtml(code)})` : ''}</p>
        </div>
    `;

    try {
        const queryParams = new URLSearchParams({
            brand: brand || "",
            code: code || "",
            generic: generic || ""
        });
        const res = await fetch(`/api/drug_info?${queryParams.toString()}`);
        const data = await res.json();

        if (data.status === "success" && data.found) {
            let photoSection = "";
            if (data.has_photo && data.photo_url) {
                photoSection = `
                    <div class="drug-photo-viewer-container">
                        <div class="drug-photo-toolbar">
                            <div class="drug-photo-toolbar-left">
                                <span class="text-primary fw-bold" style="font-size:12px;"><i class="bi bi-card-image"></i> 外觀實體照</span>
                                <span class="drug-photo-hint"><i class="bi bi-info-circle"></i> 滾輪可縮放，放大時可拖曳平移</span>
                            </div>
                            <div class="drug-photo-zoom-controls">
                                <button type="button" class="btn-zoom-tool" id="btnDrugZoomOut" title="縮小 (滾輪向下)"><i class="bi bi-dash-lg"></i></button>
                                <span class="zoom-level-indicator" id="drugZoomLevel">100%</span>
                                <button type="button" class="btn-zoom-tool" id="btnDrugZoomIn" title="放大 (滾輪向上)"><i class="bi bi-plus-lg"></i></button>
                                <button type="button" class="btn-zoom-tool" id="btnDrugZoomReset" title="重設大小 (100%)">1:1</button>
                                <button type="button" class="btn-zoom-tool" id="btnDrugZoom2X" title="2倍放大檢視 (200%)"><i class="bi bi-search"></i> 2X</button>
                            </div>
                        </div>
                        <div class="drug-modal-photo-viewport" id="drugPhotoViewport">
                            <img src="${data.photo_url}" alt="${escapeHtml(data.brand_name_en || brand)}" 
                                 class="drug-modal-photo-img" id="drugModalPhotoImg" 
                                 title="點擊放大/還原，滑鼠滾輪可任意縮放，按住可平移" draggable="false">
                        </div>
                    </div>
                `;
            } else {
                photoSection = `
                    <div class="drug-photo-viewer-container" style="align-items:center; justify-content:center; padding:35px 20px; text-align:center; color:var(--text-muted);">
                        <i class="bi bi-camera-fill" style="font-size:42px; opacity:0.35;"></i>
                        <p class="mt-2 fw-bold" style="font-size:13.5px; color:var(--text-secondary);">此藥品暫無實體圖檔</p>
                        <span class="text-muted" style="font-size:11.5px;">可依據下方健保審定之外觀刻痕、形狀與顏色資料進行臨床辨識</span>
                    </div>
                `;
            }

            bodyEl.innerHTML = `
                <div class="drug-modal-content-grid">
                    ${photoSection}
                    <div class="drug-modal-details-card">
                        ${data.brand_name_zh ? `
                            <div class="drug-modal-row">
                                <span class="drug-modal-label">中文品名</span>
                                <span class="drug-modal-val fw-bold" style="color:var(--brand-primary);">${escapeHtml(data.brand_name_zh)}</span>
                            </div>
                        ` : ''}
                        <div class="drug-modal-row">
                            <span class="drug-modal-label">英文品名</span>
                            <span class="drug-modal-val fw-bold">${escapeHtml(data.brand_name_en || brand)}</span>
                        </div>
                        <div class="drug-modal-row">
                            <span class="drug-modal-label">主成分規格</span>
                            <span class="drug-modal-val">${escapeHtml(data.generic_name || generic || '--')} ${data.strength ? `<span class="badge badge-meta">${escapeHtml(data.strength)}</span>` : ''}</span>
                        </div>
                        <div class="drug-modal-row">
                            <span class="drug-modal-label">健保代碼</span>
                            <span class="drug-modal-val font-mono">${escapeHtml(data.nhi_code || code || '--')}</span>
                        </div>
                        ${data.tfda_license_id ? `
                            <div class="drug-modal-row">
                                <span class="drug-modal-label">藥證字號</span>
                                <span class="drug-modal-val">${escapeHtml(data.tfda_license_id)}</span>
                            </div>
                        ` : ''}
                        ${data.manufacturer ? `
                            <div class="drug-modal-row">
                                <span class="drug-modal-label">製造藥廠</span>
                                <span class="drug-modal-val">${escapeHtml(data.manufacturer)}</span>
                            </div>
                        ` : ''}
                        ${(data.appearance_shape || data.appearance_color || data.appearance_markings || data.dosage_form) ? `
                            <div class="drug-modal-row" style="margin-top:8px; padding-top:8px; border-top:1px dashed var(--border-color);">
                                <span class="drug-modal-label">外觀特徵</span>
                                <div class="drug-modal-val d-flex flex-wrap gap-1">
                                    ${data.dosage_form ? `<span class="badge badge-outline">劑型: ${escapeHtml(data.dosage_form)}</span>` : ''}
                                    ${data.appearance_shape ? `<span class="badge badge-outline">形狀: ${escapeHtml(data.appearance_shape)}</span>` : ''}
                                    ${data.appearance_color ? `<span class="badge badge-outline">顏色: ${escapeHtml(data.appearance_color)}</span>` : ''}
                                    ${data.appearance_markings ? `<span class="badge badge-meta">刻痕/字樣: ${escapeHtml(data.appearance_markings)}</span>` : ''}
                                    ${data.has_score_line ? `<span class="badge badge-meta">剝痕: ${escapeHtml(data.has_score_line)}</span>` : ''}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;

            if (data.has_photo && data.photo_url) {
                initDrugPhotoZoomViewer();
            }
        } else {
            bodyEl.innerHTML = `
                <div class="p-4 text-center">
                    <i class="bi bi-info-circle text-warning" style="font-size:32px;"></i>
                    <p class="mt-2 fw-bold">未找到此藥品的外觀建檔資料</p>
                    <p class="text-muted small">${escapeHtml(brand || '')} (健保碼: ${escapeHtml(code || '無')})</p>
                </div>
            `;
        }
    } catch (err) {
        bodyEl.innerHTML = `
            <div class="p-4 text-center">
                <i class="bi bi-exclamation-triangle text-danger" style="font-size:32px;"></i>
                <p class="mt-2 fw-bold">外觀圖資讀取失敗</p>
                <p class="text-muted small">${escapeHtml(err.message || String(err))}</p>
            </div>
        `;
    }
}

/**
 * Interactive Image Zoom and Pan for Drug Photo Viewer
 */
function initDrugPhotoZoomViewer() {
    const viewport = document.getElementById("drugPhotoViewport");
    const img = document.getElementById("drugModalPhotoImg");
    const zoomLevelEl = document.getElementById("drugZoomLevel");
    const btnIn = document.getElementById("btnDrugZoomIn");
    const btnOut = document.getElementById("btnDrugZoomOut");
    const btnReset = document.getElementById("btnDrugZoomReset");
    const btn2X = document.getElementById("btnDrugZoom2X");

    if (!viewport || !img) return;

    let scale = 1.0;
    let panX = 0;
    let panY = 0;
    let isPanning = false;
    let startMouseX = 0, startMouseY = 0;
    let startPanX = 0, startPanY = 0;
    let didPanMove = false;

    function applyTransform() {
        img.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
        if (zoomLevelEl) {
            zoomLevelEl.textContent = `${Math.round(scale * 100)}%`;
        }
        if (scale > 1.05) {
            viewport.classList.add("is-zoomed");
            img.style.cursor = isPanning ? "grabbing" : "grab";
        } else {
            viewport.classList.remove("is-zoomed");
            img.style.cursor = "zoom-in";
            panX = 0;
            panY = 0;
            img.style.transform = `translate(0px, 0px) scale(${scale})`;
        }
    }

    function setScale(newScale, centerPan = false) {
        scale = Math.max(0.6, Math.min(4.0, Number(newScale.toFixed(2))));
        if (scale <= 1.05 || centerPan) {
            panX = 0;
            panY = 0;
        }
        applyTransform();
    }

    if (btnIn) btnIn.onclick = () => setScale(scale + 0.25);
    if (btnOut) btnOut.onclick = () => setScale(scale - 0.25);
    if (btnReset) btnReset.onclick = () => setScale(1.0, true);
    if (btn2X) btn2X.onclick = () => setScale(2.0, true);

    // Mouse wheel zoom
    viewport.onwheel = (e) => {
        e.preventDefault();
        const step = e.deltaY < 0 ? 0.2 : -0.2;
        setScale(scale + step);
    };

    // Drag to Pan when zoomed
    viewport.onmousedown = (e) => {
        if (e.button !== 0) return;
        if (scale > 1.05) {
            isPanning = true;
            didPanMove = false;
            startMouseX = e.clientX;
            startMouseY = e.clientY;
            startPanX = panX;
            startPanY = panY;
            viewport.classList.add("is-panning");
            e.preventDefault();
        }
    };

    const onMouseMove = (e) => {
        if (!isPanning) return;
        const dx = e.clientX - startMouseX;
        const dy = e.clientY - startMouseY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
            didPanMove = true;
        }
        panX = startPanX + dx;
        panY = startPanY + dy;
        applyTransform();
    };

    const onMouseUp = () => {
        if (isPanning) {
            isPanning = false;
            viewport.classList.remove("is-panning");
            if (scale > 1.05) {
                img.style.cursor = "grab";
            }
        }
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    // Click to toggle zoom (if not dragging/panning)
    img.onclick = () => {
        if (didPanMove) return;
        if (scale < 1.4) {
            setScale(2.2, true);
        } else {
            setScale(1.0, true);
        }
    };

    applyTransform();
}

/**
 * Enables smooth window dragging for the floating drug photo modal
 */
function initDrugModalDraggable() {
    const header = document.getElementById("drugPhotoModalHeader");
    const dialog = document.getElementById("drugPhotoModalDialog");
    if (!header || !dialog) return;

    let isDragging = false;
    let startX = 0, startY = 0;
    let initialLeft = 0, initialTop = 0;

    header.addEventListener("mousedown", (e) => {
        // Ignore if clicking close or expand buttons
        if (e.target.closest("button") || e.target.closest(".modal-close-btn") || e.target.closest(".modal-action-btn")) {
            return;
        }
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;

        const rect = dialog.getBoundingClientRect();
        initialLeft = rect.left;
        initialTop = rect.top;

        dialog.style.position = "fixed";
        dialog.style.left = `${initialLeft}px`;
        dialog.style.top = `${initialTop}px`;
        dialog.style.margin = "0";

        header.classList.add("is-dragging");
        e.preventDefault();
    });

    window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        let newLeft = initialLeft + dx;
        let newTop = initialTop + dy;

        const dialogW = dialog.offsetWidth;
        const maxLeft = Math.max(10, window.innerWidth - dialogW - 10);
        const maxTop = Math.max(10, window.innerHeight - 50);

        newLeft = Math.max(10, Math.min(maxLeft, newLeft));
        newTop = Math.max(10, Math.min(maxTop, newTop));

        dialog.style.left = `${newLeft}px`;
        dialog.style.top = `${newTop}px`;
        dialog.dataset.userPositioned = "true";
    });

    window.addEventListener("mouseup", () => {
        if (isDragging) {
            isDragging = false;
            header.classList.remove("is-dragging");
        }
    });
}

/**
 * Toggle Drug Photo Modal Expand / Compact Width
 */
function toggleDrugModalExpand() {
    const dialog = document.getElementById("drugPhotoModalDialog");
    const btn = document.getElementById("expandDrugPhotoModalBtn");
    if (!dialog || !btn) return;

    dialog.classList.toggle("is-expanded");
    const isExpanded = dialog.classList.contains("is-expanded");
    btn.innerHTML = isExpanded ? `<i class="bi bi-fullscreen-exit"></i>` : `<i class="bi bi-arrows-fullscreen"></i>`;
    btn.title = isExpanded ? "還原視窗寬度" : "放大視窗寬度";

    // Reclamp within screen
    const rect = dialog.getBoundingClientRect();
    const maxLeft = Math.max(10, window.innerWidth - dialog.offsetWidth - 10);
    const maxTop = Math.max(10, window.innerHeight - 50);
    const clampedLeft = Math.max(10, Math.min(maxLeft, rect.left));
    const clampedTop = Math.max(10, Math.min(maxTop, rect.top));
    dialog.style.left = `${clampedLeft}px`;
    dialog.style.top = `${clampedTop}px`;
}

function openDrugPhotoModalFromBtn(btn, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    const brand = btn.getAttribute("data-brand") || "";
    const code = btn.getAttribute("data-code") || "";
    const generic = btn.getAttribute("data-generic") || "";
    openDrugPhotoModal(brand, code, generic, event);
}

function closeDrugPhotoModal() {
    const modal = document.getElementById("drugPhotoModal");
    if (modal) {
        modal.classList.add("d-none");
        modal.style.display = "none";
    }
}

async function triggerAiExtract(reportIndex) {
    if (!currentPatientData) return;
    const reports = currentPatientData.findings.radiology_reports || [];
    const rep = reports[reportIndex];
    if (!rep) return;

    const modal = document.getElementById("aiModal");
    const body = document.getElementById("aiModalBody");
    modal.classList.remove("d-none");
    body.innerHTML = `
        <div class="loading-spinner" style="text-align:center; padding:24px;">
            <i class="bi bi-arrow-repeat spin" style="font-size:24px; color:var(--brand-primary);"></i>
            <p style="margin-top:10px; font-weight:600;">AI server 正在進行本地深度臨床萃取...</p>
            <p style="font-size:12px; color:var(--text-muted);">針對 ${rep.modality} 報告進行語意病灶尺寸分析</p>
        </div>
    `;

    try {
        const res = await fetch("/api/extract_ai", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: rep.raw_summary,
                modality: rep.modality
            })
        });
        const data = await res.json();

        if (data.status === "success" && data.result) {
            const r = data.result;
            let findingsHtml = "";
            (r.main_findings || []).forEach(f => {
                findingsHtml += `<li><i class="bi bi-check-circle-fill text-success"></i> ${f}</li>`;
            });

            let measHtml = "";
            (r.measurements || []).forEach(m => {
                measHtml += `
                    <div class="measurement-pill" style="margin:4px;">
                        <i class="bi bi-rulers"></i> <strong>${m.site || ''}</strong>: ${m.size || m.dimension || ''} (${m.description || ''})
                    </div>
                `;
            });

            body.innerHTML = `
                <div style="margin-bottom:12px;">
                    <h4 style="font-size:14px; font-weight:700; color:var(--brand-primary); margin-bottom:6px;">
                        <i class="bi bi-file-medical"></i> 臨床總結 (Impression)
                    </h4>
                    <p style="font-size:13px; line-height:1.5; background:var(--bg-base); padding:10px; border-radius:6px;">
                        ${r.impression || '無摘要'}
                    </p>
                </div>
                ${findingsHtml ? `
                    <div style="margin-bottom:12px;">
                        <h4 style="font-size:14px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">主要臨床異常發現</h4>
                        <ul style="list-style:none; font-size:13px; line-height:1.6;">${findingsHtml}</ul>
                    </div>
                ` : ''}
                ${measHtml ? `
                    <div>
                        <h4 style="font-size:14px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">病灶與裝置尺寸 (Lesion & Device Sizing)</h4>
                        <div style="display:flex; flex-wrap:wrap;">${measHtml}</div>
                    </div>
                ` : ''}
            `;
        } else {
            body.innerHTML = `<div class="empty-state text-danger">AI 萃取失敗：${data.message || '未知錯誤'}</div>`;
        }
    } catch (e) {
        body.innerHTML = `<div class="empty-state text-danger">連線異常：${e}</div>`;
    }
}

/* ==========================================================================
   Clinical Chat Dock Functions
   ========================================================================== */

function toggleChatDock(expandOnly = false) {
    const dock = document.getElementById("clinicalChatDock");
    const icon = document.getElementById("toggleChatIcon");
    if (!dock) return;

    if (expandOnly) {
        dock.classList.remove("collapsed");
        if (icon) icon.className = "bi bi-chevron-down";
    } else {
        dock.classList.toggle("collapsed");
        const isCollapsed = dock.classList.contains("collapsed");
        if (icon) icon.className = isCollapsed ? "bi bi-chevron-up" : "bi bi-chevron-down";
    }

    if (!dock.classList.contains("collapsed")) {
        const input = document.getElementById("chatInput");
        if (input) setTimeout(() => input.focus(), 150);
        scrollChatToBottom();
    }
}

async function sendChatMessage() {
    const input = document.getElementById("chatInput");
    if (!input) return;
    const query = input.value.trim();
    if (!query) return;

    if (!currentPatientData) {
        alert("請先載入病患資料後再進行提問");
        return;
    }

    // Ensure dock is expanded
    toggleChatDock(true);

    // Append user message
    appendChatMessage("user", query);
    chatHistory.push({ role: "user", content: query });
    input.value = "";

    // Show temporary typing indicator
    const typingId = "typing-" + Date.now();
    appendTypingIndicator(typingId);
    scrollChatToBottom();

    const sendBtn = document.getElementById("sendChatBtn");
    if (sendBtn) sendBtn.disabled = true;

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                patient_id: currentPatientData.patient_id,
                clinic_date: currentPatientData.clinic_date || "2026/09/01",
                message: query,
                history: chatHistory.slice(-6)
            })
        });

        removeElement(typingId);
        if (sendBtn) sendBtn.disabled = false;

        const data = await res.json();
        if (data.status === "success" && data.reply) {
            appendChatMessage("assistant", data.reply);
            chatHistory.push({ role: "assistant", content: data.reply });
        } else {
            appendChatMessage("assistant", `⚠️ 諮詢助理未能產生回應：${data.message || '未知錯誤'}`);
        }
    } catch (e) {
        removeElement(typingId);
        if (sendBtn) sendBtn.disabled = false;
        appendChatMessage("assistant", `⚠️ 連線錯誤：${e.message || e}`);
    }

    scrollChatToBottom();
}

function appendChatMessage(role, text) {
    const container = document.getElementById("chatMessagesContainer");
    if (!container) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.innerHTML = role === "user" ? '<i class="bi bi-person-fill"></i>' : '<i class="bi bi-robot"></i>';

    const content = document.createElement("div");
    content.className = "message-content";
    content.innerHTML = formatMessageContent(text);

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(content);
    container.appendChild(msgDiv);
}

function appendTypingIndicator(id) {
    const container = document.getElementById("chatMessagesContainer");
    if (!container) return;

    const msgDiv = document.createElement("div");
    msgDiv.id = id;
    msgDiv.className = "chat-message assistant-message";
    msgDiv.innerHTML = `
        <div class="message-avatar"><i class="bi bi-robot"></i></div>
        <div class="message-content text-muted" style="font-style:italic;">
            <i class="bi bi-arrow-repeat spin"></i> AI server 正在依據病歷資料深度研析中...
        </div>
    `;
    container.appendChild(msgDiv);
}

function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function clearChatHistory() {
    chatHistory = [];
    const container = document.getElementById("chatMessagesContainer");
    if (container) {
        container.innerHTML = `
            <div class="chat-message assistant-message">
                <div class="message-avatar"><i class="bi bi-robot"></i></div>
                <div class="message-content">
                    已清除對話紀錄。您可以隨時提問關於目前病患之病情診斷、檢驗數值、影像與處置病灶、或進行中處方與慢箋劑量。
                </div>
            </div>
        `;
    }
}

function scrollChatToBottom() {
    const container = document.getElementById("chatMessagesContainer");
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function formatMessageContent(text) {
    if (!text) return "";
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Bullet points • or -
    const lines = html.split("\n");
    let inList = false;
    let result = [];

    for (let line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("• ") || trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
            if (!inList) {
                result.push("<ul>");
                inList = true;
            }
            result.push(`<li>${trimmed.substring(2)}</li>`);
        } else {
            if (inList) {
                result.push("</ul>");
                inList = false;
            }
            if (trimmed) {
                result.push(`<p>${trimmed}</p>`);
            }
        }
    }
    if (inList) {
        result.push("</ul>");
    }

    return result.join("");
}

/* ==========================================================================
   Laboratory Trends & Drug Effect Timeline Correlation Controller
   ========================================================================== */

/**
 * Populate variable selector checkboxes for laboratory data and medications
 */
function initCorrelationSelectors() {
    if (!currentPatientData) return;
    const labContainer = document.getElementById("corrLabListContainer");
    const medContainer = document.getElementById("corrMedListContainer");
    if (!labContainer || !medContainer) return;

    labContainer.innerHTML = "";
    medContainer.innerHTML = "";

    // 1. Gather all lab items with actual numeric results
    const categories = currentPatientData.findings?.lab_panel?.flowsheet?.categories || [];
    const allLabItems = [];

    categories.forEach(cat => {
        (cat.items || []).forEach(item => {
            const count = Object.keys(item.values || {}).length;
            if (count > 0) {
                allLabItems.push({
                    item: item.item,
                    category: cat.name || cat.id || "",
                    unit: item.unit || "",
                    ref: item.ref || "",
                    count: count,
                    values: item.values
                });
            }
        });
    });

    // Clinical priority sorting for lab items (Metabolic, Renal, Liver, Hematological first)
    const PRIORITY_LABS = ["glucose", "hba1c", "creatinine", "egfr", "ast", "alt", "platelet", "albumin", "bilirubin", "bun", "uric", "hb", "wbc"];
    allLabItems.sort((a, b) => {
        const aPri = PRIORITY_LABS.findIndex(k => a.item.toLowerCase().includes(k));
        const bPri = PRIORITY_LABS.findIndex(k => b.item.toLowerCase().includes(k));
        if (aPri !== -1 && bPri !== -1) return aPri - bPri;
        if (aPri !== -1) return -1;
        if (bPri !== -1) return 1;
        return b.count - a.count;
    });

    allLabItems.forEach(it => {
        const lbl = document.createElement("label");
        lbl.className = "corr-var-label";
        lbl.dataset.name = it.item.toLowerCase();
        lbl.innerHTML = `
            <input type="checkbox" class="corr-lab-cb" value="${escapeHtml(it.item)}" ${selectedCorrLabs.has(it.item) ? 'checked' : ''}>
            <span class="corr-var-name">${escapeHtml(it.item)}</span>
            <span class="badge badge-meta">${escapeHtml(it.unit || '')}</span>
            <span class="corr-data-count text-muted">(${it.count}筆)</span>
        `;
        const cb = lbl.querySelector("input");
        cb.addEventListener("change", (e) => {
            if (e.target.checked) selectedCorrLabs.add(it.item);
            else selectedCorrLabs.delete(it.item);
            updateSelectedBadges();
        });
        labContainer.appendChild(lbl);
    });

    // 2. Gather all medication items
    const drugs = currentPatientData.medications?.timeline?.drugs || [];
    // Sort active drugs first, then by total episode count
    const sortedDrugs = drugs.slice().sort((a, b) => {
        if (a.is_active_now !== b.is_active_now) return a.is_active_now ? -1 : 1;
        return (b.episodes || []).length - (a.episodes || []).length;
    });

    sortedDrugs.forEach(d => {
        const drugKey = (d.generic_name || '') + '|' + (d.brand_name || '');
        const lbl = document.createElement("label");
        lbl.className = "corr-var-label";
        lbl.dataset.name = ((d.brand_name || '') + ' ' + (d.generic_name || '')).toLowerCase();
        lbl.innerHTML = `
            <input type="checkbox" class="corr-med-cb" value="${escapeHtml(drugKey)}" ${selectedCorrMeds.has(drugKey) ? 'checked' : ''}>
            <span class="corr-var-name">${escapeHtml(d.brand_name)}</span>
            <span class="text-muted small">(${escapeHtml(d.generic_name)})</span>
            ${d.dose ? `<span class="med-dose-badge">${escapeHtml(d.dose)}</span>` : ''}
            ${d.is_active_now ? '<span class="badge badge-success badge-xs">進行中</span>' : '<span class="badge badge-outline badge-xs">過往</span>'}
        `;
        const cb = lbl.querySelector("input");
        cb.addEventListener("change", (e) => {
            if (e.target.checked) selectedCorrMeds.add(drugKey);
            else selectedCorrMeds.delete(drugKey);
            updateSelectedBadges();
        });
        medContainer.appendChild(lbl);
    });

    corrSelectorsInitialized = true;

    // Default preset: Glucose & DM Meds if nothing selected yet
    if (selectedCorrLabs.size === 0 && selectedCorrMeds.size === 0) {
        applyCorrelationPreset("glucose");
    } else {
        updateSelectedBadges();
    }
}

/**
 * Apply clinical correlation presets
 */
function applyCorrelationPreset(preset) {
    selectedCorrLabs.clear();
    selectedCorrMeds.clear();

    if (preset === "clear") {
        syncCorrCheckboxes();
        updateSelectedBadges();
        const container = document.getElementById("corrTimelineContainer");
        if (container) {
            container.innerHTML = `
                <div class="empty-state p-5 text-center">
                    <i class="bi bi-bezier2" style="font-size:36px; color:var(--brand-primary); opacity:0.6;"></i>
                    <p class="mt-2 fw-bold">已清除選取項目</p>
                    <p class="text-muted small">請勾選欲對照之檢驗項目與藥物，再點擊「執行繪圖」。</p>
                </div>
            `;
        }
        return;
    }

    if (!currentPatientData) return;
    const allLabItems = [];
    (currentPatientData.findings?.lab_panel?.flowsheet?.categories || []).forEach(c => {
        (c.items || []).forEach(it => {
            if (Object.keys(it.values || {}).length > 0) allLabItems.push(it);
        });
    });
    const drugs = currentPatientData.medications?.timeline?.drugs || [];

    if (preset === "glucose") {
        // Find Glucose AC / HbA1c
        allLabItems.forEach(it => {
            const name = it.item.toLowerCase();
            if (name.includes("glucose") || name.includes("hba1c") || name.includes("血糖")) {
                selectedCorrLabs.add(it.item);
            }
        });
        // Find DM drugs (repaglinide, trajenta, metformin, glimepiride, insulin, janumet, forxiga, jardiance, etc.)
        drugs.forEach(d => {
            const text = `${d.brand_name} ${d.generic_name} ${d.category}`.toLowerCase();
            if (text.includes("repaglinide") || text.includes("trajenta") || text.includes("metformin") ||
                text.includes("linagliptin") || text.includes("dm") || text.includes("血糖") ||
                text.includes("diamicron") || text.includes("forxiga") || text.includes("jardiance")) {
                selectedCorrMeds.add(`${d.generic_name}|${d.brand_name}`);
            }
        });
    } else if (preset === "renal") {
        allLabItems.forEach(it => {
            const name = it.item.toLowerCase();
            if (name.includes("creatinine") || name.includes("egfr") || name.includes("bun") || name.includes("肌酸酐")) {
                selectedCorrLabs.add(it.item);
            }
        });
        drugs.forEach(d => {
            const text = `${d.brand_name} ${d.generic_name} ${d.category}`.toLowerCase();
            if (text.includes("exnortan") || text.includes("concor") || text.includes("norvasc") ||
                text.includes("isormol") || text.includes("calowlin") || text.includes("valsartan") ||
                text.includes("amlodipine") || text.includes("bisoprolol") || text.includes("blood pressure") ||
                text.includes("cardiovascular") || text.includes("降血壓") || text.includes("renal") || text.includes("腎臟")) {
                selectedCorrMeds.add(`${d.generic_name}|${d.brand_name}`);
            }
        });
    } else if (preset === "antithrombotic") {
        allLabItems.forEach(it => {
            const name = it.item.toLowerCase();
            if (name.includes("platelet") || name.includes("plt") || name.includes("inr") || name.includes("prothrombin")) {
                selectedCorrLabs.add(it.item);
            }
        });
        drugs.forEach(d => {
            const text = `${d.brand_name} ${d.generic_name} ${d.category}`.toLowerCase();
            if (text.includes("plavix") || text.includes("clopidogrel") || text.includes("cofarin") ||
                text.includes("warfarin") || text.includes("aspirin") || text.includes("bokey") ||
                text.includes("antithrombotic") || text.includes("抗凝血")) {
                selectedCorrMeds.add(`${d.generic_name}|${d.brand_name}`);
            }
        });
    } else if (preset === "liver") {
        allLabItems.forEach(it => {
            const name = it.item.toLowerCase();
            if (name.includes("ast") || name.includes("alt") || name.includes("got") ||
                name.includes("gpt") || name.includes("bilirubin") || name.includes("albumin")) {
                selectedCorrLabs.add(it.item);
            }
        });
        drugs.filter(d => d.is_active_now).slice(0, 4).forEach(d => {
            selectedCorrMeds.add(`${d.generic_name}|${d.brand_name}`);
        });
    }

    syncCorrCheckboxes();
    updateSelectedBadges();
    renderCorrelationPlot();
}

function setAllCorrCheckboxes(type, checked) {
    if (type === "labs") {
        document.querySelectorAll("#corrLabListContainer .corr-lab-cb").forEach(cb => {
            cb.checked = checked;
            if (checked) selectedCorrLabs.add(cb.value);
            else selectedCorrLabs.delete(cb.value);
        });
    } else {
        document.querySelectorAll("#corrMedListContainer .corr-med-cb").forEach(cb => {
            cb.checked = checked;
            if (checked) selectedCorrMeds.add(cb.value);
            else selectedCorrMeds.delete(cb.value);
        });
    }
    updateSelectedBadges();
}

function syncCorrCheckboxes() {
    document.querySelectorAll("#corrLabListContainer .corr-lab-cb").forEach(cb => {
        cb.checked = selectedCorrLabs.has(cb.value);
    });
    document.querySelectorAll("#corrMedListContainer .corr-med-cb").forEach(cb => {
        cb.checked = selectedCorrMeds.has(cb.value);
    });
}

function updateSelectedBadges() {
    const lBadge = document.getElementById("selectedLabCountBadge");
    const mBadge = document.getElementById("selectedMedCountBadge");
    if (lBadge) lBadge.textContent = `${selectedCorrLabs.size} 項檢驗`;
    if (mBadge) mBadge.textContent = `${selectedCorrMeds.size} 項用藥`;
}

/**
 * Render Combined Unified Timeline Plot (Lab Trends + Drug Usage)
 */
function renderCorrelationPlot() {
    const container = document.getElementById("corrTimelineContainer");
    if (!container || !currentPatientData) return;

    const allLabItemsMap = {};
    (currentPatientData.findings?.lab_panel?.flowsheet?.categories || []).forEach(c => {
        (c.items || []).forEach(it => {
            allLabItemsMap[it.item] = it;
        });
    });

    const chosenLabs = Array.from(selectedCorrLabs).map(name => allLabItemsMap[name]).filter(Boolean);
    const drugsList = currentPatientData.medications?.timeline?.drugs || [];
    const chosenDrugs = drugsList.filter(d => selectedCorrMeds.has(`${d.generic_name}|${d.brand_name}`));

    if (chosenLabs.length === 0 && chosenDrugs.length === 0) {
        container.innerHTML = `
            <div class="empty-state p-5 text-center">
                <i class="bi bi-exclamation-triangle text-warning" style="font-size:32px;"></i>
                <p class="mt-2 fw-bold">尚未選取任何檢驗或用藥項目</p>
                <p class="text-muted small">請於上方勾選至少一項檢驗或用藥，再點擊「執行繪圖」。</p>
            </div>
        `;
        return;
    }

    const clinicDateStr = currentPatientData.clinic_date || "2026/09/01";
    const clinicDt = parseStandardDate(clinicDateStr) || new Date();
    const clinicTime = clinicDt.getTime();

    // 1. Determine unified timeline bounds across all selected labs and drugs
    let minTime = clinicTime - (90 * 86400000);
    let maxTime = clinicTime + (30 * 86400000);

    chosenLabs.forEach(it => {
        for (const [dStr, v] of Object.entries(it.values || {})) {
            const dt = parseStandardDate(dStr);
            if (dt) {
                const t = dt.getTime();
                if (t < minTime) minTime = t;
                if (t > maxTime) maxTime = t;
            }
        }
    });

    chosenDrugs.forEach(d => {
        (d.episodes || []).forEach(ep => {
            const s = parseStandardDate(ep.start_date);
            const e = parseStandardDate(ep.end_date);
            if (s && s.getTime() < minTime) minTime = s.getTime();
            if (e && e.getTime() > maxTime) maxTime = e.getTime();
        });
    });

    // Add 7 days padding at the end for remaining medications
    maxTime += (7 * 86400000);

    const minDt = new Date(minTime);
    const maxDt = new Date(maxTime);
    const totalDays = Math.max(Math.round((maxTime - minTime) / 86400000), 30);

    // Update Date Span Label
    const dateSpanLabel = document.getElementById("corrPlotDateSpan");
    if (dateSpanLabel) {
        const minStd = `${minDt.getFullYear()}/${String(minDt.getMonth() + 1).padStart(2, '0')}/${String(minDt.getDate()).padStart(2, '0')}`;
        const maxStd = `${maxDt.getFullYear()}/${String(maxDt.getMonth() + 1).padStart(2, '0')}/${String(maxDt.getDate()).padStart(2, '0')}`;
        dateSpanLabel.textContent = `範圍: ${formatShortDate(minStd)} ~ ${formatShortDate(maxStd)} (共 ${totalDays} 天)`;
    }

    const statusBadge = document.getElementById("corrPlotStatusBadge");
    if (statusBadge) {
        statusBadge.textContent = `${chosenLabs.length} 項檢驗 ＋ ${chosenDrugs.length} 項用藥`;
    }

    // 2. Coordinate System: pxPerDay & trackWidth
    const pxPerDay = Math.max(5.5, Math.min(9.0, 1600 / totalDays));
    const trackWidth = Math.round(totalDays * pxPerDay);

    function getX(dt) {
        if (!dt) return 0;
        const diff = dt.getTime() - minTime;
        return Math.round((diff / 86400000) * pxPerDay);
    }

    const currentDateX = getX(clinicDt);

    // 3. Month Segments for Sticky Top Row and Grid Lines
    const months = [];
    const gridLines = [];

    let curYear = minDt.getFullYear();
    let curMonth = minDt.getMonth();
    const endYear = maxDt.getFullYear();
    const endMonth = maxDt.getMonth();

    while (curYear < endYear || (curYear === endYear && curMonth <= endMonth)) {
        const mStart = new Date(curYear, curMonth, 1);
        const mEnd = new Date(curYear, curMonth + 1, 0, 23, 59, 59);

        const clampedStart = mStart.getTime() < minTime ? new Date(minTime) : mStart;
        const clampedEnd = mEnd.getTime() > maxTime ? new Date(maxTime) : mEnd;

        const leftPx = getX(clampedStart);
        const rightPx = getX(clampedEnd) + pxPerDay;
        const widthPx = Math.max(rightPx - leftPx, 24);

        const shortYear = String(curYear).slice(-2);
        const monthNum = String(curMonth + 1).padStart(2, "0");
        const monthLabel = `${shortYear}/${monthNum}`;
        const monthDays = Math.round((clampedEnd.getTime() - clampedStart.getTime()) / 86400000) + 1;

        months.push({
            label: monthLabel,
            days: monthDays,
            left: leftPx,
            width: widthPx
        });

        if (leftPx > 0) gridLines.push(leftPx);

        curMonth++;
        if (curMonth > 11) {
            curMonth = 0;
            curYear++;
        }
    }

    const gridLinesHtml = gridLines.map(x => `<div class="med-grid-line" style="left: ${x}px;"></div>`).join("");

    const monthHeadersHtml = months.map(m => `
        <div style="position: absolute; left: ${m.left}px; width: ${m.width}px; height: 100%; border-right: 1px solid var(--border-color); display: flex; flex-direction: column; justify-content: center; align-items: center; user-select: none;">
            <span style="font-weight: 700; font-size: 11px; color: var(--text-primary); font-family: var(--font-mono);">${m.label}</span>
            <span style="font-size: 9px; color: var(--text-muted);">${m.days}天</span>
        </div>
    `).join("");

    // 4. Build Table Body Rows
    let tbodyHtml = "";

    // Section 1: Laboratory Trends (if any chosen)
    if (chosenLabs.length > 0) {
        tbodyHtml += `
            <tr class="corr-section-divider-row">
                <td colspan="2">
                    <i class="bi bi-eyedropper"></i> 1. 檢驗數值變化趨勢 (Laboratory Trend Curves) (${chosenLabs.length} 項)
                </td>
            </tr>
        `;

        chosenLabs.forEach(it => {
            const rawPts = [];
            for (const [dStr, vObj] of Object.entries(it.values || {})) {
                const dt = parseStandardDate(dStr);
                const vNum = vObj.val_num;
                if (dt && vNum !== null && vNum !== undefined && !isNaN(vNum)) {
                    rawPts.push({
                        date: dStr,
                        time: dt.getTime(),
                        x: getX(dt),
                        val_num: vNum,
                        val_str: vObj.val || String(vNum),
                        abnormal: vObj.abnormal || false,
                        status_tag: vObj.status_tag || "normal"
                    });
                }
            }
            rawPts.sort((a, b) => a.time - b.time);

            const { low: refLow, high: refHigh } = parseRefRange(it.ref);

            let minV = rawPts.length > 0 ? Math.min(...rawPts.map(p => p.val_num)) : 0;
            let maxV = rawPts.length > 0 ? Math.max(...rawPts.map(p => p.val_num)) : 100;
            if (refLow !== null) minV = Math.min(minV, refLow);
            if (refHigh !== null) maxV = Math.max(maxV, refHigh);

            const vRange = maxV - minV;
            const pad = vRange > 0 ? vRange * 0.15 : (minV > 0 ? minV * 0.2 : 5);
            const scaleMin = Math.max(0, minV - pad);
            const scaleMax = maxV + pad;

            const chartH = 140;
            const topM = 22;
            const botM = 118;
            const plotH = botM - topM;

            function getY(v) {
                if (scaleMax === scaleMin) return topM + plotH / 2;
                return Math.round(botM - ((v - scaleMin) / (scaleMax - scaleMin)) * plotH);
            }

            // Reference range shaded band
            let refBandSvg = "";
            if (refLow !== null && refHigh !== null) {
                const bandY1 = getY(refHigh);
                const bandY2 = getY(refLow);
                refBandSvg = `
                    <rect x="0" y="${bandY1}" width="${trackWidth}" height="${Math.max(bandY2 - bandY1, 2)}" fill="rgba(16, 185, 129, 0.08)" stroke="rgba(16, 185, 129, 0.3)" stroke-dasharray="4,3"/>
                    <text x="${Math.min(currentDateX, trackWidth - 100)}" y="${bandY1 - 4}" fill="#059669" font-size="9.5" font-weight="600" text-anchor="end">正常參考區間: ${refLow} ~ ${refHigh} ${escapeHtml(it.unit || '')}</text>
                `;
            }

            // Trend line and area
            const linePoints = rawPts.map(p => `${p.x} ${getY(p.val_num)}`);
            const polylineSvg = rawPts.length > 1 ? `
                <path d="M ${rawPts[0].x} ${botM} L ${linePoints.join(' L ')} L ${rawPts[rawPts.length - 1].x} ${botM} Z" fill="rgba(59, 130, 246, 0.12)" />
                <path d="M ${linePoints.join(' L ')}" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
            ` : '';

            // Data Point Circles & Value Labels
            const dotsSvg = rawPts.map(p => {
                const py = getY(p.val_num);
                const isHigh = p.status_tag === 'critical_high' || (p.abnormal && p.val_num > (refHigh || 999999));
                const isLow = p.status_tag === 'critical_low' || (p.abnormal && p.val_num < (refLow || 0));
                const dotColor = isHigh ? '#dc2626' : (isLow ? '#2563eb' : '#10b981');
                const textColor = p.abnormal ? dotColor : 'var(--text-primary)';
                return `
                    <circle cx="${p.x}" cy="${py}" r="4.5" fill="#ffffff" stroke="${dotColor}" stroke-width="2.5" style="pointer-events: auto; cursor: pointer;">
                        <title>${formatShortDate(p.date)}: ${p.val_str} (${p.status_tag || (p.abnormal ? '異常' : '正常')})</title>
                    </circle>
                    <text x="${p.x}" y="${py - 7}" text-anchor="middle" font-size="10" font-weight="700" fill="${textColor}" font-family="var(--font-mono)">${p.val_num}</text>
                `;
            }).join('');

            const latestPt = rawPts.length > 0 ? rawPts[rawPts.length - 1] : null;

            tbodyHtml += `
                <tr>
                    <td class="corr-lab-y-cell">
                        <div style="font-weight: 700; font-size: 12.5px; color: var(--text-primary); display: flex; align-items: center; justify-content: space-between;">
                            <span><i class="bi bi-eyedropper text-primary"></i> ${escapeHtml(it.item)}</span>
                            <span class="badge badge-meta">${escapeHtml(it.unit || '')}</span>
                        </div>
                        <div class="mt-1" style="font-size: 11px; color: var(--text-secondary);">
                            參考區間: <strong>${escapeHtml(it.ref || '未提供')}</strong>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-2" style="font-family: var(--font-mono); font-size: 10.5px;">
                            <span class="text-muted">Min: <strong>${minV}</strong> | Max: <strong>${maxV}</strong></span>
                            ${latestPt ? `<span class="badge badge-primary">最新: ${escapeHtml(latestPt.val_str)}</span>` : ''}
                        </div>
                    </td>
                    <td class="corr-lab-track-cell" style="width: ${trackWidth}px; min-width: ${trackWidth}px; height: ${chartH}px;">
                        ${gridLinesHtml}
                        <div class="med-current-date-line" style="left: ${currentDateX}px;"></div>
                        <svg width="${trackWidth}" height="${chartH}" style="position: absolute; top: 0; left: 0; pointer-events: none; z-index: 5;">
                            ${refBandSvg}
                            ${polylineSvg}
                            ${dotsSvg}
                        </svg>
                    </td>
                </tr>
            `;
        });
    }

    // Section 2: Concurrent Medications (if any chosen)
    if (chosenDrugs.length > 0) {
        tbodyHtml += `
            <tr class="corr-section-divider-row">
                <td colspan="2">
                    <i class="bi bi-capsule"></i> 2. 同期用藥處方時序 (Concurrent Medication Regimens) (${chosenDrugs.length} 項)
                </td>
            </tr>
        `;

        chosenDrugs.forEach(d => {
            const episodes = d.episodes || [];

            // Multi-lane allocation to prevent collisions if same drug has overlapping episodes
            const lanes = [];
            const epLanes = [];

            episodes.forEach(ep => {
                const sDt = parseStandardDate(ep.start_date);
                const eDt = parseStandardDate(ep.end_date);
                const sTime = sDt ? sDt.getTime() : 0;
                const eTime = eDt ? eDt.getTime() : 0;

                let placedLane = -1;
                for (let i = 0; i < lanes.length; i++) {
                    if (sTime >= lanes[i]) {
                        placedLane = i;
                        lanes[i] = eTime;
                        break;
                    }
                }
                if (placedLane === -1) {
                    placedLane = lanes.length;
                    lanes.push(eTime);
                }
                epLanes.push(placedLane);
            });

            const numLanes = Math.max(lanes.length, 1);
            const rowHeight = numLanes === 1 ? 42 : (numLanes * 32 + 10);

            // Build Prescription Bars HTML
            let barsHtml = "";
            episodes.forEach((ep, epIdx) => {
                const sDt = parseStandardDate(ep.start_date);
                const eDt = parseStandardDate(ep.end_date);
                if (!sDt || !eDt) return;

                const barLeft = getX(sDt);
                const barRight = getX(eDt) + pxPerDay;
                const barWidth = Math.max(barRight - barLeft, 22);
                const lane = epLanes[epIdx] || 0;
                const topOffset = numLanes === 1 ? 7 : (lane * 32 + 6);
                const barHeight = numLanes === 1 ? 28 : 26;

                // Tooltip Details
                const tooltipText = [
                    `【${d.brand_name}】(${d.generic_name})`,
                    `劑量頻率: ${ep.dose || d.dose || '--'} | ${ep.method || d.method || '--'}`,
                    `處方區間: ${formatShortDate(ep.start_date)} ~ ${formatShortDate(ep.end_date)} (共 ${ep.total_days} 日份)`,
                    ep.is_chronic_refill ? '★ 慢性病連續處方箋 (慢箋)' : '一般門診處方',
                    ep.is_active ? `★ 進行中處方：至門診日已服 ${ep.consumed} 天，尚餘藥量 ${ep.remains} 天份` : (ep.remains > 0 ? `預約處方 (剩餘 ${ep.remains} 天)` : `已於 ${formatShortDate(ep.end_date)} 服畢`),
                    ep.diagnosis ? `診斷適應症: ${ep.diagnosis}` : '',
                    ep.nhicode ? `健保代碼: ${ep.nhicode}` : '',
                    ep.contraindicated ? `⚠️ 安全警示: ${ep.contra_reason}` : ''
                ].filter(Boolean).join('\n');

                if (ep.is_active || (barLeft <= currentDateX && currentDateX <= barRight)) {
                    // Active Prescription: Split cleanly at Current Date Line
                    const consumedW = Math.max(currentDateX - barLeft, 0);
                    const remainsW = Math.max(barWidth - consumedW, 0);

                    barsHtml += `
                        <div class="med-bar active" style="left: ${barLeft}px; width: ${barWidth}px; top: ${topOffset}px; height: ${barHeight}px;" title="${escapeHtml(tooltipText)}">
                            ${consumedW > 0 ? `
                                <div class="med-bar-consumed" style="width: ${consumedW}px;">
                                    ${ep.total_days}d ${escapeHtml(ep.method || '')}
                                </div>
                            ` : ''}
                            ${remainsW > 0 ? `
                                <div class="med-bar-remains" style="width: ${remainsW}px;">
                                    <span class="med-remains-pill-text">
                                        <i class="bi bi-hourglass-split"></i> 餘 ${ep.remains}天
                                    </span>
                                </div>
                            ` : ''}
                        </div>
                    `;
                } else if (barRight < currentDateX) {
                    // Past Completed Prescription
                    barsHtml += `
                        <div class="med-bar completed" style="left: ${barLeft}px; width: ${barWidth}px; top: ${topOffset}px; height: ${barHeight}px;" title="${escapeHtml(tooltipText)}">
                            <div class="med-bar-consumed" style="width: 100%;">
                                ${ep.total_days}d ${escapeHtml(ep.method || '')} (服畢)
                            </div>
                        </div>
                    `;
                } else {
                    // Future / Scheduled Prescription
                    barsHtml += `
                        <div class="med-bar future" style="left: ${barLeft}px; width: ${barWidth}px; top: ${topOffset}px; height: ${barHeight}px;" title="${escapeHtml(tooltipText)}">
                            <div class="med-bar-remains" style="width: 100%;">
                                <span class="med-remains-pill-text">預約 ${ep.total_days}日份</span>
                            </div>
                        </div>
                    `;
                }
            });

            // Sticky Y-Axis Cell (Generic name, brand name, dose, frequency, remains badge)
            const brandDisplay = d.brand_name || d.medication || "";
            const genericDisplay = d.generic_name || "Unknown Generic";
            const doseBadge = d.dose ? `<span class="med-dose-badge" title="單次劑量">${escapeHtml(d.dose)}</span>` : '';
            const freqBadge = d.method ? `<span class="med-freq-badge" title="給藥頻率">${escapeHtml(d.method)}</span>` : '';
            const remainsPill = (d.is_active_now && d.current_remains > 0)
                ? `<span class="med-remains-summary-pill" title="本次門診日尚餘藥量"><i class="bi bi-hourglass-split"></i> 餘 ${d.current_remains}天</span>`
                : '';
            const contraBadge = d.contraindicated
                ? `<span class="badge badge-danger" style="font-size:10px;" title="${escapeHtml(d.contra_reason || '用藥安全警示')}"><i class="bi bi-exclamation-triangle-fill"></i> 禁忌</span>`
                : '';

            const epCodes = (d.episodes || []).map(ep => ep.nhicode).filter(Boolean);
            const primaryCode = epCodes[0] || '';
            const photoBtn = `<button type="button" class="med-photo-btn" data-brand="${escapeHtml(d.brand_name || brandDisplay)}" data-code="${escapeHtml(primaryCode)}" data-generic="${escapeHtml(genericDisplay)}" onclick="openDrugPhotoModalFromBtn(this, event)" title="查看藥品外觀照片"><i class="bi bi-card-image"></i></button>`;

            tbodyHtml += `
                <tr>
                    <td class="med-y-cell" style="height: ${rowHeight}px;">
                        <div class="med-generic-title" title="${escapeHtml(genericDisplay)}">
                            <span class="${d.is_active_now ? 'med-active-dot' : 'med-past-dot'}" title="${d.is_active_now ? '目前進行中' : '歷史處方'}"></span>
                            <span class="med-generic-text">${escapeHtml(genericDisplay)}</span>
                        </div>
                        <div class="med-meta-line">
                            <span class="med-brand-name" title="${escapeHtml(d.brand_full || brandDisplay)}">${escapeHtml(brandDisplay)}</span>${photoBtn}
                            ${doseBadge}
                            ${freqBadge}
                            ${remainsPill}
                            ${contraBadge}
                        </div>
                    </td>
                    <td class="med-timeline-track-cell" style="width: ${trackWidth}px; min-width: ${trackWidth}px; height: ${rowHeight}px;">
                        ${gridLinesHtml}
                        <div class="med-current-date-line" style="left: ${currentDateX}px;"></div>
                        ${barsHtml}
                    </td>
                </tr>
            `;
        });
    }

    // 5. Assemble Complete Table HTML
    const tableHtml = `
        <table class="med-timeline-table">
            <thead>
                <tr>
                    <th class="med-y-corner-cell">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span>檢驗項目與用藥品項 / Y-軸</span>
                            <span style="font-size:10px; font-weight:normal; color:var(--text-muted);">時序對照</span>
                        </div>
                    </th>
                    <th class="med-time-header-cell" style="width: ${trackWidth}px; min-width: ${trackWidth}px; height: 42px; position: relative; padding: 0;">
                        <div style="position: relative; width: 100%; height: 100%;">
                            ${monthHeadersHtml}
                            <div class="med-current-date-marker" style="left: ${currentDateX}px;" title="本次門診基準日: ${clinicDateStr}">
                                <i class="bi bi-geo-alt-fill"></i> 本次門診 ${formatShortDate(clinicDateStr)}
                            </div>
                        </div>
                    </th>
                </tr>
            </thead>
            <tbody>
                ${tbodyHtml}
            </tbody>
        </table>
    `;

    container.innerHTML = tableHtml;

    // 6. Synchronize Top Scrollbar and Auto-scroll to the Right Edge
    setTimeout(() => {
        const topDummy = document.getElementById("corrTopScrollDummy");
        const topScrollBox = document.getElementById("corrTopScrollContainer");
        const corrTopTrack = document.getElementById("corrTopScrollTrack");
        const table = container.querySelector(".med-timeline-table");

        if (table && topDummy) {
            const totalW = table.scrollWidth || table.offsetWidth;
            topDummy.style.width = totalW + "px";
            if (topScrollBox) {
                topScrollBox.style.display = totalW > container.clientWidth ? "flex" : "none";
            }
        }

        // Auto-scroll to the right edge so current medications and latest lab results are immediately visible
        container.scrollLeft = container.scrollWidth;
        if (corrTopTrack) {
            corrTopTrack.scrollLeft = corrTopTrack.scrollWidth;
        }
    }, 60);
}

