/**
 * Clinical AI chat dock.
 */
import { state } from "./state.js";
import { removeElement } from "./utils.js";

export function toggleChatDock(expandOnly = false) {
    const dock = document.getElementById("clinicalChatDock");
    const icon = document.getElementById("toggleChatIcon");
    if (!dock) return;

    if (expandOnly) {
        dock.classList.remove("collapsed");
        if (icon) icon.className = "bi bi-chevron-down";
    } else {
        dock.classList.toggle("collapsed");
        const isCollapsed = dock.classList.contains("collapsed");
        if (icon) icon.className = isCollapsed ? "bi bi-chevron-up" : "bi bi-chevron-down";
    }

    if (!dock.classList.contains("collapsed")) {
        const input = document.getElementById("chatInput");
        if (input) setTimeout(() => input.focus(), 150);
        scrollChatToBottom();
    }
}

export async function sendChatMessage() {
    const input = document.getElementById("chatInput");
    if (!input) return;
    const query = input.value.trim();
    if (!query) return;

    if (!state.currentPatientData) {
        alert("請先載入病患資料後再進行提問");
        return;
    }

    // Ensure dock is expanded
    toggleChatDock(true);

    // Append user message
    appendChatMessage("user", query);
    state.chatHistory.push({ role: "user", content: query });
    input.value = "";

    // Show temporary typing indicator
    const typingId = "typing-" + Date.now();
    appendTypingIndicator(typingId);
    scrollChatToBottom();

    const sendBtn = document.getElementById("sendChatBtn");
    if (sendBtn) sendBtn.disabled = true;

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                patient_id: state.currentPatientData.patient_id,
                clinic_date: state.currentPatientData.clinic_date || "2026/09/01",
                message: query,
                history: state.chatHistory.slice(-6)
            })
        });

        removeElement(typingId);
        if (sendBtn) sendBtn.disabled = false;

        const data = await res.json();
        if (data.status === "success" && data.reply) {
            appendChatMessage("assistant", data.reply);
            state.chatHistory.push({ role: "assistant", content: data.reply });
        } else {
            appendChatMessage("assistant", `⚠️ 諮詢助理未能產生回應：${data.message || '未知錯誤'}`);
        }
    } catch (e) {
        removeElement(typingId);
        if (sendBtn) sendBtn.disabled = false;
        appendChatMessage("assistant", `⚠️ 連線錯誤：${e.message || e}`);
    }

    scrollChatToBottom();
}

export function appendChatMessage(role, text) {
    const container = document.getElementById("chatMessagesContainer");
    if (!container) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.innerHTML = role === "user" ? '<i class="bi bi-person-fill"></i>' : '<i class="bi bi-robot"></i>';

    const content = document.createElement("div");
    content.className = "message-content";
    content.innerHTML = formatMessageContent(text);

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(content);
    container.appendChild(msgDiv);
}

export function appendTypingIndicator(id) {
    const container = document.getElementById("chatMessagesContainer");
    if (!container) return;

    const msgDiv = document.createElement("div");
    msgDiv.id = id;
    msgDiv.className = "chat-message assistant-message";
    msgDiv.innerHTML = `
        <div class="message-avatar"><i class="bi bi-robot"></i></div>
        <div class="message-content text-muted" style="font-style:italic;">
            <i class="bi bi-arrow-repeat spin"></i> AI server 正在依據病歷資料深度研析中...
        </div>
    `;
    container.appendChild(msgDiv);
}

export function clearChatHistory() {
    state.chatHistory = [];
    const container = document.getElementById("chatMessagesContainer");
    if (container) {
        container.innerHTML = `
            <div class="chat-message assistant-message">
                <div class="message-avatar"><i class="bi bi-robot"></i></div>
                <div class="message-content">
                    已清除對話紀錄。您可以隨時提問關於目前病患之病情診斷、檢驗數值、影像與處置病灶、或進行中處方與慢箋劑量。
                </div>
            </div>
        `;
    }
}

export function scrollChatToBottom() {
    const container = document.getElementById("chatMessagesContainer");
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

export function formatMessageContent(text) {
    if (!text) return "";
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Bullet points • or -
    const lines = html.split("\n");
    let inList = false;
    let result = [];

    for (let line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("• ") || trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
            if (!inList) {
                result.push("<ul>");
                inList = true;
            }
            result.push(`<li>${trimmed.substring(2)}</li>`);
        } else {
            if (inList) {
                result.push("</ul>");
                inList = false;
            }
            if (trimmed) {
                result.push(`<p>${trimmed}</p>`);
            }
        }
    }
    if (inList) {
        result.push("</ul>");
    }

    return result.join("");
}

/* ==========================================================================
   Laboratory Trends & Drug Effect Timeline Correlation Controller
   ========================================================================== */
