/**
 * Patient banner and key metric cards.
 */
import { formatStandardDate } from "./utils.js";

export function renderPatientBanner(data) {
    const prof = data.profile || {};
    const rosterSelect = document.getElementById("rosterSelect");
    const selectedOption = rosterSelect ? rosterSelect.options[rosterSelect.selectedIndex] : null;

    let name = prof.name ? prof.name : ("病患 " + data.patient_id);
    let genderAge = (prof.gender || prof.age) ? `${prof.gender || '--'} / ${prof.age || '--'} 歲` : ("身分證號: " + data.patient_id);
    let chartNo = prof.chart_no ? ("病歷號: " + prof.chart_no) : ("門診日: " + formatStandardDate(data.clinic_date));

    if (selectedOption && selectedOption.value === data.patient_id) {
        const match = selectedOption.textContent.match(/^\d+\.\s*(.*?)\s*\((.*?)\)\s*-\s*(.*)$/);
        if (match) {
            if (!prof.name || prof.name.startsWith("門診病患")) {
                name = match[1] || name;
            }
            if (!prof.age || prof.age === "--") {
                genderAge = match[2] || genderAge;
            }
            const effectiveChartNo = (prof.chart_no && prof.chart_no !== "MCP-CLOUD")
                ? prof.chart_no
                : (selectedOption.dataset.chartNo || prof.chart_no || "--");
            chartNo = "病歷號: " + effectiveChartNo;
        }
    }

    const ptNameEl = document.getElementById("ptName");
    const ptGenderAgeEl = document.getElementById("ptGenderAge");
    const ptChartNoEl = document.getElementById("ptChartNo");
    const ptIdNoEl = document.getElementById("ptIdNo");

    if (ptNameEl) ptNameEl.textContent = name;
    if (ptGenderAgeEl) {
        ptGenderAgeEl.textContent = genderAge;
        ptGenderAgeEl.title = prof.birth_date ? `民國出生日期: ${prof.birth_date}` : "";
    }
    if (ptChartNoEl) ptChartNoEl.textContent = chartNo;
    if (ptIdNoEl) ptIdNoEl.textContent = "ID: " + data.patient_id;

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

export function updateMetricCard(elemId, value, unit, isCritical) {
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
