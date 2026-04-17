/**
 * app.js — RAG Chatbot frontend logic
 *
 * Talks to the FastAPI backend at API_BASE.
 * Handles: chat, file upload, document list, session management.
 */

// ---------------------------------------------------------------------------
// Config — change API_BASE if your backend runs on a different port/host
// ---------------------------------------------------------------------------
//const API_BASE = "http://localhost:8000/api";
const API_BASE = "https://skills-library.onrender.com/api";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let sessionId      = "";
let isWaiting      = false;
let selectedFile   = null;
let documentsList  = [];

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const messagesEl    = document.getElementById("messages");
const messageInput  = document.getElementById("messageInput");
const sendBtn       = document.getElementById("sendBtn");
const uploadBtn     = document.getElementById("uploadBtn");
const fileInput     = document.getElementById("fileInput");
const uploadArea    = document.getElementById("uploadArea");
const uploadLabel   = document.getElementById("uploadLabel");
const uploadStatus  = document.getElementById("uploadStatus");
const docList       = document.getElementById("docList");
const refreshBtn    = document.getElementById("refreshDocsBtn");
const clearKbBtn    = document.getElementById("clearKbBtn");
const clearChatBtn  = document.getElementById("clearChatBtn");
const statusDot     = document.getElementById("statusDot");
const statusText    = document.getElementById("statusText");
const sidebar       = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebarToggle");
const openSidebar   = document.getElementById("openSidebar");

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  loadDocuments();
  setupInputAutoResize();
  setupDragDrop();
});

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
async function checkHealth() {
  setStatus("loading", "Connecting…");
  try {
    const res  = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    if (data.rag_ready) {
      setStatus("online", "Connected");
    } else {
      setStatus("offline", "API key missing");
    }
  } catch {
    setStatus("offline", "Server offline");
  }
}

function setStatus(state, text) {
  statusDot.className  = `status-dot ${state}`;
  statusText.textContent = text;
}

// ---------------------------------------------------------------------------
// Sidebar toggle
// ---------------------------------------------------------------------------
sidebarToggle.addEventListener("click", () => {
  sidebar.classList.toggle("collapsed");
  sidebar.classList.remove("open");
});

openSidebar.addEventListener("click", () => {
  if (window.innerWidth <= 680) {
    sidebar.classList.add("open");
    sidebar.classList.remove("collapsed");
  } else {
    sidebar.classList.remove("collapsed");
  }
});

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------
sendBtn.addEventListener("click", sendMessage);

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

messageInput.addEventListener("input", () => {
  sendBtn.disabled = !messageInput.value.trim() || isWaiting;
});

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || isWaiting) return;

  // Remove welcome screen on first message
  const welcome = messagesEl.querySelector(".welcome");
  if (welcome) welcome.remove();

  appendMessage("user", text);
  messageInput.value = "";
  messageInput.style.height = "auto";
  sendBtn.disabled = true;
  isWaiting = true;

  const typingId = showTyping();

  try {
    const res  = await fetch(`${API_BASE}/chat`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ message: text, session_id: sessionId }),
    });

    const data = await res.json();
    removeTyping(typingId);

    if (res.ok) {
      sessionId = data.session_id;
      appendMessage("ai", data.answer, data.sources || []);
    } else {
      appendMessage("ai", `Error: ${data.detail || "Unknown error."}`, [], true);
    }
  } catch (err) {
    removeTyping(typingId);
    appendMessage("ai", "Could not reach the server. Make sure the backend is running.", [], true);
  } finally {
    isWaiting = false;
    sendBtn.disabled = !messageInput.value.trim();
  }
}

function appendMessage(role, text, sources = [], isError = false) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  if (role === "ai") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "✦";
    row.appendChild(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (isError) bubble.style.color = "#DD3737";

  bubble.innerHTML = renderMarkdown(text);

  if (sources.length > 0) {
    const srcDiv = document.createElement("div");
    srcDiv.className = "sources";

    const label = document.createElement("span");
    label.style.cssText = "font-size:11px;color:#475569;width:100%;";
    label.textContent = "Sources:";
    srcDiv.appendChild(label);

    sources.forEach((src) => {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      const page = src.page !== "" ? ` · p.${Number(src.page) + 1}` : "";
      tag.textContent = `📄 ${src.filename}${page}`;
      srcDiv.appendChild(tag);
    });

    bubble.appendChild(srcDiv);
  }

  row.appendChild(bubble);
  messagesEl.appendChild(row);
  scrollBottom();
}

function renderMarkdown(text) {
  // Escape HTML
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks ```...```
  html = html.replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>");
  // Inline code `...`
  html = html.replace(/`([^`]+)`/g, "<code style='background:#f3f4f6;padding:2px 5px;border-radius:4px;font-size:13px;'>$1</code>");
  // Bold **...**
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Italic *...*
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // Line breaks
  html = html.replace(/\n/g, "<br/>");

  return html;
}

// Typing indicator
let typingCounter = 0;
function showTyping() {
  const id  = `typing-${typingCounter++}`;
  const row = document.createElement("div");
  row.className = "message-row ai typing";
  row.id = id;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "✦";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  scrollBottom();
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ---------------------------------------------------------------------------
// Clear conversation
// ---------------------------------------------------------------------------
clearChatBtn.addEventListener("click", async () => {
  if (!sessionId) {
    resetUI();
    return;
  }
  try {
    await fetch(`${API_BASE}/session/clear`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ session_id: sessionId }),
    });
  } catch { /* ignore */ }
  sessionId = "";
  resetUI();
});

function resetUI() {
  messagesEl.innerHTML = `
    <div class="welcome">
      <h2>What would you like to know?</h2>
      <p>Upload advisor documents in the sidebar, then ask questions.<br/>
         Answers are grounded in the uploaded content.</p>
      <div class="welcome-chips">
        <button class="chip" onclick="insertChip('What is this document about?')">What is this document about?</button>
        <button class="chip" onclick="insertChip('Summarise the key points.')">Summarise the key points</button>
        <button class="chip" onclick="insertChip('What are the main conclusions?')">Main conclusions</button>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// File upload
// ---------------------------------------------------------------------------
fileInput.addEventListener("change", () => {
  selectedFile = fileInput.files[0] || null;
  if (selectedFile) {
    uploadLabel.innerHTML = `<span style="font-size:22px">✅</span><span>${selectedFile.name}</span>`;
    uploadBtn.disabled = false;
    uploadStatus.textContent = "";
    uploadStatus.className = "upload-status";
  }
});

uploadBtn.addEventListener("click", uploadFile);

async function uploadFile() {
  if (!selectedFile) return;

  setUploadStatus("Uploading…", "");
  uploadBtn.disabled = true;

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const res  = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
    const data = await res.json();

    if (res.ok) {
      setUploadStatus(`✅ ${data.message}`, "success");
      resetUploadArea();
      await loadDocuments();
    } else {
      setUploadStatus(`❌ ${data.detail || "Upload failed"}`, "error");
      uploadBtn.disabled = false;
    }
  } catch {
    setUploadStatus("❌ Could not reach server.", "error");
    uploadBtn.disabled = false;
  }
}

function setUploadStatus(msg, cls) {
  uploadStatus.textContent = msg;
  uploadStatus.className = `upload-status ${cls}`;
}

function resetUploadArea() {
  selectedFile = null;
  fileInput.value = "";
  uploadLabel.innerHTML = 'Drop PDF or TXT here<br/><small>or click to browse</small>';
  uploadBtn.disabled = true;
}

// ---------------------------------------------------------------------------
// Drag & drop
// ---------------------------------------------------------------------------
function setupDragDrop() {
  uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
  });
  uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("dragover"));
  uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) {
      fileInput.files = e.dataTransfer.files;
      fileInput.dispatchEvent(new Event("change"));
    }
  });
}

// ---------------------------------------------------------------------------
// Document list
// ---------------------------------------------------------------------------
refreshBtn.addEventListener("click", loadDocuments);

async function loadDocuments() {
  try {
    const res  = await fetch(`${API_BASE}/documents`);
    const data = await res.json();
    documentsList = data.documents || [];
    renderDocList();
  } catch {
    // silently ignore — server may not be up yet
  }
}

function renderDocList() {
  if (documentsList.length === 0) {
    docList.innerHTML = '<li class="doc-empty">No documents uploaded yet.</li>';
    return;
  }
  docList.innerHTML = "";
  documentsList.forEach((doc) => {
    const li = document.createElement("li");
    li.className = "doc-item";
    li.innerHTML = `
      <span class="doc-item-icon">📄</span>
      <span class="doc-item-name" title="${doc.filename}">${doc.filename}</span>
      <button class="doc-delete" title="Delete document" onclick="deleteDocument('${doc.doc_id}')">🗑</button>
    `;
    docList.appendChild(li);
  });
}

async function deleteDocument(docId) {
  if (!confirm("Remove this document from the knowledge base?")) return;
  try {
    const res = await fetch(`${API_BASE}/documents/${docId}`, { method: "DELETE" });
    if (res.ok) await loadDocuments();
  } catch {
    alert("Failed to delete document.");
  }
}

// Clear entire knowledge base
clearKbBtn.addEventListener("click", async () => {
  if (!confirm("Remove ALL documents from the knowledge base? This cannot be undone.")) return;

  clearKbBtn.disabled = true;
  clearKbBtn.textContent = "Clearing…";

  try {
    const res  = await fetch(`${API_BASE}/documents`, { method: "DELETE" });
    const data = await res.json();
    if (res.ok) {
      await loadDocuments();
      setUploadStatus(`✅ ${data.message}`, "success");
    } else {
      alert(data.detail || "Failed to clear knowledge base.");
    }
  } catch {
    alert("Could not reach server.");
  } finally {
    clearKbBtn.disabled = false;
    clearKbBtn.innerHTML = "&#x1F5D1; Clear Knowledge Base";
  }
});

// ---------------------------------------------------------------------------
// Input auto-resize
// ---------------------------------------------------------------------------
function setupInputAutoResize() {
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + "px";
  });
}

// ---------------------------------------------------------------------------
// Chip shortcut
// ---------------------------------------------------------------------------
function insertChip(text) {
  messageInput.value = text;
  messageInput.dispatchEvent(new Event("input"));
  messageInput.focus();
}
