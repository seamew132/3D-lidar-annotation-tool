import os
import sys

if sys.platform.startswith('win'):
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import threading
import time
import webbrowser

IS_FROZEN = getattr(sys, 'frozen', False)
if IS_FROZEN:
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = BUNDLE_DIR

web_app_dir = os.path.join(BUNDLE_DIR, 'web_app')
if web_app_dir not in sys.path:
    sys.path.insert(0, web_app_dir)
if BUNDLE_DIR not in sys.path:
    sys.path.insert(0, BUNDLE_DIR)

from server import app as main_app
from fast_check_app import app as fast_check_app

def run_fast_check_server():
    """Runs Standalone FastCheck Flask app on port 5050 in background."""
    try:
        fast_check_app.run(host='0.0.0.0', port=5050, debug=False, use_reloader=False)
    except Exception as e:
        print(f"FastCheck Server error: {e}")

def run_main_server():
    """Runs Main Web Annotation Flask app on port 5000."""
    try:
        main_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Main Server error: {e}")

def open_main_browser():
    """Auto-opens ONLY http://localhost:5000/ in default browser."""
    time.sleep(1.5)
    try:
        webbrowser.open("http://localhost:5000/")
    except Exception:
        pass

if __name__ == '__main__':
    print("=========================================================")
    print(" [OK] ADO Web Annotation Tool + 3D FastCheck Dual Server")
    print("=========================================================")
    print(" - Main Web Tool: http://localhost:5000/")
    print(" - FastCheck 3D : http://localhost:5050/")
    print("=========================================================")
    print("\nStarting servers...")

    # Start FastCheck server on port 5050 in background thread
    t_fastcheck = threading.Thread(target=run_fast_check_server, daemon=True)
    t_fastcheck.start()

    # Schedule browser auto-open for main tool (port 5000)
    threading.Thread(target=open_main_browser, daemon=True).start()

    # Run Main server on port 5000 on main thread
    run_main_server()
