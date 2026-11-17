/**
 * Imaging / pathology report cards and AI deep extraction.
 */
import { state } from "./state.js";
import { escapeHtml, formatStandardDate } from "./utils.js";

export function renderRadiologyReports(reports) {
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
    const topbarReportBadge = document.getElementById("topbarReportBadge");
    const wsReportCount = document.getElementById("wsReportCount");
    const ctMriCountElem = document.getElementById("ctMriCount");
    const pathologyCountElem = document.getElementById("pathologyCount");
    const endoCountElem = document.getElementById("endoCount");
    const xrayCountElem = document.getElementById("xrayCount");

    if (reportCountElem) reportCountElem.textContent = totalCount;
    if (topbarReportBadge) topbarReportBadge.textContent = totalCount;
    if (wsReportCount) wsReportCount.textContent = totalCount;
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
        if (state.currentImagingTab === "all") return true;
        const cat = r.modality_category || "";
        if (state.currentImagingTab === "ct_mri") {
            return r.is_ct || r.is_mri || cat === "ct_mri";
        }
        if (state.currentImagingTab === "pathology") {
            return r.is_pathology || cat === "pathology";
        }
        if (state.currentImagingTab === "endoscopy_pta") {
            return cat === "endoscopy_pta";
        }
        if (state.currentImagingTab === "xray_sono") {
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
            for (const fList of Object.values(rep.findings_by_category || {})) {
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

export function toggleRawReport(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.toggle("show");
    }
}

export async function triggerAiExtract(reportIndex) {
    if (!state.currentPatientData) return;
    const reports = state.currentPatientData.findings.radiology_reports || [];
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
