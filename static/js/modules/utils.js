/**
 * Pure helpers: date parsing/formatting, HTML escaping, ICD formatting.
 */

/**
 * Parse lab reference range string (e.g. "[70][100]", "0.6-1.2", "< 140", "> 60")
 */
export function parseRefRange(refStr) {
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
export function parseStandardDate(str) {
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
export function formatStandardDate(d) {
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
export function formatShortDate(d) {
    if (!d) return "";
    let std = formatStandardDate(d);
    return std.replace(/^20(\d{2})[\/\-]/, '$1/');
}

/**
 * Format any date string into standard 7-digit ROC date (e.g. 2026/07/21 -> 1150721, 1150721 -> 1150721)
 */
export function formatRocDate(d) {
    if (!d) return "1150721";
    let s = String(d).trim();
    if (/^\d{7}$/.test(s)) return s;
    const std = formatStandardDate(s);
    if (/^\d{4}\/\d{2}\/\d{2}$/.test(std)) {
        const parts = std.split("/");
        const rocYear = parseInt(parts[0], 10) - 1911;
        return `${String(rocYear).padStart(3, "0")}${parts[1]}${parts[2]}`;
    }
    return s;
}

export function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

export function formatIcd(code) {
    if (!code) return "";
    let c = String(code).trim().toUpperCase();
    if (/^[A-Z][0-9]{3,}$/.test(c) && !c.includes(".")) {
        return c.substring(0, 3) + "." + c.substring(3);
    }
    return c;
}

export function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
