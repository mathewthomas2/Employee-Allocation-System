import os
import sys
import subprocess
import time

def run_case(case_folder):
    case_path = os.path.join("videos", case_folder)
    
    if not os.path.exists(case_path):
        print(f"Error: Folder '{case_path}' does not exist.")
        return
        
    video_extensions = ['.mov', '.mp4', '.avi', '.mkv']
    videos_to_run = []
    
    # Find all videos in the case folder
    for file in os.listdir(case_path):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            videos_to_run.append(os.path.join(case_path, file))
            
    if not videos_to_run:
        print(f"No videos found in '{case_path}'. Add some .MOV or .mp4 files.")
        return

    print(f"Found {len(videos_to_run)} videos in {case_path}. Starting Multi-Camera Simulation...")
    
    processes = []
    
    # Launch each video as an independent process
    for i, video in enumerate(videos_to_run):
        print(f"[{i+1}/{len(videos_to_run)}] Starting Virtual Camera for: {video}")
        # Use sys.executable to ensure we use the same Python environment
        p = subprocess.Popen([sys.executable, os.path.join("cv_engine", "main.py"), video])
        processes.append(p)
        time.sleep(1) # Give OpenCV a second to initialize the window
        
    print("\nAll Virtual Cameras are running!")
    print("Press Ctrl+C in this terminal to stop all cameras and end the simulation.")
    
    try:
        # Keep the launcher alive while the children are running
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\nShutting down all Virtual Cameras...")
        for p in processes:
            p.terminate()
        print("Simulation ended.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_scenario.py <case_folder_name>")
        print("Example: python run_scenario.py case1")
    else:
        run_case(sys.argv[1])
