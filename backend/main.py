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
    id: str  # e.g., "EMP_01"
    password: str # [NEW] Password field
    status: str  # "Idle", "Occupied", "Out of Zone"
    last_seen: str # timestamp string

class LoginRequest(BaseModel):
    id: str
    password: str

class Customer(BaseModel):
    id: int
    status: str # "Shopping", "Needs Help"
    location: Optional[str] = None # Description of location

class SystemState(BaseModel):
    employees: List[Employee]
    customers: List[Customer]
    pending_notifications: List[str] = []
    unattended_zones: dict = {} # Track unattended status per camera/zone

class StatusUpdateRequest(BaseModel):
    employee_id: str
    status: str
    unattended_customer: bool = False
    location: Optional[str] = "Unknown"

# --- Mock Data Store ---
# IDs updated to match Video Text (EMP_01)
state = SystemState(
    employees=[
        Employee(id="EMP_01", password="1234", status="Idle", last_seen="10:00:00"),
        Employee(id="EMP_02", password="password", status="Idle", last_seen="10:00:05"),
        Employee(id="EMP_03", password="admin", status="Occupied", last_seen="09:55:00"),
    ],
    customers=[
        Customer(id=101, status="Shopping", location="Aisle 1"),
        Customer(id=102, status="Needs Help", location="Checkout"),
    ],
    pending_notifications=[],
    unattended_zones={}
)

# --- Routes ---
@app.post("/login")
def login(request: LoginRequest):
    """validates credentials against the mock database."""
    emp = next((e for e in state.employees if e.id == request.id), None)
    
    if not emp:
        raise HTTPException(status_code=404, detail="Employee ID not found")
    
    if emp.password != request.password:
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    
    return {"message": "Login successful", "emp_id": emp.id}

# --- Routes ---
@app.get("/")
def read_root():
    return {"message": "Employee Monitoring System API is running"}

@app.get("/status", response_model=SystemState)
def get_status():
    """Returns the current simulated state of the supermarket."""
    return state

@app.post("/update_real_status")
def update_real_status(update: StatusUpdateRequest):
    """
    Receives real-time updates from Computer Vision Engine.
    Expected Payload: {"employee_id": "EMP_01", "status": "Idle", "unattended_customer": True}
    """
    # 1. Update Employee Status (if ID is known)
    emp = None
    if update.employee_id and update.employee_id != "UNKNOWN" and update.employee_id != "Scanning...":
        emp = next((e for e in state.employees if e.id == update.employee_id), None)
        if emp:
            emp.status = update.status
            import datetime
            emp.last_seen = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[REAL-TIME] Updated {emp.id} to {emp.status}")
        else:
            print(f"[WARNING] Employee ID {update.employee_id} not found in system.")

    # 2. Update Unattended Customer Status per Zone (using employee_id as the zone identifier)
    zone_id = update.employee_id
    state.unattended_zones[zone_id] = {
        "is_unattended": update.unattended_customer,
        "location": update.location
    }
            
    return {"message": "Status updated successfully"}

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
    Only sends an alert if the employee is Idle AND there is an Unattended Customer.
    """
    target_emp = next((e for e in state.employees if e.id == emp_id), None)
    
    if not target_emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Check if ANY zone is currently reporting an unattended customer
    unattended_zone_info = None
    for zone, info in state.unattended_zones.items():
        if isinstance(info, dict) and info.get("is_unattended"):
            unattended_zone_info = info
            break
        elif isinstance(info, bool) and info is True: # Fallback for old data structure
            unattended_zone_info = {"location": "Unknown"}
            break

    if target_emp.status == "Idle" and unattended_zone_info:
        loc = unattended_zone_info.get("location", "Unknown")
        return {"has_notification": True, "message": f"Unattended Customer at {loc}! Please assist."}
    
    return {"has_notification": False, "message": ""}
