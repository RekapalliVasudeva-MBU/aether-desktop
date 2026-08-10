#!/usr/bin/env python3
"""
Verification script for Aether Desktop App.
Run after building to confirm all endpoints work.
"""
import subprocess
import time
import sys
import requests
import json

def start_backend():
    """Start the backend server."""
    env = dict(os.environ)
    env["AETHER_PORT"] = "8732"
    proc = subprocess.Popen(
        [sys.executable, "-c", "from desktop_app_fixed import main; main()"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc

def wait_for_health(port=8732, timeout=30):
    """Wait for health endpoint to respond."""
    url = f"http://127.0.0.1:{port}/api/health"
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

def test_chat(message, mode="normal", port=8732):
    """Test chat endpoint."""
    url = f"http://127.0.0.1:{port}/api/chat"
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
    import os
    import sys
    
    print("=" * 60)
    print("Aether Desktop App Verification")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("desktop_app_fixed.py"):
        print("ERROR: Run from aether project root")
        sys.exit(1)
    
    # Kill any existing backend
    print("Killing existing processes on port 8732...")
    subprocess.run(["taskkill", "/F", "/PID", "8732"], capture_output=True)
    time.sleep(1)
    
    # Start backend
    print("Starting backend...")
    proc = start_backend()
    
    try:
        # Wait for health
        print("Waiting for health check...")
        if not wait_for_health():
            print("FAIL: Health check timeout")
            sys.exit(1)
        print("PASS: Health check OK")
        
        # Test normal mode
        print("Testing normal mode chat...")
        response = test_chat("hello", mode="normal")
        if response and len(response) > 10:
            print(f"PASS: Normal mode response ({len(response)} chars)")
        else:
            print(f"FAIL: Normal mode empty or too short: {response}")
            sys.exit(1)
        
        # Test RAG mode
        print("Testing RAG mode chat...")
        response = test_chat("what is rag", mode="rag")
        if response and "RAG" in response and "Retrieval" in response:
            print(f"PASS: RAG mode response ({len(response)} chars)")
        else:
            print(f"FAIL: RAG mode failed: {response[:200]}")
            sys.exit(1)
        
        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)