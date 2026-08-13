
const dev = "render";

let API_URL;
let WS_URL;

if(dev === "local") {
    API_URL = "http://localhost:8000";
    WS_URL = "ws://localhost:8000/ws";
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

let socket;
let activeToolRun = null;
let isSignup = false;
let isAuthenticated = false;
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
    userName.textContent = user.name || "User";
    userEmail.textContent = user.email || "";
    userProfile.classList.remove("hidden");
    authScreen.classList.add("hidden");
    sendButton.disabled = true;
    connectSocket();
}

function showAuthScreen() {
    isAuthenticated = false;
    window.clearTimeout(reconnectTimer);
    if (socket) socket.close();
    userProfile.classList.add("hidden");
    authScreen.classList.remove("hidden");
    document.body.classList.remove("has-messages");
    setAuthMode(false);
    emailInput.focus();
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
    } catch (error) {
        showAuthError(error.message);
    } finally {
        authSubmit.disabled = false;
    }
});

authToggle.addEventListener("click", () => setAuthMode(!isSignup));

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
        if (event.code === 1008 || !isAuthenticated) {
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

function sendMessage() {
    const userInput = input.value.trim();
    if (!userInput || !socket || socket.readyState !== WebSocket.OPEN) return;
    addMessage(userInput, "user");
    input.value = "";
    sendButton.disabled = true;
    socket.send(JSON.stringify({ type: "message", content: userInput }));
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
