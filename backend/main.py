from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random

app = FastAPI()

# Enable CORS for Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class Employee(BaseModel):
    id: str  # e.g., "EMP001"
    status: str  # "Idle", "Occupied", "Out of Zone"
    last_seen: str # timestamp string

class Customer(BaseModel):
    id: int
    status: str # "Shopping", "Needs Help"
    location: Optional[str] = None # Description of location

class SystemState(BaseModel):
    employees: List[Employee]
    customers: List[Customer]
    pending_notifications: List[str] # List of messages

# --- Mock Data Store ---
state = SystemState(
    employees=[
        Employee(id="EMP001", status="Idle", last_seen="10:00:00"),
        Employee(id="EMP002", status="Occupied", last_seen="10:00:05"),
        Employee(id="EMP003", status="Out of Zone", last_seen="09:55:00"),
    ],
    customers=[
        Customer(id=101, status="Shopping", location="Aisle 1"),
        Customer(id=102, status="Needs Help", location="Checkout"),
    ],
    pending_notifications=["Customer 102 needs help!"]
)

# --- Routes ---
@app.get("/")
def read_root():
    return {"message": "Employee Monitoring System API is running"}

@app.get("/status", response_model=SystemState)
def get_status():
    """Returns the current simulated state of the supermarket."""
    return state

@app.post("/update_mock")
def update_mock_status():
    """Randomly updates statuses to simulate activity for demo purposes."""
    statuses = ["Idle", "Occupied", "Out of Zone"]
    for emp in state.employees:
        emp.status = random.choice(statuses)
    
    # Randomly add/remove notifications
    if random.random() > 0.7:
        state.pending_notifications.append(f"New alert at {random.randint(1,5)} min ago")
    elif len(state.pending_notifications) > 0 and random.random() > 0.5:
        state.pending_notifications.pop(0)

    return {"message": "Mock state updated", "current_state": state}

@app.get("/notifications/{emp_id}")
def get_notifications(emp_id: str):
    """
    Mobile App Poll Endpoint.
    Real logic would check if a specific alert is assigned to this ID.
    """
    # Simple logic: If EMP001 is Idle and there are notifications, send one.
    target_emp = next((e for e in state.employees if e.id == emp_id), None)
    
    if not target_emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    if target_emp.status == "Idle" and state.pending_notifications:
        return {"has_notification": True, "message": state.pending_notifications[0]}
    
    return {"has_notification": False, "message": ""}
