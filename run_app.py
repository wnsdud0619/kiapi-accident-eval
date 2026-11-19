"""주소창 없는 앱 창 실행 런처 (단일 .exe 패키징 및 직접 실행 공용)"""
import os
import sys
import time
import socket
import shutil
import tempfile
import threading
import subprocess
import webbrowser
import urllib.request


def setup_logging():
    """--noconsole 실행 시 sys.stdout / sys.stderr 가 None 이 되는 문제 방지"""
    log_dir = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "KIAPI_Accident_Eval")
    os.makedirs(log_dir, exist_ok=True)
    log_file = open(os.path.join(log_dir, "app.log"), "w", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r", encoding="utf-8")
    return log_file


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_chromium_browser():
    candidates = [
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        shutil.which("msedge"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def wait_for_server(port, timeout=30.0):
    health_url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def launch_app_window(port):
    if not wait_for_server(port):
        print(f"[ERR] Streamlit server did not respond on port {port}", flush=True)
        os._exit(1)

    url = f"http://127.0.0.1:{port}"
    browser = find_chromium_browser()
    print(f"[INFO] Server ready at {url} | browser={browser}", flush=True)
    if browser:
        profile_dir = tempfile.mkdtemp(prefix="kiapi_eval_ui_")
        try:
            cmd = [
                browser,
                f"--app={url}",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-features=msEdgeStartupBoost",
                "--window-size=1480,920",
                "--new-window",
            ]
            t0 = time.monotonic()
            proc = subprocess.Popen(cmd, cwd=tempfile.gettempdir())
            proc.wait()
            elapsed = time.monotonic() - t0
            print(f"[INFO] Browser process exited after {elapsed:.2f}s", flush=True)
            if elapsed >= 2.0:
                shutil.rmtree(profile_dir, ignore_errors=True)
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(0)
        except Exception as e:
            print(f"[WARN] Browser app launch failed: {e}", flush=True)
            shutil.rmtree(profile_dir, ignore_errors=True)
            webbrowser.open(url)
    else:
        webbrowser.open(url)


def main():
    setup_logging()

    # PyInstaller 종속성 분석 보장용 import (app.py 가 data 로 포함됨)
    import traceback
    import pandas  # noqa: F401
    import numpy  # noqa: F401
    import plotly.graph_objects  # noqa: F401
    from plotly.subplots import make_subplots  # noqa: F401
    from streamlit import config as _config
    from streamlit.web import bootstrap

    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    app_path = os.path.abspath(os.path.join(base_dir, "app.py"))

    # 샘플 CSV가 있는 외부 폴더 및 _MEI 임시 폴더 잠금을 피하도록 전용 빈 작업 디렉터리 사용
    work_dir = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "KIAPI_Accident_Eval", "workdir")
    os.makedirs(work_dir, exist_ok=True)
    os.chdir(work_dir)

    port = find_free_port()
    threading.Thread(target=launch_app_window, args=(port,), daemon=True).start()

    flag_options = {
        "server_port": port,
        "server_address": "127.0.0.1",
        "server_headless": True,
        "server_fileWatcherType": "none",
        "global_developmentMode": False,
        "browser_gatherUsageStats": False,
        "client_toolbarMode": "minimal",
    }
    try:
        _config._main_script_path = app_path
        bootstrap.load_config_options(flag_options=flag_options)
        bootstrap.run(app_path, False, [], flag_options)
    except Exception:
        traceback.print_exc()
        os._exit(1)


if __name__ == "__main__":
    main()
