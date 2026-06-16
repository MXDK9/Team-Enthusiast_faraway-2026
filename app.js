// Initialize Map centered on India
const map = L.map('map', {
    zoomControl: false,
    attributionControl: false
}).setView([22.5937, 78.9629], 5);

// Add Dark Matter tiles
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
}).addTo(map);

// Storage
const markers = {};
const routeLines = {};
let trackedTrainId = null;

// DOM Elements
const trainList = document.getElementById('train-list');
const agentConsole = document.getElementById('agent-console');
const activeCount = document.getElementById('active-count');
const anomalyCount = document.getElementById('anomaly-count');

// Custom SVG Train Icon
const getTrainIconHTML = (heading, isDelayed) => `
    <div class="train-icon-wrapper ${isDelayed ? 'delayed' : ''}" style="transform: rotate(${heading}deg);">
        <svg class="train-svg" viewBox="0 0 24 24" fill="${isDelayed ? '#ff3366' : '#00f0ff'}">
            <path d="M12 2L4 10h3v12h10V10h3L12 2z"/>
        </svg>
    </div>
`;

// Connect to Backend WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'telemetry') {
        updateMap(data.trains);
        updateUI(data.trains);
        updateConsole(data.agent_logs);
    }
};

function updateMap(trains) {
    trains.forEach(t => {
        // Draw the track route line if not drawn yet
        if (!routeLines[t.route]) {
            routeLines[t.route] = L.polyline(t.waypoints, {
                color: '#00f0ff', 
                weight: 2, 
                opacity: 0.5,
                dashArray: '5, 10'
            }).addTo(map);
        }

        // Draw or update Train Marker
        const isDelayed = t.status !== 'ON_TIME';
        const iconHtml = getTrainIconHTML(t.heading, isDelayed);
        
        if (!markers[t.id]) {
            const icon = L.divIcon({ html: iconHtml, className: '', iconSize: [24, 24], iconAnchor: [12, 12] });
            markers[t.id] = L.marker([t.lat, t.lng], { icon }).addTo(map)
                .bindTooltip(`<div class="font-bold">${t.name} (${t.id})</div><div class="${isDelayed ? 'text-red-400' : 'text-emerald-400'}">Status: ${t.status}</div>`, {className: 'bg-black/90 border border-cyan-500 text-white'});
        } else {
            const icon = L.divIcon({ html: iconHtml, className: '', iconSize: [24, 24], iconAnchor: [12, 12] });
            markers[t.id].setLatLng([t.lat, t.lng]);
            markers[t.id].setIcon(icon);
            markers[t.id].setTooltipContent(`<div class="font-bold">${t.name} (${t.id})</div><div class="${isDelayed ? 'text-red-400' : 'text-emerald-400'}">Status: ${t.status}</div>`);
        }

        // Auto-pan if this train is currently tracked
        if (trackedTrainId === t.id) {
            map.panTo([t.lat, t.lng], { animate: true, duration: 1.0 });
        }
    });
}

function focusTrain(trainId, lat, lng) {
    trackedTrainId = trainId;
    map.flyTo([lat, lng], 8, { animate: true, duration: 1.5 });
    
    // Add visual indicator to the console
    const el = document.createElement('div');
    el.innerHTML = `<span class="text-cyan-400 font-bold">[USER] Target Lock acquired on Train ${trainId}.</span>`;
    agentConsole.appendChild(el);
    agentConsole.scrollTop = agentConsole.scrollHeight;
}

// Attach to window so onclick works
window.focusTrain = focusTrain;

function updateUI(trains) {
    activeCount.innerText = trains.length;
    anomalyCount.innerText = trains.filter(t => t.status !== 'ON_TIME').length;

    let html = '';
    trains.forEach(t => {
        const color = t.status === 'ON_TIME' ? 'text-emerald-400' : 'text-red-400';
        const isTracked = trackedTrainId === t.id ? 'border-cyan-400 bg-cyan-900/40 shadow-[0_0_10px_rgba(0,240,255,0.3)]' : 'border-cyan-500/20 bg-black/40';
        
        html += `
            <div onclick="focusTrain('${t.id}', ${t.lat}, ${t.lng})" class="train-card p-3 rounded-lg border ${isTracked}">
                <div class="flex justify-between font-bold mb-1 items-center">
                    <span class="text-cyan-300 flex items-center gap-2">
                        <i data-lucide="train" class="w-4 h-4"></i> ${t.name}
                    </span>
                    <span class="${color} text-[10px] px-2 py-0.5 rounded bg-black/50">${t.status}</span>
                </div>
                <div class="flex justify-between text-[10px] text-slate-400 font-mono mt-2">
                    <span>ID: ${t.id}</span>
                    <span>Hdg: ${t.heading.toFixed(0)}°</span>
                </div>
            </div>
        `;
    });
    
    // Only update if HTML changed to prevent flickering, or update directly
    if(trainList.innerHTML !== html) {
        trainList.innerHTML = html;
        lucide.createIcons();
    }
}

function updateConsole(logs) {
    logs.forEach(log => {
        const el = document.createElement('div');
        el.innerText = log;
        agentConsole.appendChild(el);
    });
    agentConsole.scrollTop = agentConsole.scrollHeight;
    while (agentConsole.children.length > 25) {
        agentConsole.removeChild(agentConsole.firstChild);
    }
}
