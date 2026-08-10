#!/usr/bin/env python3
"""
Verification script for Frozen Python Desktop Apps (PyInstaller + pywebview).
Generic pattern that works for Aether and similar apps.
"""
import subprocess
import time
import sys
import os
import requests
import json
import signal

def run_test(script_path, port=8732, health_endpoint="/api/health", chat_endpoint="/api/chat"):
    """
    Run full verification suite for a frozen desktop app.
    
    Args:
        script_path: Path to the main entry point script (e.g., desktop_app_fixed.py)
        port: Port the app runs on
        health_endpoint: Health check endpoint
        chat_endpoint: Chat endpoint
    
    Returns:
        True if all tests pass, False otherwise
    """
    base_url = f"http://127.0.0.1:{port}"
    health_url = f"{base_url}{health_endpoint}"
    chat_url = f"{base_url}{chat_endpoint}"
    
    # Kill existing processes on port
    print(f"[1/5] Killing existing processes on port {port}...")
    try:
        subprocess.run(["taskkill", "/F", "/FI", f"PID eq {port}"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "Aether.exe"], capture_output=True)
    except:
        pass
    time.sleep(1)
    
    # Start backend
    print(f"[2/5] Starting backend from {script_path}...")
    env = dict(os.environ)
    env["AETHER_PORT"] = str(port)
    proc = subprocess.Popen(
        [sys.executable, "-c", f"from {os.path.splitext(os.path.basename(script_path))[0]} import main; main()"],
        cwd=os.path.dirname(script_path) or ".",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    try:
        # Wait for health
        print(f"[3/5] Waiting for health endpoint...")
        if not wait_for_url(health_url, timeout=30):
            print("    FAIL: Health check timeout")
            return False
        print("    PASS: Health check OK")
        
        # Test normal mode
        print(f"[4/5] Testing normal mode chat...")
        response = test_chat(chat_url, "hello", mode="normal")
        if not response or len(response) < 10:
            print(f"    FAIL: Normal mode failed: {response[:200]}")
            return False
        print(f"    PASS: Normal mode ({len(response)} chars)")
        
        # Test RAG mode
        print(f"[5/5] Testing RAG mode chat...")
        response = test_chat(chat_url, "what is rag", mode="rag")
        if not response or "RAG" not in response or "Retrieval" not in response:
            print(f"    FAIL: RAG mode failed: {response[:200]}")
            return False
        print(f"    PASS: RAG mode ({len(response)} chars)")
        
        print("\n" + "=" * 50)
        print("ALL VERIFICATION TESTS PASSED")
        print("=" * 50)
        return True
        
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()

def wait_for_url(url, timeout=30):
    """Wait for URL to return 200 OK."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def test_chat(url, message, mode="normal"):
    """Test chat endpoint and return full response."""
    r = requests.post(
        url,
        json={"message": message, "mode": mode},
        headers={"Content-Type": "application/json"},
        timeout=30,
        stream=True
    )
    chunks = []
    for line in r.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if 'token' in data:
                        chunks.append(data['token'])
                    if 'done' in data:
                        break
                except:
                    pass
    return ''.join(chunks)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify frozen Python desktop app")
    parser.add_argument("script", nargs="?", default="desktop_app_fixed.py", 
                        help="Main entry point script")
    parser.add_argument("--port", type=int, default=8732, help="App port")
    args = parser.parse_args()
    
    script_path = os.path.abspath(args.script)
    if not os.path.exists(script_path):
        print(f"ERROR: {script_path} not found")
        sys.exit(1)
    
    success = run_test(script_path, port=args.port)
    sys.exit(0 if success else 1)