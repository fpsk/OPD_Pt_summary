/**
 * Lab & drug-effect correlation plot and its selectors.
 */
import { state } from "./state.js";
import { escapeHtml, formatShortDate, parseRefRange, parseStandardDate } from "./utils.js";

/**
 * Populate variable selector checkboxes for laboratory data and medications
 */
export function initCorrelationSelectors() {
    if (!state.currentPatientData) return;
    const labContainer = document.getElementById("corrLabListContainer");
    const medContainer = document.getElementById("corrMedListContainer");
    if (!labContainer || !medContainer) return;

    labContainer.innerHTML = "";
    medContainer.innerHTML = "";

    // 1. Gather all lab items with actual numeric results
    const categories = state.currentPatientData.findings?.lab_panel?.flowsheet?.categories || [];
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
            <input type="checkbox" class="corr-lab-cb" value="${escapeHtml(it.item)}" ${state.selectedCorrLabs.has(it.item) ? 'checked' : ''}>
            <span class="corr-var-name">${escapeHtml(it.item)}</span>
            <span class="badge badge-meta">${escapeHtml(it.unit || '')}</span>
            <span class="corr-data-count text-muted">(${it.count}筆)</span>
        `;
        const cb = lbl.querySelector("input");
        cb.addEventListener("change", (e) => {
            if (e.target.checked) state.selectedCorrLabs.add(it.item);
            else state.selectedCorrLabs.delete(it.item);
            updateSelectedBadges();
        });
        labContainer.appendChild(lbl);
    });

    // 2. Gather all medication items
    const drugs = state.currentPatientData.medications?.timeline?.drugs || [];
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
            <input type="checkbox" class="corr-med-cb" value="${escapeHtml(drugKey)}" ${state.selectedCorrMeds.has(drugKey) ? 'checked' : ''}>
            <span class="corr-var-name">${escapeHtml(d.brand_name)}</span>
            <span class="text-muted small">(${escapeHtml(d.generic_name)})</span>
            ${d.dose ? `<span class="med-dose-badge">${escapeHtml(d.dose)}</span>` : ''}
            ${d.is_active_now ? '<span class="badge badge-success badge-xs">進行中</span>' : '<span class="badge badge-outline badge-xs">過往</span>'}
        `;
        const cb = lbl.querySelector("input");
        cb.addEventListener("change", (e) => {
            if (e.target.checked) state.selectedCorrMeds.add(drugKey);
            else state.selectedCorrMeds.delete(drugKey);
            updateSelectedBadges();
        });
        medContainer.appendChild(lbl);
    });

    state.corrSelectorsInitialized = true;

    // Default preset: Glucose & DM Meds if nothing selected yet
    if (state.selectedCorrLabs.size === 0 && state.selectedCorrMeds.size === 0) {
        applyCorrelationPreset("glucose");
    } else {
        updateSelectedBadges();
    }
}

/**
 * Apply clinical correlation presets
 */
export function applyCorrelationPreset(preset) {
    state.selectedCorrLabs.clear();
    state.selectedCorrMeds.clear();

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

    if (!state.currentPatientData) return;
    const allLabItems = [];
    (state.currentPatientData.findings?.lab_panel?.flowsheet?.categories || []).forEach(c => {
        (c.items || []).forEach(it => {
            if (Object.keys(it.values || {}).length > 0) allLabItems.push(it);
        });
    });
    const drugs = state.currentPatientData.medications?.timeline?.drugs || [];

    if (preset === "glucose") {
        // Find Glucose AC / HbA1c
        allLabItems.forEach(it => {
            const name = it.item.toLowerCase();
            if (name.includes("glucose") || name.includes("hba1c") || name.includes("血糖")) {
                state.selectedCorrLabs.add(it.item);
            }
        });
        // Find DM drugs (repaglinide, trajenta, metformin, glimepiride, insulin, janumet, forxiga, jardiance, etc.)
        drugs.forEach(d => {
            const text = `${d.brand_name} ${d.generic_name} ${d.category}`.toLowerCase();
            if (text.includes("repaglinide") || text.includes("trajenta") || text.includes("metformin") ||
                text.includes("linagliptin") || text.includes("dm") || text.includes("血糖") ||
                text.includes("diamicron") || text.includes("forxiga") || text.includes("jardiance")) {
                state.selectedCorrMeds.add(`${d.generic_name}|${d.brand_name}`);
            }
        });
    } else if (preset === "renal") {
        allLabItems.forEach(it => {
            const name = it.item.toLowerCase();
            if (name.includes("creatinine") || name.includes("egfr") || name.includes("bun") || name.includes("肌酸酐")) {
                state.selectedCorrLabs.add(it.item);
            }
        });
        drugs.forEach(d => {
            const text = `${d.brand_name} ${d.generic_name} ${d.category}`.toLowerCase();
            if (text.includes("exnortan") || text.includes("concor") || text.includes("norvasc") ||
                text.includes("isormol") || text.includes("calowlin") || text.includes("valsartan") ||
                text.includes("amlodipine") || text.includes("bisoprolol") || text.includes("blood pressure") ||
                text.includes("cardiovascular") || text.includes("降血壓") || text.includes("renal") || text.includes("腎臟")) {
                state.selectedCorrMeds.add(`${d.generic_name}|${d.brand_name}`);
            }
        });
    } else if (preset === "antithrombotic") {
        allLabItems.forEach(it => {
            const name = it.item.toLowerCase();
            if (name.includes("platelet") || name.includes("plt") || name.includes("inr") || name.includes("prothrombin")) {
                state.selectedCorrLabs.add(it.item);
            }
        });
        drugs.forEach(d => {
            const text = `${d.brand_name} ${d.generic_name} ${d.category}`.toLowerCase();
            if (text.includes("plavix") || text.includes("clopidogrel") || text.includes("cofarin") ||
                text.includes("warfarin") || text.includes("aspirin") || text.includes("bokey") ||
                text.includes("antithrombotic") || text.includes("抗凝血")) {
                state.selectedCorrMeds.add(`${d.generic_name}|${d.brand_name}`);
            }
        });
    } else if (preset === "liver") {
        allLabItems.forEach(it => {
            const name = it.item.toLowerCase();
            if (name.includes("ast") || name.includes("alt") || name.includes("got") ||
                name.includes("gpt") || name.includes("bilirubin") || name.includes("albumin")) {
                state.selectedCorrLabs.add(it.item);
            }
        });
        drugs.filter(d => d.is_active_now).slice(0, 4).forEach(d => {
            state.selectedCorrMeds.add(`${d.generic_name}|${d.brand_name}`);
        });
    }

    syncCorrCheckboxes();
    updateSelectedBadges();
    renderCorrelationPlot();
}

export function setAllCorrCheckboxes(type, checked) {
    if (type === "labs") {
        document.querySelectorAll("#corrLabListContainer .corr-lab-cb").forEach(cb => {
            cb.checked = checked;
            if (checked) state.selectedCorrLabs.add(cb.value);
            else state.selectedCorrLabs.delete(cb.value);
        });
    } else {
        document.querySelectorAll("#corrMedListContainer .corr-med-cb").forEach(cb => {
            cb.checked = checked;
            if (checked) state.selectedCorrMeds.add(cb.value);
            else state.selectedCorrMeds.delete(cb.value);
        });
    }
    updateSelectedBadges();
}

export function syncCorrCheckboxes() {
    document.querySelectorAll("#corrLabListContainer .corr-lab-cb").forEach(cb => {
        cb.checked = state.selectedCorrLabs.has(cb.value);
    });
    document.querySelectorAll("#corrMedListContainer .corr-med-cb").forEach(cb => {
        cb.checked = state.selectedCorrMeds.has(cb.value);
    });
}

export function updateSelectedBadges() {
    const lBadge = document.getElementById("selectedLabCountBadge");
    const mBadge = document.getElementById("selectedMedCountBadge");
    if (lBadge) lBadge.textContent = `${state.selectedCorrLabs.size} 項檢驗`;
    if (mBadge) mBadge.textContent = `${state.selectedCorrMeds.size} 項用藥`;
}

/**
 * Render Combined Unified Timeline Plot (Lab Trends + Drug Usage)
 */
export function renderCorrelationPlot() {
    const container = document.getElementById("corrTimelineContainer");
    if (!container || !state.currentPatientData) return;

    const allLabItemsMap = {};
    (state.currentPatientData.findings?.lab_panel?.flowsheet?.categories || []).forEach(c => {
        (c.items || []).forEach(it => {
            allLabItemsMap[it.item] = it;
        });
    });

    const chosenLabs = Array.from(state.selectedCorrLabs).map(name => allLabItemsMap[name]).filter(Boolean);
    const drugsList = state.currentPatientData.medications?.timeline?.drugs || [];
    const chosenDrugs = drugsList.filter(d => state.selectedCorrMeds.has(`${d.generic_name}|${d.brand_name}`));

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

    const clinicDateStr = state.currentPatientData.clinic_date || "2026/09/01";
    const clinicDt = parseStandardDate(clinicDateStr) || new Date();
    const clinicTime = clinicDt.getTime();

    // 1. Determine unified timeline bounds across all selected labs and drugs
    let minTime = clinicTime - (90 * 86400000);
    let maxTime = clinicTime + (30 * 86400000);

    chosenLabs.forEach(it => {
        for (const dStr of Object.keys(it.values || {})) {
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
