// Smart UDP Log Viewer Application

// DOM Elements
const logContainer = document.getElementById('logContainer');
const logList = document.getElementById('logList');
const pauseBtn = document.getElementById('pauseBtn');
const resumeBtn = document.getElementById('resumeBtn');
const clearBtn = document.getElementById('clearBtn');
const downloadBtn = document.getElementById('downloadBtn');
const autoScrollBtn = document.getElementById('autoScrollBtn');
const liveStatus = document.getElementById('liveStatus');
const connectionStatus = document.getElementById('connectionStatus');
const logCount = document.getElementById('logCount');
const searchInput = document.getElementById('searchInput');

// Application State
const MAX_LOGS = 10000;
let logs = [];
let paused = false;
let autoScroll = true;
let reconnectDelay = 1000;

// Initialize application
async function bootstrap() {
    await loadInitialLogs();
    setupControls();
    connectWebSocket();
}

// Get authentication token from URL or localStorage
function getAuthToken() {
    try {
        const params = new URLSearchParams(window.location.search);
        const tokenFromUrl = params.get('token');
        if (tokenFromUrl) {
            localStorage.setItem('smartlog_token', tokenFromUrl);
            return tokenFromUrl;
        }
        return localStorage.getItem('smartlog_token');
    } catch (error) {
        return null;
    }
}

// Load initial logs from server
async function loadInitialLogs() {
    try {
        const response = await fetch('/logs?limit=500');
        if (!response.ok) throw new Error('Failed to fetch logs');
        const data = await response.json();
        logs = (data.logs || []).slice(-MAX_LOGS);
        renderLogs();
    } catch (error) {
        console.error('Error loading logs', error);
        connectionStatus.textContent = 'Failed to load initial logs';
    }
}

// Setup UI controls and event listeners
function setupControls() {
    pauseBtn.addEventListener('click', () => {
        paused = true;
        pauseBtn.disabled = true;
        resumeBtn.disabled = false;
        liveStatus.textContent = 'PAUSED';
        liveStatus.classList.remove('live');
        liveStatus.classList.add('paused');
    });

    resumeBtn.addEventListener('click', () => {
        paused = false;
        pauseBtn.disabled = false;
        resumeBtn.disabled = true;
        liveStatus.textContent = 'LIVE';
        liveStatus.classList.add('live');
        liveStatus.classList.remove('paused');
        renderLogs();
    });

    clearBtn.addEventListener('click', async () => {
        try {
            // Clear server buffer
            const response = await fetch('/logs', { method: 'DELETE' });
            if (!response.ok) {
                console.error('Failed to clear server buffer');
            }
        } catch (error) {
            console.error('Error clearing server buffer', error);
        }
        // Clear local logs
        logs = [];
        renderLogs();
    });

    downloadBtn.addEventListener('click', () => {
        const text = logs.map(entry => `[${entry.timestamp}] ${entry.message}`).join('\n');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const now = new Date().toISOString().replace(/[:.]/g, '-');
        link.href = url;
        link.download = `udp-log-${now}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });

    autoScrollBtn.addEventListener('click', () => {
        autoScroll = !autoScroll;
        autoScrollBtn.textContent = `👁 Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
    });

    searchInput.addEventListener('input', () => {
        renderLogs();
    });
}

// Connect to WebSocket for real-time log streaming
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const token = getAuthToken();
    const query = token ? `?token=${encodeURIComponent(token)}` : '';
    const url = `${protocol}://${window.location.host}/ws${query}`;
    const socket = new WebSocket(url);

    socket.addEventListener('open', () => {
        connectionStatus.textContent = 'Connected';
        reconnectDelay = 1000;
    });

    socket.addEventListener('message', (event) => {
        const payload = JSON.parse(event.data);
        pushLog(payload);
        if (!paused) {
            appendLog(payload);
        }
        updateLogCount();
    });

    socket.addEventListener('close', (event) => {
        if (event.code === 4401) {
            connectionStatus.textContent = 'Unauthorized – check token';
            return;
        }
        connectionStatus.textContent = 'Disconnected – reconnecting…';
        setTimeout(connectWebSocket, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 10000);
    });

    socket.addEventListener('error', () => {
        connectionStatus.textContent = 'WebSocket error';
        socket.close();
    });
}

// Add log entry to buffer
function pushLog(entry) {
    logs.push(entry);
    if (logs.length > MAX_LOGS) {
        logs.shift();
        if (!paused && !searchInput.value.trim() && logList.firstChild) {
            logList.removeChild(logList.firstChild);
        }
    }
}

// Append single log entry to DOM
function appendLog(entry) {
    const filter = searchInput.value.trim().toLowerCase();
    if (filter && !entry.message.toLowerCase().includes(filter)) {
        return;
    }
    const line = document.createElement('div');
    line.className = 'log-line';
    line.textContent = `[${formatTime(entry.timestamp)}] ${entry.message}`;
    logList.appendChild(line);
    updateScroll();
}

// Re-render all logs (used for filtering and resume)
function renderLogs() {
    logList.innerHTML = '';
    const filter = searchInput.value.trim().toLowerCase();
    const filtered = filter
        ? logs.filter(entry => entry.message.toLowerCase().includes(filter))
        : logs;
    for (const entry of filtered) {
        const line = document.createElement('div');
        line.className = 'log-line';
        line.textContent = `[${formatTime(entry.timestamp)}] ${entry.message}`;
        logList.appendChild(line);
    }
    updateLogCount(filtered.length);
    updateScroll();
}

// Update log count display
function updateLogCount(count) {
    const filter = searchInput.value.trim().toLowerCase();
    let value = count;
    if (value === undefined) {
        if (filter) {
            value = logs.filter(entry => entry.message.toLowerCase().includes(filter)).length;
        } else {
            value = logs.length;
        }
    }
    logCount.textContent = `${value} entr${value === 1 ? 'y' : 'ies'}`;
}

// Auto-scroll to bottom if enabled
function updateScroll() {
    if (autoScroll) {
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

// Format timestamp for display
function formatTime(timestamp) {
    try {
        const date = new Date(timestamp);
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${day}/${month} ${hours}:${minutes}:${seconds}`;
    } catch (e) {
        return timestamp;
    }
}

// Start application
bootstrap();
