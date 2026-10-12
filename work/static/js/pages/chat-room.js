const textarea = document.getElementById("message-input");
const form = document.getElementById("message-form");
const messages = document.querySelector(".messages");

textarea.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 300) + "px";
});

textarea.addEventListener("focus", () => {
    setTimeout(() => {
        textarea.scrollIntoView({ block: "end", behavior: "smooth" });
    }, 250);
    setTimeout(() => {
        messages.scrollTop = messages.scrollHeight;
    }, 300);
});

const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const chatSocket = new WebSocket(
    wsProtocol + window.location.host + "/ws/chat/" + conversationId + "/"
);

chatSocket.onopen = function () {
    console.log("Connected");
};

let typingTimer;

textarea.addEventListener("input", function () {
    if (chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({ type: "typing", typing: true }));
    }

    clearTimeout(typingTimer);
    typingTimer = setTimeout(function () {
        if (chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({ type: "typing", typing: false }));
        }
    }, 1000);
});

function receiptLabel(status) {
    if (status === "read" || status === "delivered") return "✓✓";
    return "✓";
}

function updateReceipt(messageId, status) {
    const receipt = document.querySelector(
        `[data-receipt-for="${messageId}"]`
    );
    if (!receipt) return;

    const rank = { sent: 0, delivered: 1, read: 2 };
    if ((rank[receipt.dataset.status] || 0) > (rank[status] || 0)) return;

    receipt.dataset.status = status;
    receipt.textContent = receiptLabel(status);
    receipt.title =
        status === "read" ? "Read" : status === "delivered" ? "Delivered" : "Sent";
}

function sendReceipt(type, messageId, targetConversationId = conversationId) {
    if (chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(
            JSON.stringify({
                type,
                message_id: Number(messageId),
                conversation_id: Number(targetConversationId),
            })
        );
    }
}

chatSocket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    const typingIndicator = document.getElementById("typing-indicator");

    if (data.type === "typing") {
        if (data.sender === window.currentUser) return;
        typingIndicator.classList.toggle("show", !!data.typing);
        return;
    }

    if (data.type === "notification") {
        sendReceipt("delivered", data.message_id, data.conversation_id);
        return;
    }

    if (data.type === "receipt") {
        if (data.reader_id !== window.currentUserId) {
            data.message_ids.forEach((id) => updateReceipt(id, data.status));
        }
        return;
    }

    if (data.type !== "message") return;

    const isMe = Number(data.sender_id) === Number(window.currentUserId);
    const wrapper = document.createElement("div");
    wrapper.className = "chat";

    const bubble = document.createElement("div");
    bubble.className = isMe ? "user" : "other_user";

    const sender = document.createElement("strong");
    sender.textContent = isMe ? "You" : data.sender;

    const body = document.createElement("p");
    body.className = "message";
    body.textContent = data.message;

    const time = document.createElement("small");
    time.className = "message-time";
    time.textContent = data.created_at;

    if (isMe) {
        const receipt = document.createElement("small");
        receipt.className = "message-receipt";
        receipt.dataset.receiptFor = data.message_id;
        receipt.dataset.status = "sent";
        receipt.title = "Sent";
        receipt.textContent = "✓";
        time.append(" ", receipt);
    }

    bubble.append(
        sender,
        body,
        time
    );

    wrapper.appendChild(bubble);
    messages.appendChild(wrapper);
    wrapper.scrollIntoView({ behavior: "smooth", block: "end" });

    if (!isMe) sendReceipt("read", data.message_id);
};

chatSocket.onclose = function () {
    console.log("closed");
};

chatSocket.onerror = function (e) {
    console.log("error");
    console.log(e);
};

form.addEventListener("submit", function (e) {
    e.preventDefault();

    const message = textarea.value.trim();
    if (message === "") return;

    chatSocket.send(JSON.stringify({ message }));
    textarea.value = "";
});

window.addEventListener("load", function () {
    const lastMessage = messages.lastElementChild;
    if (lastMessage) {
        lastMessage.scrollIntoView({ behavior: "instant", block: "end" });
    }
});