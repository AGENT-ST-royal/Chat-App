const textarea = document.getElementById("message-input");
const form = document.getElementById("message-form");
const messages = document.querySelector(".messages");
const footer = document.getElementById("footer");


textarea.addEventListener("input", function(){
    this.style.height= "auto";
    this.style.height = Math.min(this.scrollHeight, 300) + "px";
})

textarea.addEventListener("focus", () => {
    setTimeout(() => {
        textarea.scrollIntoView({
            block: "end",
            behavior: "smooth"
        });
    }, 250);
});

textarea.addEventListener("focus", () => {
    setTimeout(() => {
        messages.scrollTop = messages.scrollHeight;
    }, 300);
});

console.log("JavaScript Loaded")

const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const chatSocket = new WebSocket(
    wsProtocol +
    window.location.host +
    "/ws/chat/" +
    conversationId +
    "/"
);

chatSocket.onopen = function(e) {
    console.log("Connected")
};

chatSocket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    const isMe = data.sender === window.currentUser;
    let html = "";

    
    if (isMe){
        html = `
        <div class="chat">
            <div class="user">
                <p>
                    <strong>You<br></strong>${ data.message}
                    <br>
                    <small>${ data.created_at }</small>
                </p>
            </div>
        </div>`;
    } else {
        html = `
        <div class="chat">
            <div class="other_user">
                <p>
                    <strong>${ data.sender } <br></strong>${ data.message }
                    <br>
                    <small>${ data.created_at }</small>
                </p>
            </div> 
        </div>`;
    }
    messages.insertAdjacentHTML("beforeend", html.trim());
    const lastMessage = messages.lastElementChild;
    
    lastMessage.scrollIntoView({
        behavior: "smooth",
        block: "end"
    })
};

chatSocket.onclose = function(e) {
    console.log("closed")
};

chatSocket.onerror = function(e) {
    console.log("error");
    console.log(e);
};

form.addEventListener("submit", function(e){
    e.preventDefault()

    const message = textarea.value.trim();

    if (message === "") return;
    chatSocket.send(JSON.stringify({
        message: message
    }))
    textarea.value = "";
})



window.addEventListener("load", function(){
    const lastMessage = messages.lastElementChild;
    if (lastMessage) {
        lastMessage.scrollIntoView({
            behavior: "instant",
            block: "end"
        });
    }
})