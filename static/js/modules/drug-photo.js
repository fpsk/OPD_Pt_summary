/**
 * Floating, draggable drug photo viewer with zoom/pan.
 */
import { escapeHtml } from "./utils.js";

/**
 * Open Drug Photo & Identification Modal
 */
export async function openDrugPhotoModal(brand, code, generic, event) {
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

let zoomListenersAbort = null;

/**
 * Interactive Image Zoom and Pan for Drug Photo Viewer
 */
export function initDrugPhotoZoomViewer() {
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

    // Replace (not accumulate) window listeners from a previously opened photo
    zoomListenersAbort?.abort();
    zoomListenersAbort = new AbortController();
    window.addEventListener("mousemove", onMouseMove, { signal: zoomListenersAbort.signal });
    window.addEventListener("mouseup", onMouseUp, { signal: zoomListenersAbort.signal });

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
export function initDrugModalDraggable() {
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
export function toggleDrugModalExpand() {
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

export function openDrugPhotoModalFromBtn(btn, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    const brand = btn.getAttribute("data-brand") || "";
    const code = btn.getAttribute("data-code") || "";
    const generic = btn.getAttribute("data-generic") || "";
    openDrugPhotoModal(brand, code, generic, event);
}

export function closeDrugPhotoModal() {
    zoomListenersAbort?.abort();
    zoomListenersAbort = null;
    const modal = document.getElementById("drugPhotoModal");
    if (modal) {
        modal.classList.add("d-none");
        modal.style.display = "none";
    }
}
