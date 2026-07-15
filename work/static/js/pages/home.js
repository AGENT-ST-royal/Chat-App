console.log("active")

const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const homeSocket = new WebSocket(
    wsProtocol + window.location.host + "/ws/home/"
);

homeSocket.onopen = function(){
    console.log("Home WebSocket connected");
};

homeSocket.onclose = function(){
    console.log("Home WebSocket disconnected");
};

homeSocket.onerror = function(error){
    console.log("Home WebSocket error: ", error);
};

homeSocket.onmessage = function(e){
    const data = JSON.parse(e.data)
    const message = document.getElementById(`last-message-${data.conversation_id}`);
    const time = document.getElementById(`time-${data.conversation_id}`);
    console.log(data);

    function truncateMessage(text, maxLength = 20) {
        if (text.length <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength) + "...";
    }
    
    if (data.type === "presence_update") {
        const status = document.getElementById(`status-${data.user_id}`);
        if (status) {
            if (data.is_online) {
                status.textContent = "🟢 Online";
            } else {
                status.textContent = `⚫ Last seen ${data.last_seen}`;
            }
        }
        return;
    }

    if (message){
        message.innerHTML = `
            <small>${data.sender}: </small>
            ${truncateMessage(data.message)}
        `;
    }

    if (time){
        time.textContent = data.created_at;
    }

    const badge = document.getElementById(`badge-${data.conversation_id}`);

    if (badge){
        let count = parseInt(badge.textContent) || 0;
        count++;
        badge.textContent = count;
        badge.style.display ="flex";
    }
    const conversation = document.getElementById(`conversation-${data.conversation_id}`);

    const list = document.getElementById("conversation-list");
    
    if (conversation && list) {
        list.prepend(conversation)

    }
};

const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results");
const conversationList = document.getElementById("conversation-list");
const searchForm = document.getElementById("search-form");
const searchBack = document.getElementById("search-back");
const searchHistoryKey = "chat_search_history";
let searchTimer = null;

const getSearchHistory = () => {
    try {
        return JSON.parse(localStorage.getItem(searchHistoryKey) || "[]");
    } catch (error) {
        return [];
    }
};

const saveSearchQuery = (query) => {
    if (!query) {
        return;
    }

    const normalized = query.trim();
    const history = getSearchHistory().filter(
        (item) => item.toLowerCase() !== normalized.toLowerCase()
    );
    history.unshift(normalized);
    localStorage.setItem(searchHistoryKey, JSON.stringify(history.slice(0, 6)));
};

const renderSearchHistory = () => {
    const history = getSearchHistory();
    if (!history.length) {
        searchResults.innerHTML = '<p class="history-empty">No recent searches</p>';
        return;
    }

    searchResults.innerHTML = `
        <h3>Search history</h3>
        <div class="search-history">
            ${history
                .map((item) => {
                    const escaped = item.replace(/"/g, '&quot;');
                    return `<button type="button" class="history-item" data-query="${escaped}">
                            <i class="bx bx-history"></i>
                            <span>${item}</span>
                        </button>`;
                })
                .join("")}
        </div>
    `;
};

const updateSearchResults = async (query) => {
    if (!query) {
        searchResults.innerHTML = "";
        return;
    }

    const url = `${window.location.pathname}?search=${encodeURIComponent(query)}`;
    const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!response.ok) {
        return;
    }

    const html = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const newResult = doc.querySelector(".search .result");

    console.log("Response HTML:", html);
    console.log("Found result:", newResult);

    if (newResult) {
        searchResults.innerHTML = newResult.innerHTML;
    } else {
        console.error("Couldn't find .search .result");
    }
};

const setSearchMode = (on) => {
    document.body.classList.toggle("search-active", !!on);
};

if (searchInput) {
    searchInput.addEventListener("focus", () => {
        setSearchMode(true);
        const query = searchInput.value.trim();
        if (query) {
            updateSearchResults(query);
        } else {
            renderSearchHistory();
        }
    });

    searchInput.addEventListener("input", () => {
        setSearchMode(true);
        if (searchTimer) {
            clearTimeout(searchTimer);
        }
        searchTimer = setTimeout(() => {
            const query = searchInput.value.trim();
            if (query) {
                updateSearchResults(query);
            } else {
                renderSearchHistory();
            }
        }, 200);
    });

    // Do not switch back on blur; only back arrow should exit search mode
    if (searchBack) {
        searchBack.addEventListener("click", (e) => {
            e.preventDefault();

            // Clear the search input
            searchInput.value = "";

            // Clear any displayed users/history
            searchResults.innerHTML = "";

            // Exit search mode
            setSearchMode(false);

            // Remove ?search=... from the URL
            window.history.replaceState({}, "", window.location.pathname);

            // Remove focus from the input
            searchInput.blur();
        });
    }
}

if (searchForm) {
    searchForm.addEventListener("submit", (event) => {
        event.preventDefault();

        const query = searchInput.value.trim();

        if (!query) {
            searchResults.innerHTML = "";
            setSearchMode(false);
            return;
        }

        saveSearchQuery(query);
        updateSearchResults(query);
    });
}

searchResults?.addEventListener("click", (event) => {
    const button = event.target.closest(".history-item");
    if (!button) {
        return;
    }

    const query = button.dataset.query;
    if (!query) {
        return;
    }

    searchInput.value = query;
    setSearchMode(true);
    updateSearchResults(query);
});
