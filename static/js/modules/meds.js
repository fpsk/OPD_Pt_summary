/**
 * Medication timeline, list view and remaining-days analysis.
 */
import { state } from "./state.js";
import { escapeHtml, formatShortDate, parseStandardDate } from "./utils.js";

export function renderMedications(meds) {
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
    const clinicDt = parseStandardDate(meds.timeline?.clinic_date || "1150721") || new Date();
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
        renderMedicationTimeline(meds.timeline, state.currentMedFilter, state.medSearchQuery);
    }

    // Render Traditional List View
    renderMedicationList(meds, state.currentMedFilter, state.medSearchQuery);
}

/**
 * Render Medication Timeline Matrix:
 * X-axis: Time / Dates (earliest on left, most current on right edge)
 * Red Dotted Line: Current Visit Date (Clinic Date)
 * Green Striped Portion: Drug Remains (殘藥量) past the dotted line
 * Y-axis: Sticky left column with Generic Name, Brand Name, Dose, and Frequency
 */
export function renderMedicationTimeline(timeline, filterMode, searchQuery) {
    const container = document.getElementById("medTimelineContainer");
    if (!container) return;

    if (!timeline || !timeline.drugs || timeline.drugs.length === 0) {
        container.innerHTML = '<div class="empty-state p-4 text-center">尚無用藥時序資料</div>';
        return;
    }

    const clinicDateStr = timeline.clinic_date || "1150721";
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
            const infoBtn = `<button type="button" class="med-info-btn" data-brand="${escapeHtml(d.brand_name || brandDisplay)}" data-code="${escapeHtml(primaryCode)}" data-generic="${escapeHtml(genericDisplay)}" onclick="openDrugSafetyModalFromBtn(this, event)" title="查看藥品臨床安全資訊 (安全劑量、腎功能調整、副作用、禁忌症、懷孕警語)"><i class="bi bi-info-circle"></i></button>`;

            tbodyHtml += `
                <tr>
                    <td class="med-y-cell" style="height: ${rowHeight}px;">
                        <div class="med-generic-title" title="${escapeHtml(genericDisplay)}">
                            <span class="${d.is_active_now ? 'med-active-dot' : 'med-past-dot'}" title="${d.is_active_now ? '目前進行中' : '歷史處方'}"></span>
                            <span class="med-generic-text">${escapeHtml(genericDisplay)}</span>
                        </div>
                        <div class="med-meta-line">
                            <span class="med-brand-name" title="${escapeHtml(d.brand_full || brandDisplay)}">${escapeHtml(brandDisplay)}</span>${photoBtn}${infoBtn}
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
export function renderMedicationList(meds, filterMode, searchQuery) {
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
            const infoBtn = `<button type="button" class="med-info-btn" data-brand="${escapeHtml(brand)}" data-code="${escapeHtml(m.nhicode || '')}" data-generic="${escapeHtml(generic)}" onclick="openDrugSafetyModalFromBtn(this, event)" title="查看藥品臨床安全資訊 (安全劑量、腎功能調整、副作用、禁忌症、懷孕警語)"><i class="bi bi-info-circle"></i></button>`;

            item.innerHTML = `
                <div class="med-header-row">
                    <div class="med-title-block">
                        <div class="med-brand-row">
                            <span class="med-brand-name">${escapeHtml(brand)}</span>${photoBtn}${infoBtn}
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
