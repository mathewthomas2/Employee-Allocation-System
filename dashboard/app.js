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

    // 1. Update Stats
    const idle = employees.filter(e => e.status === "Idle").length;
    const occupied = employees.filter(e => e.status === "Occupied").length;
    const out = employees.filter(e => e.status === "Out of Zone").length;

    document.getElementById("count-idle").innerText = idle;
    document.getElementById("count-occupied").innerText = occupied;
    document.getElementById("count-out").innerText = out;

    // 2. Update Employee List
    const empList = document.getElementById("employee-list");
    empList.innerHTML = ""; // Clear existing

    employees.forEach(emp => {
        const div = document.createElement("div");
        div.className = "list-item";
        // Handle "Out of Zone" logic for CSS class
        const statusClass = emp.status === "Out of Zone" ? "Out" : emp.status;
        
        div.innerHTML = `
            <div>
                <span class="status-dot status-${statusClass}"></span>
                <strong>${emp.id}</strong>
            </div>
            <div style="opacity: 0.8; font-size: 0.9em;">
                ${emp.status} <span style="font-size:0.8em; margin-left:10px;">(Seen: ${emp.last_seen})</span>
            </div>
        `;
        empList.appendChild(div);
    });

    // 3. Update Alerts
    const alertList = document.getElementById("alert-list");
    alertList.innerHTML = "";

    if (notifications.length === 0) {
        alertList.innerHTML = '<div class="empty-state">No active alerts</div>';
    } else {
        notifications.forEach(note => {
            const div = document.createElement("div");
            div.className = "list-item alert-item";
            div.innerText = note;
            alertList.appendChild(div);
        });
    }
}

// Poll every 2 seconds
setInterval(fetchStatus, 2000);
fetchStatus(); // Initial call
