#!/usr/bin/env python3
"""
Daily tunnel manager - runs as a cron job at 8 AM daily.
Kills old tunnel, starts fresh quick tunnel, extracts new URL, reports it.
The new tunnel runs detached in background and survives after script exits.
"""
import subprocess
import time
import re
import sys
import os
import signal

def run_cmd(cmd, timeout=10):
    """Run command and return (success, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, 
            text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)

def main():
    cloudflared = r"C:\\Program Files (x86)\\cloudflared\\cloudflared.exe"
    # Actual working server location (worktree)
    project_dir = r"C:\\Users\\valte\\project_rag.worktrees\\ngrok-hosting-aether-minds-app"
    
    print(f"=== Daily Tunnel Restart - {time.ctime()} ===")
    
    # 1. Kill all existing cloudflared processes
    print("1. Stopping old tunnel...")
    run_cmd("taskkill /F /IM cloudflared.exe")
    time.sleep(2)
    
    # 2. Start new quick tunnel in background (detached)
    print("2. Starting new quick tunnel...")
    cmd = f'"{cloudflared}" tunnel --url http://localhost:8000'
    
    # Use CREATE_NEW_PROCESS_GROUP to detach on Windows
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    
    proc = subprocess.Popen(
        cmd, shell=True, cwd=project_dir,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, creationflags=creation_flags
    )
    
    # 3. Wait for URL to appear in output
    print("3. Waiting for tunnel URL...")
    url = None
    start_time = time.time()
    
    while time.time() - start_time < 45:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.5)
            continue
        line = line.strip()
        if line:
            print(f"   {line}")
            match = re.search(r'https://[a-z0-9-]+\\.trycloudflare\\.com', line)
            if match:
                url = match.group(0)
                break
    
    if not url:
        print("   ERROR: Could not extract URL")
        proc.terminate()
        return 1
    
    # 4. Verify tunnel works
    print(f"\n4. Verifying tunnel: {url}")
    time.sleep(3)
    success, stdout, stderr = run_cmd(f'curl -s {url}/api/health', timeout=15)
    if success and '"status":"ok"' in stdout:
        print("   ✅ Health check passed")
    else:
        print(f"   ⚠️ Health check failed: {stdout[:200]}")
    
    # 5. Report the URL (this gets delivered by cron)
    print(f"\n=== DAILY TUNNEL URL ===")
    print(f"Date: {time.strftime('%Y-%m-%d')}")
    print(f"Website:     {url}")
    print(f"Health:      {url}/api/health")
    print(f"Chat API:    {url}/api/chat")
    print(f"Download:    {url}/download/aether")
    print(f"RAG Docs:    {url}/knowledge")
    print(f"\nThis URL is valid until next daily restart (8 AM tomorrow).")
    print(f"Server runs on your laptop - laptop on = site on.")
    
    # Process continues running in background (detached)
    # We exit here but the tunnel keeps running
    return 0

if __name__ == "__main__":
    sys.exit(main())