const API_URL = "http://127.0.0.1:8000";

async function fetchStatus() {
    try {
        const response = await fetch(`${API_URL}/status`);
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error("Error fetching status:", error);
    }
}

function updateUI(data) {
    const employees = data.employees;
    
    // In our python backend, unattended_zones is a dict like {"EMP_01": {"is_unattended": true, "location": "Section A"}}
    // Build a list of active alerts to display
    let activeAlerts = [];
    if (data.unattended_zones) {
        Object.keys(data.unattended_zones).forEach(zoneId => {
            const info = data.unattended_zones[zoneId];
            if ((typeof info === 'object' && info.is_unattended) || info === true) {
                const loc = (typeof info === 'object' && info.location) ? info.location : "Unknown Zone";
                activeAlerts.push(`Unattended Customer detected at ${loc}`);
            }
        });
    }

    // 1. Update Stats
    const idle = employees.filter(e => e.status === "Idle").length;
    const occupied = employees.filter(e => e.status === "Occupied").length;
    const out = employees.filter(e => e.status === "Out of Zone").length;

    animateValue("count-idle", parseInt(document.getElementById("count-idle").innerText) || 0, idle);
    animateValue("count-occupied", parseInt(document.getElementById("count-occupied").innerText) || 0, occupied);
    animateValue("count-out", parseInt(document.getElementById("count-out").innerText) || 0, out);

    // 2. Update Employee List
    const empList = document.getElementById("employee-list");
    empList.innerHTML = ""; 

    employees.forEach((emp, index) => {
        // Handle Map to CSS classes
        let statusClass = "Idle";
        let iconName = "person-outline";
        if(emp.status === "Occupied") {
            statusClass = "Occupied";
            iconName = "people-outline";
        }
        if(emp.status === "Out of Zone") {
            statusClass = "Out";
            iconName = "log-out-outline";
        }

        // Add stagger animation delay
        const delay = (index * 0.1) + 's';

        const div = document.createElement("div");
        div.className = "employee-card";
        div.style.animationDelay = delay;
        // Data attribute for the CSS glow effect
        div.setAttribute('data-status', statusClass);
        
        div.innerHTML = `
            <div class="avatar">
                <ion-icon name="${iconName}"></ion-icon>
            </div>
            <div class="card-info">
                <h3>${emp.id}</h3>
                <span class="status-badge badge-${statusClass}">
                    <div class="status-indicator"></div>
                    ${emp.status}
                </span>
                <span class="last-seen">
                    <ion-icon name="time-outline"></ion-icon>
                    Last seen: ${emp.last_seen}
                </span>
            </div>
        `;
        empList.appendChild(div);
    });

    // 3. Update Alerts
    const alertList = document.getElementById("alert-list");
    
    // Only rebuild if the alert count changed to prevent constant animation flashing
    // For a complex production app we'd use a real ID diff, but this is simple enough for the demo
    if (activeAlerts.length === 0) {
        if (!alertList.querySelector('.empty-state')) {
            alertList.innerHTML = `
                <div class="empty-state">
                    <ion-icon name="shield-checkmark-outline" style="font-size: 48px; margin-bottom: 10px; color: var(--status-idle);"></ion-icon>
                    <div>All zones secure. No active triggers.</div>
                </div>`;
        }
    } else {
        alertList.innerHTML = ""; // Clear empty state
        activeAlerts.forEach((alertMsg, index) => {
            const div = document.createElement("div");
            div.className = "alert-card";
            div.style.animationDelay = (index * 0.1) + 's';
            
            div.innerHTML = `
                <div class="alert-icon-ring">
                    <ion-icon name="warning" style="font-size: 24px; color: #ef4444;"></ion-icon>
                </div>
                <div class="alert-message">
                    <strong>Critical Alert Triggered</strong>
                    <span>${alertMsg}</span>
                </div>
            `;
            alertList.appendChild(div);
        });
    }
}

// Helper to animate numbers smoothly
function animateValue(id, start, end) {
    if (start === end) return;
    const obj = document.getElementById(id);
    let current = start;
    const range = end - start;
    const increment = end > start ? 1 : -1;
    // Faster animation for smaller range
    const stepTime = Math.abs(Math.floor(200 / range));
    
    if (!stepTime || !Number.isFinite(stepTime)) { 
        obj.innerText = end; 
        return; 
    }

    const timer = setInterval(() => {
        current += increment;
        obj.innerText = current;
        if (current === end) {
            clearInterval(timer);
        }
    }, Math.max(stepTime, 20)); 
}

// Decrease polling time to 2 seconds for a presentation-ready "real-time" feel
setInterval(fetchStatus, 2000);
fetchStatus(); // Initial load
