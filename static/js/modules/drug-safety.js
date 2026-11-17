/**
 * Clinical Drug Safety Information Viewer Modal.
 * Shows safety dose range, renal adjustment, side effects, contraindications,
 * pregnancy warnings, and important safety remarks (Black Box Warning, monitoring, DDIs).
 */
import { escapeHtml } from "./utils.js";

/**
 * Open Drug Safety Information Modal
 */
export async function openDrugSafetyModal(brand, code, generic, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    const modal = document.getElementById("drugSafetyModal");
    const dialog = document.getElementById("drugSafetyModalDialog");
    const titleEl = document.getElementById("drugSafetyModalTitle");
    const bodyEl = document.getElementById("drugSafetyModalBody");
    if (!modal || !bodyEl) return;

    modal.classList.remove("d-none");
    modal.style.display = "flex";
    if (titleEl) {
        titleEl.textContent = brand ? `${brand} 臨床用藥安全指引` : "臨床用藥安全與處方指引";
    }

    // Default positioning on first open if user hasn't moved it yet
    if (dialog && !dialog.dataset.userPositioned) {
        const winW = window.innerWidth;
        const winH = window.innerHeight;
        const dialogW = dialog.classList.contains("is-expanded") ? 1040 : 780;
        const initialLeft = Math.max(15, Math.floor((winW - Math.min(dialogW, winW - 30)) / 2));
        const initialTop = Math.max(30, Math.floor((winH - 620) / 2));
        dialog.style.position = "fixed";
        dialog.style.left = `${initialLeft}px`;
        dialog.style.top = `${initialTop}px`;
        dialog.style.margin = "0";
    }

    bodyEl.innerHTML = `
        <div class="loading-spinner" style="text-align:center; padding:36px;">
            <i class="bi bi-arrow-repeat spin" style="font-size:26px; color:#0284c7;"></i>
            <p style="margin-top:12px; font-weight:600; font-size:14px;">正在檢索臨床用藥安全、劑量指引與器官調整資料...</p>
            <p style="font-size:12px; color:var(--text-muted);">${escapeHtml(brand || '')} ${code ? `(${escapeHtml(code)})` : ''} ${generic ? `[${escapeHtml(generic)}]` : ''}</p>
        </div>
    `;

    try {
        const queryParams = new URLSearchParams({
            brand: brand || "",
            code: code || "",
            generic: generic || ""
        });
        const res = await fetch(`/api/drug_safety?${queryParams.toString()}`);
        const data = await res.json();

        if (data.status === "success" && data.found) {
            renderDrugSafetyDetails(data, bodyEl);
        } else {
            bodyEl.innerHTML = `
                <div class="p-4 text-center">
                    <i class="bi bi-shield-slash text-warning" style="font-size:38px;"></i>
                    <h5 class="mt-3">查無特定藥品安全仿單資料</h5>
                    <p class="text-muted small">${escapeHtml(data.message || '資料庫暫無該品項之完整仿單資料，請參閱臨床藥典或台灣 TFDA 藥證指引。')}</p>
                    <div class="mt-3 p-3 bg-light rounded text-start small">
                        <strong>查詢條件：</strong> 健保碼: ${escapeHtml(code || '無')} | 廠牌: ${escapeHtml(brand || '無')} | 學名: ${escapeHtml(generic || '無')}
                    </div>
                </div>
            `;
        }
    } catch (err) {
        console.error("Error fetching drug safety info:", err);
        bodyEl.innerHTML = `
            <div class="p-4 text-center text-danger">
                <i class="bi bi-exclamation-octagon" style="font-size:38px;"></i>
                <h5 class="mt-3">載入藥品安全資料時發生錯誤</h5>
                <p class="text-muted small">${escapeHtml(err.message || '網路連線異常')}</p>
            </div>
        `;
    }
}

function renderDrugSafetyDetails(data, container) {
    const d = data;
    const dose = d.safety_dose_range || {};
    const renal = d.renal_adjustment || {};
    const sideEffects = d.side_effects || {};
    const contra = d.contraindications || [];
    const preg = d.pregnancy_warning || {};
    const remarks = d.safety_remarks || {};

    // 1. Boxed Warning Alert Banner (if present)
    let boxedBanner = "";
    if (remarks.has_boxed_warning && remarks.boxed_warning_text) {
        boxedBanner = `
            <div class="safety-alert-banner alert-boxed-warning">
                <div class="safety-banner-title">
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <strong>黑框警語 (FDA Black Box Warning)</strong>
                </div>
                <div class="safety-banner-content">${escapeHtml(remarks.boxed_warning_text)}</div>
            </div>
        `;
    }

    // 2. High Alert Badge
    const highAlertBadge = d.high_alert
        ? `<span class="badge badge-danger" title="高警訊藥品 (High Alert Medication)"><i class="bi bi-shield-exclamation"></i> 高警訊藥品</span>`
        : "";

    // 3. Drug Class Badges
    const classBadges = (d.drug_classes || []).map(c => `
        <span class="badge badge-outline-secondary" style="font-size:11px;">${escapeHtml(c)}</span>
    `).join("");

    // 4. Renal Brackets Table
    let renalRowsHtml = "";
    if (renal.brackets && renal.brackets.length > 0) {
        renalRowsHtml = renal.brackets.map(b => {
            let badgeClass = "badge-outline-secondary";
            if (b.severity === "severe") badgeClass = "badge-danger";
            else if (b.severity === "moderate") badgeClass = "badge-warning";
            else if (b.severity === "normal") badgeClass = "badge-success";

            return `
                <tr>
                    <td style="white-space:nowrap; width:140px;">
                        <span class="badge ${badgeClass}">${escapeHtml(b.egfr_range)}</span>
                    </td>
                    <td class="small">${escapeHtml(b.recommendation)}</td>
                </tr>
            `;
        }).join("");
    }

    // 5. Common and Severe Side Effects Badges
    const commonBadges = (sideEffects.common || []).map(s => `
        <span class="side-effect-chip chip-common">${escapeHtml(s)}</span>
    `).join("");

    const severeBadges = (sideEffects.severe || []).map(s => `
        <span class="side-effect-chip chip-severe"><i class="bi bi-exclamation-circle-fill"></i> ${escapeHtml(s)}</span>
    `).join("");

    // Side effects by system list
    let systemsHtml = "";
    if (sideEffects.by_system && Object.keys(sideEffects.by_system).length > 0) {
        systemsHtml = Object.entries(sideEffects.by_system).map(([sys, list]) => `
            <div class="system-se-item">
                <span class="system-se-name"><i class="bi bi-diagram-3"></i> ${escapeHtml(sys)}:</span>
                <span class="system-se-terms">${escapeHtml(list.join("、 "))}</span>
            </div>
        `).join("");
    }

    // 6. Contraindications List
    const contraListHtml = contra.map(c => `
        <li class="contra-item">
            <i class="bi bi-x-circle-fill text-danger contra-bullet"></i>
            <span>${escapeHtml(c)}</span>
        </li>
    `).join("");

    // 7. Key Interactions
    let interactionsHtml = "";
    if (remarks.key_interactions && remarks.key_interactions.length > 0) {
        interactionsHtml = remarks.key_interactions.map(ddi => `
            <div class="ddi-card-item">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <strong class="text-dark small"><i class="bi bi-arrow-left-right text-warning"></i> 併用: ${escapeHtml(ddi.drug)}</strong>
                    <span class="badge ${ddi.severity === '嚴重' ? 'badge-danger' : 'badge-warning'}" style="font-size:10px;">${escapeHtml(ddi.severity)}</span>
                </div>
                <div class="small text-muted">${escapeHtml(ddi.effect)}</div>
            </div>
        `).join("");
    }

    // 8. Lab Monitoring
    const monitoringHtml = (remarks.lab_monitoring || []).map(m => {
        let text = "";
        if (typeof m === "string") {
            text = m;
        } else if (typeof m === "object" && m !== null) {
            const testName = m.lab_test || m.test || m.name || "";
            const freq = m.frequency ? ` (${m.frequency})` : "";
            const alert = m.alert_threshold ? ` [警戒: ${m.alert_threshold}]` : "";
            text = `${testName}${freq}${alert}`.trim();
            if (!text && m.action) text = m.action;
        }
        if (!text) return "";
        return `
            <span class="badge badge-light border text-dark me-1 mb-1" style="font-size:11px;">
                <i class="bi bi-activity text-primary"></i> ${escapeHtml(text)}
            </span>
        `;
    }).join("");

    // FDC Badge (highAlertBadge is declared above)
    const fdcBadge = d.is_fdc
        ? `<span class="badge" style="background:#0284c7; color:#fff; font-size:11px;" title="固定劑量複方製劑 (Fixed-Dose Combination)"><i class="bi bi-layers-half"></i> 固定劑量複方 (FDC)</span>`
        : "";

    // FDC Components Table for Card 1
    let fdcComponentsHtml = "";
    if (dose.is_fdc && Array.isArray(dose.components) && dose.components.length > 0) {
        const compRows = dose.components.map(c => `
            <tr>
                <td style="font-weight:700; white-space:nowrap;">
                    ${escapeHtml(c.display_name || c.moiety)}
                    ${c.drug_class ? `<div class="text-muted" style="font-size:10px; font-weight:normal;">${escapeHtml(c.drug_class)}</div>` : ''}
                </td>
                <td class="text-center" style="white-space:nowrap;">
                    <span class="badge badge-light border text-dark fw-bold" style="font-size:11px;">${escapeHtml(c.amount_str || `${c.amount_value || ''} ${c.amount_unit || ''}`.trim() || '依品項規格')}</span>
                </td>
                <td class="small" style="white-space:nowrap;">
                    ${escapeHtml(c.monotherapy_dose || '參見單方指引')}
                </td>
                <td class="text-center" style="white-space:nowrap;">
                    <span class="badge badge-danger" style="font-size:11px;">${escapeHtml(c.max_daily_dose || '臨床指引')}</span>
                </td>
                <td class="small text-secondary" style="font-size:11px; line-height:1.4;">
                    ${c.warning ? `<span class="text-danger fw-semibold"><i class="bi bi-shield-exclamation"></i> ${escapeHtml(c.warning)}</span><br>` : ''}
                    ${c.renal_note ? `<span class="text-muted"><i class="bi bi-droplet"></i> ${escapeHtml(c.renal_note)}</span>` : ''}
                </td>
            </tr>
        `).join("");

        fdcComponentsHtml = `
            <div class="fdc-components-section mt-2">
                <div class="d-flex align-items-center gap-1 mb-1" style="font-size:11px; font-weight:700; color:var(--text-primary);">
                    <i class="bi bi-layers-half text-primary"></i> 複方主成分規格與個別每日安全上限 (Component Limits)：
                </div>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered fdc-comp-table mb-1">
                        <thead>
                            <tr class="table-light text-secondary" style="font-size:10.5px;">
                                <th>主成分 (Moiety)</th>
                                <th class="text-center" style="width:95px;">單錠含量</th>
                                <th style="width:145px;">單方常用劑量</th>
                                <th class="text-center" style="width:115px;">每日安全上限</th>
                                <th>臨床警語與備註</th>
                            </tr>
                        </thead>
                        <tbody>${compRows}</tbody>
                    </table>
                </div>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="drug-safety-container">
            <!-- Header Identity Banner -->
            <div class="drug-safety-header-card">
                <div class="d-flex flex-wrap justify-content-between align-items-start gap-2">
                    <div>
                        <div class="d-flex align-items-center gap-2 flex-wrap">
                            <h4 class="mb-0 text-primary fw-bold">${escapeHtml(d.brand_name_zh || d.drug_name)}</h4>
                            <span class="text-muted fw-semibold" style="font-size:13.5px;">${escapeHtml(d.brand_name_en || '')}</span>
                            ${highAlertBadge}
                            ${fdcBadge}
                            ${remarks.has_boxed_warning ? '<span class="badge badge-danger"><i class="bi bi-exclamation-triangle-fill"></i> 黑框警語</span>' : ''}
                        </div>
                        <div class="text-secondary small mt-1">
                            <span class="fw-semibold text-dark"><i class="bi bi-capsule"></i> 主成分：</span>${escapeHtml(d.generic_name || d.drug_name)}
                            ${d.strength ? `<span class="mx-1">•</span>劑量規格：${escapeHtml(d.strength)}` : ''}
                            ${d.dosage_form ? `<span class="mx-1">•</span>劑型：${escapeHtml(d.dosage_form)}` : ''}
                            ${d.nhi_code ? `<span class="mx-1">•</span>健保代碼：<code class="text-primary">${escapeHtml(d.nhi_code)}</code>` : ''}
                            ${d.atc_code ? `<span class="mx-1">•</span>ATC：<code>${escapeHtml(d.atc_code)}</code>` : ''}
                        </div>
                    </div>
                    <div class="drug-class-badges-group d-flex flex-wrap gap-1 justify-content-end">
                        ${classBadges}
                    </div>
                </div>
            </div>

            ${boxedBanner}

            <!-- 2-Column Clinical Safety Grid -->
            <div class="safety-grid">
                <!-- CARD 1: Safety Dose Range (安全劑量區間) -->
                <div class="safety-card">
                    <div class="safety-card-header bg-card-dose">
                        <i class="bi bi-speedometer2 text-success"></i>
                        <span>1. 安全劑量區間與用法用量 (Dose Range)</span>
                        ${dose.is_fdc ? '<span class="badge ms-auto" style="background:#0284c7; color:#fff; font-size:10px;"><i class="bi bi-layers-half"></i> 複方指引</span>' : ''}
                    </div>
                    <div class="safety-card-body">
                        <div class="dose-stat-row">
                            <div class="dose-stat-item">
                                <span class="dose-stat-label">${dose.is_fdc ? '複方起始 / 常規劑量' : '起始 / 常規劑量'}</span>
                                <span class="dose-stat-val text-success">${escapeHtml(dose.starting_dose || '依處方指示')}</span>
                            </div>
                            <div class="dose-stat-item">
                                <span class="dose-stat-label">${dose.is_fdc ? '複方每日最大安全劑量' : '每日最大安全劑量'}</span>
                                <span class="dose-stat-val text-danger">${escapeHtml(dose.max_daily_dose || '參見臨床指引')}</span>
                            </div>
                        </div>
                        ${fdcComponentsHtml}
                        ${dose.administration_timing ? `
                            <div class="safety-timing-note">
                                <i class="bi bi-clock-history text-primary"></i> <strong>服用時機：</strong> ${escapeHtml(dose.administration_timing)}
                            </div>
                        ` : ''}
                        ${dose.titration ? `
                            <div class="safety-titration-note">
                                <i class="bi bi-arrow-up-right-circle text-success"></i> <strong>劑量調整與維持：</strong> ${escapeHtml(dose.titration)}
                            </div>
                        ` : ''}
                        <div class="safety-narrative-summary">
                            ${escapeHtml(dose.summary || '請依照醫師指示調整。')}
                        </div>
                    </div>
                </div>

                <!-- CARD 2: Renal & Hepatic Adjustment (腎功能與器官調整) -->
                <div class="safety-card">
                    <div class="safety-card-header bg-card-renal">
                        <i class="bi bi-droplet-half text-primary"></i>
                        <span>2. 腎功能劑量調整 (Renal Adjustment)</span>
                    </div>
                    <div class="safety-card-body">
                        ${renal.dialysis_note ? `
                            <div class="dialysis-alert-strip">
                                <i class="bi bi-hospital"></i> <strong>透析 / ESRD 指引：</strong> ${escapeHtml(renal.dialysis_note)}
                            </div>
                        ` : ''}
                        ${renalRowsHtml ? `
                            <div class="table-responsive mt-2">
                                <table class="table table-sm table-bordered renal-table mb-2">
                                    <thead>
                                        <tr class="table-light">
                                            <th>eGFR 區間</th>
                                            <th>劑量建議與處方原則</th>
                                        </tr>
                                    </thead>
                                    <tbody>${renalRowsHtml}</tbody>
                                </table>
                            </div>
                        ` : '<p class="small text-muted mb-2">一般無特殊重度腎功能障礙下無需調整。</p>'}
                        
                        ${renal.hepatic_adjustment ? `
                            <div class="hepatic-note small">
                                <strong><i class="bi bi-shield"></i> 肝功能調整：</strong> ${escapeHtml(renal.hepatic_adjustment)}
                            </div>
                        ` : ''}
                    </div>
                </div>

                <!-- CARD 3: Contraindications (禁忌症) -->
                <div class="safety-card">
                    <div class="safety-card-header bg-card-contra">
                        <i class="bi bi-slash-circle-fill text-danger"></i>
                        <span>3. 禁忌症與嚴格禁用對象 (Contraindications)</span>
                    </div>
                    <div class="safety-card-body">
                        <ul class="contra-list mb-0">
                            ${contraListHtml || '<li class="small text-muted">無特殊絕對禁忌症紀錄</li>'}
                        </ul>
                    </div>
                </div>

                <!-- CARD 4: Pregnancy & Lactation (懷孕與哺乳警語) -->
                <div class="safety-card">
                    <div class="safety-card-header bg-card-preg">
                        <i class="bi bi-heart-pulse-fill text-purple" style="color:#8b5cf6;"></i>
                        <span>4. 懷孕與哺乳安全評估 (Pregnancy & Lactation)</span>
                    </div>
                    <div class="safety-card-body">
                        <div class="d-flex align-items-center gap-2 mb-2">
                            <span class="badge" style="background:#8b5cf6; color:#fff; font-size:11.5px;">${escapeHtml(preg.category || '懷孕風險評估')}</span>
                        </div>
                        <div class="small mb-2" style="line-height:1.5;">
                            <strong><i class="bi bi-gender-female text-danger"></i> 懷孕期安全性：</strong>
                            ${escapeHtml(preg.risk_summary || '懷孕期間用藥應經醫師審慎評估利益與風險。')}
                        </div>
                        <div class="small text-muted" style="line-height:1.45; border-top:1px dashed var(--border-color); padding-top:6px;">
                            <strong><i class="bi bi-cup-hot text-primary"></i> 哺乳期安全性：</strong>
                            ${escapeHtml(preg.lactation || '建議評估暫停哺乳或改用替代藥物。')}
                        </div>
                    </div>
                </div>

                <!-- CARD 5: Adverse Reactions & Side Effects (副作用與不良反應) -->
                <div class="safety-card">
                    <div class="safety-card-header bg-card-se">
                        <i class="bi bi-exclamation-diamond text-warning"></i>
                        <span>5. 副作用與不良反應 (Side Effects)</span>
                    </div>
                    <div class="safety-card-body">
                        ${severeBadges ? `
                            <div class="mb-2">
                                <span class="badge-title text-danger small fw-bold"><i class="bi bi-shield-fill-x"></i> 警示與嚴重不良反應：</span>
                                <div class="chips-container mt-1">${severeBadges}</div>
                            </div>
                        ` : ''}
                        
                        <div class="mb-2">
                            <span class="badge-title text-secondary small fw-bold"><i class="bi bi-info-circle"></i> 常見不良反應：</span>
                            <div class="chips-container mt-1">${commonBadges || '<span class="text-muted small">暫無常見副作用標籤</span>'}</div>
                        </div>

                        ${systemsHtml ? `
                            <div class="systems-se-box mt-2">
                                <div class="fw-semibold small text-dark mb-1">依器官系統反應：</div>
                                ${systemsHtml}
                            </div>
                        ` : ''}
                    </div>
                </div>

                <!-- CARD 6: Safety Remarks & Monitoring (其他重要安全備註) -->
                <div class="safety-card">
                    <div class="safety-card-header bg-card-remarks">
                        <i class="bi bi-shield-check text-info"></i>
                        <span>6. 監測指標與交互作用 (Safety Remarks & Monitoring)</span>
                    </div>
                    <div class="safety-card-body">
                        <div class="mb-2">
                            <div class="fw-semibold small text-dark mb-1"><i class="bi bi-clipboard2-pulse text-primary"></i> 實驗室定期檢驗監測：</div>
                            <div>${monitoringHtml || '<span class="text-muted small">依臨床狀況例行檢驗</span>'}</div>
                        </div>

                        ${interactionsHtml ? `
                            <div class="mt-2">
                                <div class="fw-semibold small text-dark mb-1"><i class="bi bi-arrow-left-right text-warning"></i> 重大藥物交互作用 (DDIs)：</div>
                                <div class="ddi-list-box">${interactionsHtml}</div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Setup draggable header and action buttons for Drug Safety Modal
 */
export function setupDrugSafetyModalEvents() {
    const modal = document.getElementById("drugSafetyModal");
    const dialog = document.getElementById("drugSafetyModalDialog");
    const header = document.getElementById("drugSafetyModalHeader");
    const closeBtn = document.getElementById("closeDrugSafetyModalBtn");
    const closeFooterBtn = document.getElementById("closeDrugSafetyModalFooterBtn");
    const expandBtn = document.getElementById("expandDrugSafetyModalBtn");

    if (!modal || !dialog) return;

    function closeModal() {
        modal.classList.add("d-none");
        modal.style.display = "none";
    }

    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (closeFooterBtn) closeFooterBtn.addEventListener("click", closeModal);

    // Expand/Restore toggle
    if (expandBtn) {
        expandBtn.addEventListener("click", () => {
            dialog.classList.toggle("is-expanded");
            const icon = expandBtn.querySelector("i");
            if (dialog.classList.contains("is-expanded")) {
                expandBtn.title = "還原視窗寬度";
                if (icon) icon.className = "bi bi-fullscreen-exit";
            } else {
                expandBtn.title = "放大視窗寬度";
                if (icon) icon.className = "bi bi-arrows-fullscreen";
            }
        });
    }

    // Draggable dialog header
    if (header) {
        let isDragging = false;
        let startX, startY, initX, initY;

        header.addEventListener("mousedown", (e) => {
            if (e.target.closest("button")) return;
            isDragging = true;
            dialog.dataset.userPositioned = "true";
            startX = e.clientX;
            startY = e.clientY;
            const rect = dialog.getBoundingClientRect();
            initX = rect.left;
            initY = rect.top;
            header.classList.add("is-dragging");
            document.body.style.userSelect = "none";
        });

        window.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            dialog.style.position = "fixed";
            dialog.style.left = `${Math.max(10, Math.min(window.innerWidth - 80, initX + dx))}px`;
            dialog.style.top = `${Math.max(10, Math.min(window.innerHeight - 80, initY + dy))}px`;
            dialog.style.margin = "0";
        });

        window.addEventListener("mouseup", () => {
            if (isDragging) {
                isDragging = false;
                header.classList.remove("is-dragging");
                document.body.style.userSelect = "";
            }
        });
    }

    // Close on Escape key
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.classList.contains("d-none")) {
            closeModal();
        }
    });
}

/**
 * Triggered from inline onclick attribute on medication item buttons
 */
export function openDrugSafetyModalFromBtn(btn, ev) {
    if (ev) {
        ev.stopPropagation();
        ev.preventDefault();
    }
    const brand = btn.getAttribute("data-brand") || btn.dataset?.brand || "";
    const code = btn.getAttribute("data-code") || btn.dataset?.code || "";
    const generic = btn.getAttribute("data-generic") || btn.dataset?.generic || "";
    openDrugSafetyModal(brand, code, generic, ev);
}
