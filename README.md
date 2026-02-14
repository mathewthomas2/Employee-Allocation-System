# Employee Availability Monitoring System

An automated system to track employee engagement and availability using Computer Vision, updating a Supervisor Dashboard and a Mobile App for employees.

## Project Structure
- `backend/`: FastAPI server handling logic and mock data.
- `mobile_app/`: Flutter Android application for employees.
- `dashboard/`: Web interface for supervisors.
- `cv_engine/`: (Planned) Computer Vision module.

## How to Run

### 1. Start the Backend (Required First)
The backend acts as the central server.
1. Open a terminal.
2. Navigate to the backend directory:
   ```bash
   cd backend
   ```
3. Run the server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   *Note: Finding your local IP (e.g., `192.168.x.x`) is important for the mobile app to connect.*

### 2. Run the Employee App (Android)
1. Connect your Android device via USB (ensure Developer Options > USB Debugging is ON).
2. Open a **new** terminal.
3. Navigate to the app directory:
   ```bash
   cd mobile_app
   ```
4. Run the app:
   ```bash
   flutter run
   ```
5. **Login**: Use ID `EMP001` and Password `1234`.

### 3. Start the Computer Vision Brain (New)
1. Open a **new** terminal.
2. Run the detection script:
   ```bash
   python cv_engine/main.py
   ```
3. A window will open showing the video feed and detection boxes.

### 4. Open the Dashboard
1. Simply navigate to the `dashboard` folder in your file explorer.
2. Double-click `index.html` to open it in your web browser.
3. It will connect to `http://localhost:8000` automatically.

## How to Stop & Restart
To stop any part of the system (Backend, Mobile App, or CV), just click inside its terminal and press **Ctrl + C**.

To restart, simply run the command for that part again. All components are independent!