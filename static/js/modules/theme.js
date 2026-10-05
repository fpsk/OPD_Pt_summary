/**
 * Light/dark theme persistence.
 */

export function initTheme() {
    const savedTheme = localStorage.getItem("opd_theme") || "theme-light";
    document.body.className = savedTheme;
    const toggleBtn = document.getElementById("themeToggleBtn");
    if (toggleBtn) {
        toggleBtn.innerHTML = savedTheme === "theme-dark" ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
    }
}

export function toggleTheme() {
    const isDark = document.body.classList.contains("theme-dark");
    const newTheme = isDark ? "theme-light" : "theme-dark";
    document.body.className = newTheme;
    localStorage.setItem("opd_theme", newTheme);
    const toggleBtn = document.getElementById("themeToggleBtn");
    if (toggleBtn) {
        toggleBtn.innerHTML = newTheme === "theme-dark" ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
    }
}
