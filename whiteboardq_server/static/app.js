(function() {
    'use strict';

    // State
    let ws = null;
    let stationName = '';
    let messages = [];
    let config = {
        yellow_threshold_minutes: 10,
        red_threshold_minutes: 20,
        overdue_threshold_minutes: 30
    };
    let reconnectTimeout = null;
    let ageUpdateInterval = null;

    // DOM elements
    const loginScreen = document.getElementById('login-screen');
    const mainScreen = document.getElementById('main-screen');
    const stationInput = document.getElementById('station-input');
    const connectBtn = document.getElementById('connect-btn');
    const stationLabel = document.getElementById('station-label');
    const connectionStatus = document.getElementById('connection-status');
    const messagesList = document.getElementById('messages-list');
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');

    // Initialize
    function init() {
        connectBtn.addEventListener('click', handleConnect);
        stationInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleConnect();
        });
        messageForm.addEventListener('submit', handleSubmitMessage);

        // Check for saved station name
        const savedStation = localStorage.getItem('whiteboardq_station');
        if (savedStation) {
            stationInput.value = savedStation;
        }
    }

    // Connect handler
    function handleConnect() {
        const station = stationInput.value.trim();
        if (!station) {
            stationInput.focus();
            return;
        }
        stationName = station;
        localStorage.setItem('whiteboardq_station', station);
        showMainScreen();
        connectWebSocket();
    }

    // Show main screen
    function showMainScreen() {
        loginScreen.classList.add('hidden');
        mainScreen.classList.remove('hidden');
        stationLabel.textContent = stationName;
        messageInput.focus();
    }

    // WebSocket connection
    function connectWebSocket() {
        if (ws) {
            ws.close();
        }

        setConnectionStatus('connecting');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws?station=${encodeURIComponent(stationName)}`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            setConnectionStatus('connected');
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = null;
            }
        };

        ws.onclose = () => {
            setConnectionStatus('disconnected');
            scheduleReconnect();
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleServerEvent(data);
        };
    }

    // Reconnect logic
    function scheduleReconnect() {
        if (!reconnectTimeout) {
            reconnectTimeout = setTimeout(() => {
                reconnectTimeout = null;
                connectWebSocket();
            }, 3000);
        }
    }

    // Connection status display
    function setConnectionStatus(status) {
        connectionStatus.className = '';
        switch (status) {
            case 'connected':
                connectionStatus.textContent = 'Connected';
                connectionStatus.classList.add('status-connected');
                break;
            case 'disconnected':
                connectionStatus.textContent = 'Disconnected';
                connectionStatus.classList.add('status-disconnected');
                break;
            case 'connecting':
                connectionStatus.textContent = 'Connecting...';
                connectionStatus.classList.add('status-connecting');
                break;
        }
    }

    // Handle server events
    function handleServerEvent(event) {
        switch (event.type) {
            case 'initial_state':
                messages = event.messages || [];
                config = event.config || config;
                renderMessages();
                startAgeUpdates();
                break;

            case 'message_created':
                messages.push(event.message);
                messages.sort((a, b) => a.position - b.position);
                renderMessages();
                break;

            case 'message_moved':
                // Update positions from server
                const positionMap = {};
                for (const pos of event.all_positions) {
                    positionMap[pos.id] = pos.position;
                }
                for (const msg of messages) {
                    if (positionMap[msg.id] !== undefined) {
                        msg.position = positionMap[msg.id];
                    }
                }
                messages.sort((a, b) => a.position - b.position);
                renderMessages();
                break;

            case 'message_deleted':
                messages = messages.filter(m => m.id !== event.message_id);
                renderMessages();
                break;

            case 'message_restored':
                messages.push(event.message);
                messages.sort((a, b) => a.position - b.position);
                renderMessages();
                break;
        }
    }

    // Render messages
    function renderMessages() {
        if (messages.length === 0) {
            messagesList.innerHTML = '<div class="empty-state"><p>No messages yet. Create one below!</p></div>';
            return;
        }

        messagesList.innerHTML = messages.map(msg => {
            const ageInfo = getMessageAge(msg.created_at);
            const statusClass = getStatusClass(ageInfo.minutes);

            return `
                <div class="message-item ${statusClass}" data-id="${msg.id}">
                    <div class="message-content">
                        <div class="message-text">${escapeHtml(msg.content)}</div>
                        <div class="message-meta">
                            <span class="message-station">${escapeHtml(msg.station_name)}</span>
                            &bull;
                            <span class="message-age" data-created="${msg.created_at}">${ageInfo.text}</span>
                        </div>
                    </div>
                    <div class="message-actions">
                        <button class="btn-top" onclick="moveMessage('${msg.id}', 'top')" title="Move to top">&#8657;</button>
                        <button class="btn-up" onclick="moveMessage('${msg.id}', 'up')" title="Move up">&#8593;</button>
                        <button class="btn-down" onclick="moveMessage('${msg.id}', 'down')" title="Move down">&#8595;</button>
                        <button class="btn-delete" onclick="deleteMessage('${msg.id}')" title="Delete">&#10005;</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Calculate message age
    function getMessageAge(createdAt) {
        const created = new Date(createdAt);
        const now = new Date();
        const diffMs = now - created;
        const minutes = Math.floor(diffMs / 60000);

        let text;
        if (minutes < 1) {
            text = 'just now';
        } else if (minutes === 1) {
            text = '1 min ago';
        } else if (minutes < 60) {
            text = `${minutes} min ago`;
        } else {
            const hours = Math.floor(minutes / 60);
            if (hours === 1) {
                text = '1 hour ago';
            } else {
                text = `${hours} hours ago`;
            }
        }

        return { minutes, text };
    }

    // Get status class based on age
    function getStatusClass(minutes) {
        if (minutes >= config.overdue_threshold_minutes) {
            return 'status-overdue';
        } else if (minutes >= config.red_threshold_minutes) {
            return 'status-red';
        } else if (minutes >= config.yellow_threshold_minutes) {
            return 'status-yellow';
        }
        return '';
    }

    // Update ages periodically
    function startAgeUpdates() {
        if (ageUpdateInterval) {
            clearInterval(ageUpdateInterval);
        }
        ageUpdateInterval = setInterval(() => {
            // Update age text and status classes
            const items = messagesList.querySelectorAll('.message-item');
            items.forEach(item => {
                const ageSpan = item.querySelector('.message-age');
                if (ageSpan) {
                    const created = ageSpan.dataset.created;
                    const ageInfo = getMessageAge(created);
                    ageSpan.textContent = ageInfo.text;

                    // Update status class
                    item.classList.remove('status-yellow', 'status-red', 'status-overdue');
                    const statusClass = getStatusClass(ageInfo.minutes);
                    if (statusClass) {
                        item.classList.add(statusClass);
                    }
                }
            });
        }, 10000); // Update every 10 seconds
    }

    // Send message
    function handleSubmitMessage(e) {
        e.preventDefault();
        const content = messageInput.value.trim();
        if (!content || !ws || ws.readyState !== WebSocket.OPEN) return;

        ws.send(JSON.stringify({
            type: 'create_message',
            content: content
        }));

        messageInput.value = '';
        messageInput.focus();
    }

    // Move message (global function for onclick)
    window.moveMessage = function(messageId, direction) {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;

        ws.send(JSON.stringify({
            type: 'move_message',
            message_id: messageId,
            direction: direction
        }));
    };

    // Delete message (global function for onclick)
    window.deleteMessage = function(messageId) {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;

        ws.send(JSON.stringify({
            type: 'delete_message',
            message_id: messageId
        }));
    };

    // Escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Start app
    init();
})();
