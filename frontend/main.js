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
const authSubtitle = document.getElementById("auth-subtitle");
const authSubmit = document.getElementById("auth-submit");
const authToggle = document.getElementById("auth-toggle");
const guestButton = document.getElementById("guest-button");
const authError = document.getElementById("auth-error");
const nameField = document.getElementById("name-field");
const nameInput = document.getElementById("name-input");
const emailInput = document.getElementById("email-input");
const passwordInput = document.getElementById("password-input");
const togglePasswordButton = document.getElementById("toggle-password");
const logoutButton = document.getElementById("logout");
const chat = document.getElementById("chat");
const input = document.getElementById("input");
const sendButton = document.getElementById("send");
const connectionIndicator = document.getElementById("connection-indicator");
const sidebar = document.getElementById("conversation-sidebar");
const conversationList = document.getElementById("conversation-list");
const newConversationButton = document.getElementById("new-conversation");
const collapseSidebarButton = document.getElementById("collapse-sidebar");
const suggestedPrompts = document.querySelectorAll(".suggested-prompt");

let socket;
let activeToolRun = null;
let transientUserUpdates = [];
let userUpdateRunActive = false;
let isSignup = false;
let isAuthenticated = false;
let isGuest = false;
let conversations = [];
let activeConversationId = null;
let activeConversationHasMessages = false;
let showToolCalls = false;
let isSubmittingMessage = false;
let htmlResponseReceived = false;
let htmlLoadingMessage = null;
let guestThreadId = sessionStorage.getItem("andromeda_guest_thread") || `guest:${crypto.randomUUID()}`;
sessionStorage.setItem("andromeda_guest_thread", guestThreadId);
let reconnectTimer;

function setAuthMode(signup) {
    isSignup = signup;
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
    logoutButton.classList.remove("hidden");
    authScreen.classList.add("hidden");
    sidebar.classList.remove("hidden");
    sidebar.classList.add("collapsed");
    collapseSidebarButton.textContent = "›";
    collapseSidebarButton.setAttribute("aria-label", "Expand history");
    collapseSidebarButton.title = "Expand history";
    sendButton.disabled = true;
    connectSocket();
}

function showAuthScreen() {
    isAuthenticated = false;
    isGuest = false;
    userUpdateRunActive = false;
    window.clearTimeout(reconnectTimer);
    if (socket) socket.close();
    logoutButton.classList.add("hidden");
    sidebar.classList.add("hidden");
    sidebar.classList.add("collapsed");
    authScreen.classList.remove("hidden");
    document.body.classList.remove("has-messages");
    setAuthMode(false);
    emailInput.focus();
}

function showGuestMode() {
    isAuthenticated = false;
    isGuest = true;
    authScreen.classList.add("hidden");
    logoutButton.classList.add("hidden");
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

togglePasswordButton.addEventListener("click", () => {
    const showingPassword = passwordInput.type === "text";
    passwordInput.type = showingPassword ? "password" : "text";
    togglePasswordButton.textContent = showingPassword ? "◉" : "◌";
    togglePasswordButton.setAttribute("aria-label", showingPassword ? "Show password" : "Hide password");
    togglePasswordButton.title = showingPassword ? "Show password" : "Hide password";
});

async function loadConversations() {
    const response = await fetch(`${API_URL}/api/v1/conversations`, { credentials: "include" });
    if (!response.ok) throw new Error("Unable to load conversations");
    conversations = await response.json();
    activeConversationId = null;
    renderConversations();
    await createNewConversation();
}

function renderConversations() {
    conversationList.replaceChildren();
    conversations.forEach((conversation) => {
        const item = document.createElement("div");
        item.className = `conversation-item${conversation.id === activeConversationId ? " active" : ""}`;

        const selectButton = document.createElement("button");
        selectButton.className = "conversation-select";
        selectButton.textContent = conversation.title;
        selectButton.title = conversation.title;
        selectButton.addEventListener("click", () => selectConversation(conversation.id));

        const deleteButton = document.createElement("button");
        deleteButton.className = "delete-conversation";
        deleteButton.type = "button";
        deleteButton.textContent = "×";
        deleteButton.title = `Delete ${conversation.title}`;
        deleteButton.setAttribute("aria-label", `Delete ${conversation.title}`);
        deleteButton.addEventListener("click", (event) => {
            event.stopPropagation();
            deleteConversation(conversation.id);
        });

        item.append(selectButton, deleteButton);
        conversationList.appendChild(item);
    });
}

async function selectConversation(id) {
    await discardEmptyActiveConversation(id);
    activeConversationId = id;
    activeConversationHasMessages = false;
    showToolCalls = false;
    renderConversations();
    if (!isSubmittingMessage) chat.replaceChildren();
    if (!isSubmittingMessage) document.body.classList.remove("has-messages");
    finishToolRun();
    userUpdateRunActive = false;
    if (!isAuthenticated) return;
    const response = await fetch(`${API_URL}/api/v1/conversations/${id}/messages`, { credentials: "include" });
    if (!response.ok) return;
    const messages = await response.json();
    activeConversationHasMessages = messages.length > 0;
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
    await selectConversation(conversation.id);
    return conversation;
}

newConversationButton.addEventListener("click", () => {
    if (sidebar.classList.contains("collapsed")) {
        sidebar.classList.remove("collapsed");
        collapseSidebarButton.textContent = "‹";
        collapseSidebarButton.setAttribute("aria-label", "Collapse history");
        collapseSidebarButton.title = "Collapse history";
        return;
    }
    createNewConversation();
});

async function discardEmptyActiveConversation(nextConversationId = null) {
    if (!isAuthenticated || !activeConversationId || activeConversationHasMessages || activeConversationId === nextConversationId) return;

    const emptyConversationId = activeConversationId;
    const response = await fetch(`${API_URL}/api/v1/conversations/${emptyConversationId}`, {
        method: "DELETE",
        credentials: "include",
    });
    if (!response.ok) return;

    conversations = conversations.filter((conversation) => conversation.id !== emptyConversationId);
    activeConversationId = null;
    activeConversationHasMessages = false;
    renderConversations();
}

async function deleteConversation(id) {
    const conversation = conversations.find((item) => item.id === id);
    if (!conversation || !window.confirm(`Delete “${conversation.title}”?`)) return;

    const response = await fetch(`${API_URL}/api/v1/conversations/${id}`, {
        method: "DELETE",
        credentials: "include",
    });
    if (!response.ok) return;

    conversations = conversations.filter((item) => item.id !== id);
    if (activeConversationId === id) {
        activeConversationId = null;
        activeConversationHasMessages = false;
        chat.replaceChildren();
        document.body.classList.remove("has-messages");
        if (conversations.length) await selectConversation(conversations[0].id);
        else await createNewConversation();
    } else {
        renderConversations();
    }
}

collapseSidebarButton.addEventListener("click", () => {
    const collapsed = sidebar.classList.toggle("collapsed");
    collapseSidebarButton.textContent = collapsed ? "›" : "‹";
    collapseSidebarButton.setAttribute("aria-label", collapsed ? "Expand history" : "Collapse history");
    collapseSidebarButton.title = collapsed ? "Expand history" : "Collapse history";
});

logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    try {
        await discardEmptyActiveConversation();
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
        if (data.type === "user_update") return appendUserUpdate(data);
        if (data.type === "html_response") {
            console.log("[HTML response] received height_guess:", data.height_guess);
            removeHTMLLoadingMessage();
            userUpdateRunActive = false;
            htmlResponseReceived = true;
            addHTMLMessage(data.content, data.height_guess);
            finishToolRun();
            sendButton.disabled = false;
            input.focus();
            return;
        }
        if (data.type === "response") {
            removeHTMLLoadingMessage();
            userUpdateRunActive = false;
            // send_html_response returns a short acknowledgement after it has
            // already delivered the actual HTML over the WebSocket.
            const isHTMLAcknowledgement = htmlResponseReceived &&
                data.content === "HTML response sent to user.";
            if (!isHTMLAcknowledgement) addMessage(data.content, "agent", true);
            htmlResponseReceived = false;
            finishToolRun();
            sendButton.disabled = false;
            input.focus();
        }
        if (data.type === "error") {
            removeHTMLLoadingMessage();
            userUpdateRunActive = false;
            addMessage(data.content, "agent");
            sendButton.disabled = false;
        }
    });
}

function startToolRun() {
    const run = document.createElement("details");
    run.className = "tool-run";
    run.open = true;
    run.innerHTML = `<summary>Agent Actions<span class="tool-count">0</span></summary><div class="tool-log"><div class="tool-empty">Tool activity will appear here while Andromeda works.</div></div>`;
    chat.appendChild(run);
    activeToolRun = run;
}

function appendToolUpdate(update) {
    if (!showToolCalls) return;
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

function appendUserUpdate(update) {
    if (!userUpdateRunActive) return;
    const message = addMessage(update.content || "", "agent");
    message.classList.add("transient-user-update");
    transientUserUpdates.push(message);
}

function clearUserUpdates() {
    transientUserUpdates.forEach((message) => message.remove());
    transientUserUpdates = [];
}

function showHTMLLoadingMessage() {
    removeHTMLLoadingMessage();

    htmlLoadingMessage = document.createElement("div");
    htmlLoadingMessage.className = "message agent html-loading-message";
    htmlLoadingMessage.innerHTML = `
        <span>Generating HTML</span>
        <span class="loading-dots" aria-label="Loading">
            <span></span><span></span><span></span>
        </span>
    `;
    chat.appendChild(htmlLoadingMessage);
    chat.scrollTop = chat.scrollHeight;
}

function removeHTMLLoadingMessage() {
    htmlLoadingMessage?.remove();
    htmlLoadingMessage = null;
}

function addMessage(content, type, markdown = false, animateAfterEmptyState = false) {
    document.body.classList.add("has-messages");
    const message = document.createElement("div");
    message.classList.add("message", type);
    if (animateAfterEmptyState) message.classList.add("user-message-entering");
    if (markdown) message.innerHTML = marked.parse(content);
    else message.textContent = content;
    const timestamp = document.createElement("time");
    timestamp.className = "message-time";
    timestamp.dateTime = new Date().toISOString();
    timestamp.textContent = new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit" }).format(new Date());
    message.appendChild(timestamp);
    chat.appendChild(message);
    chat.scrollTop = chat.scrollHeight;
    return message;
}

function getHTMLFrameHeight(heightGuess) {
    const numericHeight = typeof heightGuess === "number"
        ? heightGuess
        : typeof heightGuess === "string" && heightGuess.trim() !== ""
            ? Number(heightGuess)
            : NaN;

    if (!Number.isFinite(numericHeight)) return 720;
    if (numericHeight < 900) return 600;
    if (numericHeight <= 1800) return 720;
    return 850;
}

function prepareHTMLDocument(htmlContent) {
    if (typeof htmlContent !== "string") return "";

    const scrollbarCSS = `
        <style id="andromeda-embed-scrollbar">
            html {
                scrollbar-width: thin;
                scrollbar-color: #424242 transparent;
            }

            ::-webkit-scrollbar {
                width: 6px;
                height: 6px;
            }

            ::-webkit-scrollbar-thumb {
                border: 1px solid transparent;
                border-radius: 999px;
                background: #424242;
                background-clip: content-box;
            }
        </style>
    `;

    if (/<\/head\s*>/i.test(htmlContent)) {
        return htmlContent.replace(/<\/head\s*>/i, `${scrollbarCSS}</head>`);
    }

    return `${scrollbarCSS}${htmlContent}`;
}


function addHTMLMessage(htmlContent, heightGuess) {
    document.body.classList.add("has-messages");

    const message = document.createElement("div");
    message.classList.add("message", "agent", "html-message");

    const frame = document.createElement("iframe");

    frame.className = "html-response-frame";
    frame.title = "Interactive HTML response";
    frame.setAttribute("scrolling", "auto");

    const iframeHeight = getHTMLFrameHeight(heightGuess);
    frame.height = iframeHeight;
    frame.style.height = `${iframeHeight}px`;
    frame.srcdoc = prepareHTMLDocument(htmlContent);

    const timestamp = document.createElement("time");

    timestamp.className = "message-time";
    timestamp.dateTime = new Date().toISOString();

    timestamp.textContent =
        new Intl.DateTimeFormat([], {
            hour: "numeric",
            minute: "2-digit"
        }).format(new Date());

    message.append(frame, timestamp);

    chat.appendChild(message);
    chat.scrollTop = chat.scrollHeight;

    return message;
}

function isChatNearBottom() {
    const distanceFromBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight;
    return distanceFromBottom < 64;
}

async function sendMessage() {
    const userInput = input.value.trim();
    if (!userInput || !socket || socket.readyState !== WebSocket.OPEN) return;

    // Start the empty-state animation before any conversation setup requests.
    const isFirstMessage = !document.body.classList.contains("has-messages");
    isSubmittingMessage = true;
    document.body.classList.add("has-messages");
    addMessage(userInput, "user", false, isFirstMessage);
    activeConversationHasMessages = true;
    input.value = "";
    sendButton.disabled = true;
    showToolCalls = true;
    htmlResponseReceived = false;
    userUpdateRunActive = true;
    showHTMLLoadingMessage();

    if (isAuthenticated && !activeConversationId) {
        try {
            await createNewConversation();
        } catch (error) {
            isSubmittingMessage = false;
            userUpdateRunActive = false;
            removeHTMLLoadingMessage();
            sendButton.disabled = false;
            addMessage(error.message || "Unable to start a conversation.", "agent");
            return;
        }
    }

    const activeConversation = conversations.find((conversation) => conversation.id === activeConversationId);
    if (isAuthenticated && activeConversation?.title === "New conversation") {
        try {
            const response = await fetch(`${API_URL}/api/v1/conversations/${activeConversationId}`, {
                method: "PATCH",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: userInput }),
            });
            if (response.ok) {
                const renamedConversation = await response.json();
                activeConversation.title = renamedConversation.title;
                renderConversations();
            }
        } catch {
            // The message can still be sent if renaming is temporarily unavailable.
        }
    }

    isSubmittingMessage = false;
    socket.send(JSON.stringify({
        type: "message",
        content: userInput,
        conversation_id: activeConversationId,
        guest_thread_id: guestThreadId,
    }));
}

sendButton.addEventListener("click", sendMessage);
suggestedPrompts.forEach((promptButton) => {
    promptButton.addEventListener("click", () => {
        input.value = promptButton.dataset.prompt || "";
        input.focus();
    });
});

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

setAuthMode(false);
restoreSession();
