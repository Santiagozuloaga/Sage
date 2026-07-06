// SAGE OS v4.5 Web Interface JavaScript
// Handles API calls and WebSocket for real-time updates

class SAGEWebInterface {
    constructor() {
        this.ws = null;
        this.reconnectInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadInitialData();
    }

    setupEventListeners() {
        // Command input
        const commandInput = document.getElementById('command-input');
        const executeBtn = document.getElementById('execute-btn');

        executeBtn.addEventListener('click', () => this.executeCommand());
        commandInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.executeCommand();
            }
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.addConsoleLine('WebSocket connected', 'system');
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.addConsoleLine('WebSocket disconnected, reconnecting...', 'warning');
                this.scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.addConsoleLine('WebSocket error', 'error');
            };
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectInterval) {
            clearInterval(this.reconnectInterval);
        }
        this.reconnectInterval = setInterval(() => {
            this.connectWebSocket();
        }, 5000);
    }

    handleWebSocketMessage(data) {
        if (data.type === 'status_update') {
            this.updateStatus(data.data);
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadKernelStatus(),
            this.loadAgents(),
            this.loadDashboard(),
            this.loadEvents(),
            this.loadMemory(),
            this.loadMissions()
        ]);
    }

    async loadKernelStatus() {
        try {
            const response = await fetch('/api/kernel/status');
            const data = await response.json();
            
            if (data.error) {
                console.error(data.error);
                return;
            }

            document.getElementById('session-id').textContent = `Session: ${data.session_id}`;
            document.getElementById('uptime').textContent = `Uptime: ${Math.floor(data.uptime_seconds)}s`;
            document.getElementById('kernel-status').textContent = data.is_running ? 'READY' : 'STOPPED';
            document.getElementById('kernel-status').className = 'status-value ' + (data.is_running ? 'active' : 'error');
            document.getElementById('kernel-state').textContent = data.state;
            document.getElementById('kernel-state').className = 'status-value active';

            // Update component statuses
            document.getElementById('memory-status').textContent = 'CONNECTED';
            document.getElementById('memory-status').className = 'status-value active';
            document.getElementById('eventbus-status').textContent = 'ACTIVE';
            document.getElementById('eventbus-status').className = 'status-value active';
            document.getElementById('dispatcher-status').textContent = 'ACTIVE';
            document.getElementById('dispatcher-status').className = 'status-value active';
            document.getElementById('mission-status').textContent = 'ACTIVE';
            document.getElementById('mission-status').className = 'status-value active';
            document.getElementById('dashboard-status').textContent = 'ACTIVE';
            document.getElementById('dashboard-status').className = 'status-value active';

        } catch (error) {
            console.error('Failed to load kernel status:', error);
        }
    }

    async loadAgents() {
        try {
            const response = await fetch('/api/agents/list');
            const data = await response.json();
            
            if (data.error) {
                document.getElementById('agents-list').innerHTML = `<div class="loading">${data.error}</div>`;
                return;
            }

            const agentsList = document.getElementById('agents-list');
            agentsList.innerHTML = data.agents.map(agent => `
                <div class="agent-item ${agent.enabled ? 'enabled' : 'disabled'}">
                    <div>
                        <div class="agent-name">${agent.name}</div>
                        <div class="agent-type">${agent.agent_type}</div>
                    </div>
                    <div class="agent-status ${agent.enabled ? '' : 'offline'}"></div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Failed to load agents:', error);
            document.getElementById('agents-list').innerHTML = '<div class="loading">Failed to load agents</div>';
        }
    }

    async loadDashboard() {
        try {
            const response = await fetch('/api/dashboard/status');
            const data = await response.json();
            
            if (data.error) {
                console.error(data.error);
                return;
            }

            document.getElementById('metric-cpu').textContent = '--%';
            document.getElementById('metric-memory').textContent = `${data.memory_usage_mb.toFixed(1)} MB`;
            document.getElementById('metric-tasks').textContent = data.active_tasks;
            document.getElementById('metric-errors').textContent = data.error_count;

        } catch (error) {
            console.error('Failed to load dashboard:', error);
        }
    }

    async loadEvents() {
        try {
            const response = await fetch('/api/events/history?limit=20');
            const data = await response.json();
            
            if (data.error) {
                document.getElementById('events-log').innerHTML = `<div class="loading">${data.error}</div>`;
                return;
            }

            const eventsLog = document.getElementById('events-log');
            if (data.events.length === 0) {
                eventsLog.innerHTML = '<div class="loading">No events</div>';
                return;
            }

            eventsLog.innerHTML = data.events.map(event => `
                <div class="event-item">
                    <span class="event-type">${event.event_type}</span>
                    <span class="event-time">${new Date(event.timestamp).toLocaleTimeString()}</span>
                </div>
            `).join('');

        } catch (error) {
            console.error('Failed to load events:', error);
            document.getElementById('events-log').innerHTML = '<div class="loading">Failed to load events</div>';
        }
    }

    async loadMemory() {
        try {
            const response = await fetch('/api/memory/records?limit=10');
            const data = await response.json();
            
            if (data.error) {
                document.getElementById('memory-list').innerHTML = `<div class="loading">${data.error}</div>`;
                return;
            }

            const memoryList = document.getElementById('memory-list');
            if (data.records.length === 0) {
                memoryList.innerHTML = '<div class="loading">No memory records</div>';
                return;
            }

            memoryList.innerHTML = data.records.map(record => `
                <div class="memory-item">
                    <div class="memory-title">${record.title}</div>
                    <div class="memory-type">${record.memory_type}</div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Failed to load memory:', error);
            document.getElementById('memory-list').innerHTML = '<div class="loading">Failed to load memory</div>';
        }
    }

    async loadMissions() {
        try {
            const response = await fetch('/api/mission/active');
            const data = await response.json();
            
            if (data.error) {
                document.getElementById('mission-list').innerHTML = `<div class="loading">${data.error}</div>`;
                return;
            }

            const missionList = document.getElementById('mission-list');
            if (data.missions.length === 0) {
                missionList.innerHTML = '<div class="loading">No active missions</div>';
                return;
            }

            missionList.innerHTML = data.missions.map(mission => `
                <div class="mission-item">
                    <div class="mission-objective">${mission.objective}</div>
                    <div class="mission-status">${mission.status}</div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Failed to load missions:', error);
            document.getElementById('mission-list').innerHTML = '<div class="loading">Failed to load missions</div>';
        }
    }

    async executeCommand() {
        const input = document.getElementById('command-input');
        const command = input.value.trim();
        
        if (!command) {
            return;
        }

        this.addConsoleLine(`> ${command}`, 'user');
        input.value = '';

        try {
            const response = await fetch('/api/command/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ command })
            });

            const data = await response.json();

            if (data.success) {
                this.addConsoleLine(data.result, 'success');
            } else {
                this.addConsoleLine(`Error: ${data.error}`, 'error');
            }

            // Refresh data after command
            await this.loadKernelStatus();
            await this.loadDashboard();

        } catch (error) {
            console.error('Failed to execute command:', error);
            this.addConsoleLine(`Failed to execute command: ${error}`, 'error');
        }
    }

    addConsoleLine(message, type = 'system') {
        const consoleOutput = document.getElementById('console-output');
        const line = document.createElement('div');
        line.className = `console-line ${type}`;
        line.textContent = message;
        consoleOutput.appendChild(line);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    updateStatus(data) {
        document.getElementById('kernel-state').textContent = data.state;
        document.getElementById('metric-tasks').textContent = data.command_count;
        document.getElementById('metric-errors').textContent = data.error_count;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new SAGEWebInterface();
});
