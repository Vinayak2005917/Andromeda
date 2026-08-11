        const chat = document.getElementById("chat");
        const input = document.getElementById("input");
        const sendButton = document.getElementById("send");

        function addMessage(content, type, markdown = false) {
            const message = document.createElement("div");
            message.classList.add("message", type);

            if (markdown) {
                message.innerHTML = marked.parse(content);
            } else {
                message.textContent = content;
            }

            chat.appendChild(message);

            // Scroll to bottom
            chat.scrollTop = chat.scrollHeight;
        }

        async function sendMessage() {
            const userInput = input.value.trim();

            if (!userInput) return;

            // Show user message
            addMessage(userInput, "user");

            input.value = "";
            sendButton.disabled = true;

            try {
                const response = await fetch(
                    `http://localhost:8025/ask?user_input=${encodeURIComponent(userInput)}`
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();

                // Render agent response as Markdown
                addMessage(data.response, "agent", true);

            } catch (error) {
                console.error(error);

                addMessage(
                    `**Error:** Could not connect to the agent.`,
                    "agent",
                    true
                );
            }

            sendButton.disabled = false;
            input.focus();
        }

        sendButton.addEventListener("click", sendMessage);

        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                sendMessage();
            }
        });