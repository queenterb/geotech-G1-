# CIS Agent Auto-Update Logic (Python)
# Add this to your agent for Windows/Linux/Mac auto-update
import os
import requests
import sys
import shutil

def check_for_update(current_version, update_url, download_url):
    try:
        resp = requests.get(update_url, timeout=5)
        latest = resp.text.strip()
        if latest != current_version:
            print(f"Update available: {latest}")
            resp = requests.get(download_url, stream=True)
            with open("CISAgent_new.exe", "wb") as f:
                shutil.copyfileobj(resp.raw, f)
            print("Downloaded new version. Replacing...")
            os.replace("CISAgent_new.exe", sys.argv[0])
            os.execv(sys.argv[0], sys.argv)
    except Exception as e:
        print(f"Update check failed: {e}")

# Usage:
# check_for_update("1.0.0", "https://yourserver.com/cis/version.txt", "https://yourserver.com/cis/CISAgent.exe")
