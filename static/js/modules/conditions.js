/**
 * Problem list (chronic / acute / surgical) panel.
 */
import { escapeHtml, formatIcd, formatStandardDate } from "./utils.js";

export function renderConditions(conditions) {
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
