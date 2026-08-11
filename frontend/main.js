        const chat = document.getElementById("chat");
        const input = document.getElementById("input");
        const sendButton = document.getElementById("send");
        const connectionIndicator = document.getElementById("connection-indicator");

        let socket;
        let activeToolRun = null;

        function setConnectionState(connected) {
            connectionIndicator.classList.toggle("connected", connected);
            connectionIndicator.setAttribute("aria-label", connected ? "Connected" : "Disconnected");
            connectionIndicator.title = connected ? "Connected" : "Disconnected";
        }

        function connectSocket() {
            const host = window.location.hostname || "localhost";
            socket = new WebSocket(`ws://${host}:8025/ws`);

            socket.addEventListener("open", () => {
                setConnectionState(true);
                input.focus();
            });

            socket.addEventListener("close", () => {
                setConnectionState(false);
                sendButton.disabled = true;
                window.setTimeout(connectSocket, 1500);
            });

            socket.addEventListener("error", () => setConnectionState(false));

            socket.addEventListener("message", (event) => {
                const data = JSON.parse(event.data);

                if (data.type === "tool_update") {
                    appendToolUpdate(data);
                    return;
                }

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
            run.innerHTML = `
                <summary>Tool calls <span class="tool-count">0</span></summary>
                <div class="tool-log">
                    <div class="tool-empty">Tool activity will appear here while Andromeda works.</div>
                </div>
            `;
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

        function finishToolRun() {
            if (!activeToolRun) return;
            activeToolRun = null;
        }

        function addMessage(content, type, markdown = false) {
            document.body.classList.add("has-messages");
            const message = document.createElement("div");
            message.classList.add("message", type);

            if (markdown) {
                message.innerHTML = marked.parse(content);
            } else {
                message.textContent = content;
            }

            const timestamp = document.createElement("time");
            timestamp.className = "message-time";
            timestamp.dateTime = new Date().toISOString();
            timestamp.textContent = new Intl.DateTimeFormat([], {
                hour: "numeric",
                minute: "2-digit"
            }).format(new Date());
            message.appendChild(timestamp);

            chat.appendChild(message);

            // Scroll to bottom
            chat.scrollTop = chat.scrollHeight;
        }

        async function sendMessage() {
            const userInput = input.value.trim();

            if (!userInput || !socket || socket.readyState !== WebSocket.OPEN) return;

            // Show user message
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

        connectSocket();
