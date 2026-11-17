/**
 * Lab results: list view and flowsheet matrix.
 */
import { state } from "./state.js";
import { escapeHtml, formatShortDate, formatStandardDate } from "./utils.js";

export function renderLabTable(labPanel, tab) {
    if (!labPanel) return;

    const flowsheetWrapper = document.getElementById("labFlowsheetWrapper");
    const listWrapper = document.getElementById("labListWrapper");
    const btnFlowsheet = document.getElementById("btnLabFlowsheet");
    const btnList = document.getElementById("btnLabList");

    // Manage container view toggles
    if (state.currentLabView === "flowsheet") {
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
        renderLabFlowsheet(labPanel.flowsheet, tab, state.flowsheetFilterText);
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
export function renderLabFlowsheet(flowsheet, activeTab, filterText) {
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
            const rawRefNote = it.raw_ref && it.raw_ref !== it.ref ? ` | 原始標示: ${it.raw_ref}` : '';
            trItem.title = `${it.item}${unitRefText ? ` (${unitRefText})` : ''}${rawRefNote}`;
            tdItem.innerHTML = `
                <div class="flowsheet-item-name">${escapeHtml(it.item)}</div>
                ${unitRefText ? `<div class="flowsheet-item-meta" title="${escapeHtml(trItem.title)}">${escapeHtml(unitRefText)}</div>` : ''}
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
