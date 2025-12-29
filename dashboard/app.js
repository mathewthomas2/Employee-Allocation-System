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
    const notifications = data.pending_notifications;

    // 1. Update Stats (with simple animation logic could be added here)
    const idle = employees.filter(e => e.status === "Idle").length;
    const occupied = employees.filter(e => e.status === "Occupied").length;
    const out = employees.filter(e => e.status === "Out of Zone").length;

    animateValue("count-idle", parseInt(document.getElementById("count-idle").innerText), idle);
    animateValue("count-occupied", parseInt(document.getElementById("count-occupied").innerText), occupied);
    animateValue("count-out", parseInt(document.getElementById("count-out").innerText), out);

    // 2. Update Employee List
    const empList = document.getElementById("employee-list");
    // Improvement: Instead of clearing innerHTML, we could diff, but for now simple rebuild is fine for small list
    empList.innerHTML = ""; 

    employees.forEach(emp => {
        // Handle "Out of Zone" logic for CSS class
        let statusClass = "Idle";
        if(emp.status === "Occupied") statusClass = "Occupied";
        if(emp.status === "Out of Zone") statusClass = "Out";

        const div = document.createElement("div");
        div.className = "employee-card";
        
        div.innerHTML = `
            <div class="avatar">${emp.id.substring(3)}</div>
            <div class="card-info">
                <h3>${emp.id}</h3>
                <span class="status-badge badge-${statusClass}">${emp.status}</span>
                <span class="last-seen">Last seen: ${emp.last_seen}</span>
            </div>
            <ion-icon name="radio-button-on-outline" style="color: var(--status-${statusClass.toLowerCase()});"></ion-icon>
        `;
        empList.appendChild(div);
    });

    // 3. Update Alerts
    const alertList = document.getElementById("alert-list");
    alertList.innerHTML = "";

    if (notifications.length === 0) {
        alertList.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <ion-icon name="shield-checkmark-outline" style="font-size: 32px; margin-bottom: 10px;"></ion-icon>
                <div>No active alerts. All zones secure.</div>
            </div>`;
    } else {
        notifications.forEach(note => {
            const div = document.createElement("div");
            div.className = "alert-card";
            div.innerHTML = `
                <ion-icon name="warning" style="font-size: 24px; color: #f87171; min-width: 24px;"></ion-icon>
                <div>
                    <strong style="display:block; margin-bottom:4px; color: #fff;">Attention Required</strong>
                    <span style="opacity: 0.9">${note}</span>
                </div>
            `;
            alertList.appendChild(div);
        });
    }
}

// Helper to animate numbers
function animateValue(id, start, end) {
    if (start === end) return;
    const obj = document.getElementById(id);
    let current = start;
    const range = end - start;
    const increment = end > start ? 1 : -1;
    const stepTime = Math.abs(Math.floor(500 / range));
    
    // Safety for infinite loop if stepTime is 0
    if (!stepTime) { 
        obj.innerText = end; 
        return; 
    }

    const timer = setInterval(() => {
        current += increment;
        obj.innerText = current;
        if (current === end) {
            clearInterval(timer);
        }
    }, Math.max(stepTime, 50)); // Min 50ms to manage perf
}

// Poll every 5 seconds
setInterval(fetchStatus, 5000);
fetchStatus(); // Initial call
