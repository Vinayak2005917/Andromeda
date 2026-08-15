
const dev = "local";

let API_URL;
let WS_URL;

if (dev === "local") {
    API_URL = "http://127.0.0.1:8000";
    WS_URL = "ws://127.0.0.1:8000/ws";
}
else if(dev === "render") {
    API_URL = "https://andromeda-3fdr.onrender.com";
    WS_URL = "wss://andromeda-3fdr.onrender.com/ws";
}

const authScreen = document.getElementById("auth-screen");
const authForm = document.getElementById("auth-form");
const authTitle = document.getElementById("auth-title");
const authSubtitle = document.getElementById("auth-subtitle");
const authSubmit = document.getElementById("auth-submit");
const authToggle = document.getElementById("auth-toggle");
const guestButton = document.getElementById("guest-button");
const authError = document.getElementById("auth-error");
const nameField = document.getElementById("name-field");
const nameInput = document.getElementById("name-input");
const emailInput = document.getElementById("email-input");
const passwordInput = document.getElementById("password-input");
const userProfile = document.getElementById("user-profile");
const userName = document.getElementById("user-name");
const userEmail = document.getElementById("user-email");
const logoutButton = document.getElementById("logout");
const chat = document.getElementById("chat");
const input = document.getElementById("input");
const sendButton = document.getElementById("send");
const connectionIndicator = document.getElementById("connection-indicator");
const sidebar = document.getElementById("conversation-sidebar");
const conversationList = document.getElementById("conversation-list");
const newConversationButton = document.getElementById("new-conversation");

let socket;
let activeToolRun = null;
let isSignup = false;
let isAuthenticated = false;
let isGuest = false;
let conversations = [];
let activeConversationId = null;
let guestThreadId = sessionStorage.getItem("andromeda_guest_thread") || `guest:${crypto.randomUUID()}`;
sessionStorage.setItem("andromeda_guest_thread", guestThreadId);
let reconnectTimer;

function setAuthMode(signup) {
    isSignup = signup;
    authTitle.textContent = signup ? "Create your account" : "Welcome to Andromeda";
    authSubtitle.textContent = signup ? "Get started with Andromeda." : "Sign in to continue.";
    authSubmit.textContent = signup ? "Create account" : "Sign in";
    authToggle.textContent = signup ? "Already have an account? Sign in" : "Create an account";
    nameField.classList.toggle("hidden", !signup);
    nameInput.required = signup;
    passwordInput.autocomplete = signup ? "new-password" : "current-password";
    authError.textContent = "";
}

function showAuthError(message) {
    authError.textContent = message;
}

function showAuthenticatedUser(user) {
    isAuthenticated = true;
    isGuest = false;
    userName.textContent = user.name || "User";
    userEmail.textContent = user.email || "";
    userProfile.classList.remove("hidden");
    authScreen.classList.add("hidden");
    sidebar.classList.remove("hidden");
    sendButton.disabled = true;
    connectSocket();
}

function showAuthScreen() {
    isAuthenticated = false;
    isGuest = false;
    window.clearTimeout(reconnectTimer);
    if (socket) socket.close();
    userProfile.classList.add("hidden");
    sidebar.classList.add("hidden");
    authScreen.classList.remove("hidden");
    document.body.classList.remove("has-messages");
    setAuthMode(false);
    emailInput.focus();
}

function showGuestMode() {
    isAuthenticated = false;
    isGuest = true;
    authScreen.classList.add("hidden");
    userProfile.classList.add("hidden");
    sidebar.classList.add("hidden");
    connectSocket();
}

async function authRequest(path, body) {
    const response = await fetch(`${API_URL}/api/v1/auth/${path}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Authentication failed");
    return data;
}

async function restoreSession() {
    try {
        let response = await fetch(`${API_URL}/api/v1/auth/me`, { credentials: "include" });

        if (response.status === 401) {
            await fetch(`${API_URL}/api/v1/auth/refresh`, {
                method: "POST",
                credentials: "include",
            });
            response = await fetch(`${API_URL}/api/v1/auth/me`, { credentials: "include" });
        }

        if (!response.ok) throw new Error("No active session");
        showAuthenticatedUser(await response.json());
        await loadConversations();
    } catch {
        showAuthScreen();
    }
}

authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    authSubmit.disabled = true;
    showAuthError("");

    try {
        const body = { email: emailInput.value.trim(), password: passwordInput.value };
        if (isSignup) body.name = nameInput.value.trim();
        const data = await authRequest(isSignup ? "signup" : "login", body);
        authForm.reset();
        showAuthenticatedUser(data.user);
        await loadConversations();
    } catch (error) {
        showAuthError(error.message);
    } finally {
        authSubmit.disabled = false;
    }
});

authToggle.addEventListener("click", () => setAuthMode(!isSignup));
guestButton.addEventListener("click", showGuestMode);

async function loadConversations() {
    const response = await fetch(`${API_URL}/api/v1/conversations`, { credentials: "include" });
    if (!response.ok) throw new Error("Unable to load conversations");
    conversations = await response.json();
    renderConversations();
    if (!activeConversationId && conversations.length) selectConversation(conversations[0].id);
    if (!activeConversationId && !conversations.length) await createNewConversation();
}

function renderConversations() {
    conversationList.replaceChildren();
    conversations.forEach((conversation) => {
        const button = document.createElement("button");
        button.className = `conversation-item${conversation.id === activeConversationId ? " active" : ""}`;
        button.textContent = conversation.title;
        button.title = conversation.title;
        button.addEventListener("click", () => selectConversation(conversation.id));
        conversationList.appendChild(button);
    });
}

async function selectConversation(id) {
    activeConversationId = id;
    renderConversations();
    chat.replaceChildren();
    document.body.classList.remove("has-messages");
    finishToolRun();
    if (!isAuthenticated) return;
    const response = await fetch(`${API_URL}/api/v1/conversations/${id}/messages`, { credentials: "include" });
    if (!response.ok) return;
    const messages = await response.json();
    messages.forEach((message) => addMessage(message.content, message.role === "user" ? "user" : "agent", message.role === "assistant"));
}

async function createNewConversation() {
    const response = await fetch(`${API_URL}/api/v1/conversations`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New conversation" }),
    });
    if (!response.ok) throw new Error("Unable to create conversation");
    const conversation = await response.json();
    conversations.unshift(conversation);
    selectConversation(conversation.id);
    return conversation;
}

newConversationButton.addEventListener("click", createNewConversation);

logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    try {
        await fetch(`${API_URL}/api/v1/auth/logout`, {
            method: "POST",
            credentials: "include",
        });
    } finally {
        logoutButton.disabled = false;
        showAuthScreen();
    }
});

function setConnectionState(connected) {
    connectionIndicator.classList.toggle("connected", connected);
    connectionIndicator.setAttribute("aria-label", connected ? "Connected" : "Disconnected");
    connectionIndicator.title = connected ? "Connected" : "Disconnected";
}

function connectSocket() {
    if (socket && socket.readyState <= WebSocket.OPEN) return;
    socket = new WebSocket(WS_URL);

    socket.addEventListener("open", () => {
        setConnectionState(true);
        sendButton.disabled = false;
        input.focus();
    });

    socket.addEventListener("close", (event) => {
        setConnectionState(false);
        sendButton.disabled = true;
        if (event.code === 1008 || (!isAuthenticated && !isGuest)) {
            showAuthScreen();
            return;
        }
        reconnectTimer = window.setTimeout(connectSocket, 1500);
    });

    socket.addEventListener("error", () => setConnectionState(false));

    socket.addEventListener("message", (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "tool_update") return appendToolUpdate(data);
        if (data.type === "response") {
            addMessage(data.content, "agent", true);
            finishToolRun();
            sendButton.disabled = false;
            input.focus();
        }
        if (data.type === "error") {
            addMessage(data.content, "agent");
            sendButton.disabled = false;
        }
    });
}

function startToolRun() {
    const run = document.createElement("details");
    run.className = "tool-run";
    run.open = true;
    run.innerHTML = `<summary>Tool calls <span class="tool-count">0</span></summary><div class="tool-log"><div class="tool-empty">Tool activity will appear here while Andromeda works.</div></div>`;
    chat.appendChild(run);
    activeToolRun = run;
}

function appendToolUpdate(update) {
    if (!activeToolRun) startToolRun();
    const log = activeToolRun.querySelector(".tool-log");
    const count = activeToolRun.querySelector(".tool-count");
    log.querySelector(".tool-empty")?.remove();
    const entry = document.createElement("article");
    entry.className = "tool-entry";
    const meta = document.createElement("div");
    meta.className = "tool-entry-meta";
    meta.textContent = `${update.timestamp || "now"} · ${update.function || update.file || "tool"}`;
    const content = document.createElement("div");
    content.className = "tool-entry-content";
    content.textContent = update.content || "Tool completed.";
    entry.append(meta, content);
    log.appendChild(entry);
    count.textContent = log.children.length;
    log.scrollTop = log.scrollHeight;
}

function finishToolRun() { activeToolRun = null; }

function addMessage(content, type, markdown = false) {
    document.body.classList.add("has-messages");
    const message = document.createElement("div");
    message.classList.add("message", type);
    if (markdown) message.innerHTML = marked.parse(content);
    else message.textContent = content;
    const timestamp = document.createElement("time");
    timestamp.className = "message-time";
    timestamp.dateTime = new Date().toISOString();
    timestamp.textContent = new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit" }).format(new Date());
    message.appendChild(timestamp);
    chat.appendChild(message);
    chat.scrollTop = chat.scrollHeight;
}

async function sendMessage() {
    const userInput = input.value.trim();
    if (!userInput || !socket || socket.readyState !== WebSocket.OPEN) return;

    if (isAuthenticated && !activeConversationId) {
        sendButton.disabled = true;
        try {
            await createNewConversation();
        } catch (error) {
            sendButton.disabled = false;
            addMessage(error.message || "Unable to start a conversation.", "agent");
            return;
        }
    }

    addMessage(userInput, "user");
    input.value = "";
    sendButton.disabled = true;
    socket.send(JSON.stringify({
        type: "message",
        content: userInput,
        conversation_id: activeConversationId,
        guest_thread_id: guestThreadId,
    }));
}

sendButton.addEventListener("click", sendMessage);
input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

setAuthMode(false);
restoreSession();
