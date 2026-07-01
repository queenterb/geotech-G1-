import os
import time
import json
import traceback
from datetime import datetime

import requests
import cv2
import numpy as np
import base64


STREAM_URL = os.getenv("STREAM_URL", "http://media:80/hls/stream.m3u8")
API_ENDPOINT = os.getenv("API_ENDPOINT", "http://backend:8000/api/alerts")
API_TOKEN = os.getenv("CIS_SIEM_BEARER_TOKEN") or os.getenv("SIEM_SHARED_SECRET") or ""
MOTION_THRESHOLD = int(os.getenv("MOTION_THRESHOLD", "6000"))
CHECK_INTERVAL = float(os.getenv("CHECK_INTERVAL", "1.0"))

HEADERS = {"Content-Type": "application/json"}
if API_TOKEN:
    HEADERS["Authorization"] = f"Bearer {API_TOKEN}"


def post_alert(motion_score: int):
    payload = {
        "event_type": "behavior_analysis",
        "severity": "MEDIUM",
        "source": "behavior_worker",
        "payload": {"motion_score": int(motion_score)},
        "description": f"Motion detected (score={motion_score})",
    }
    try:
        resp = requests.post(API_ENDPOINT, json=payload, headers=HEADERS, timeout=5)
        if resp.status_code >= 400:
            print(f"[worker] alert post failed: {resp.status_code} {resp.text}")
        else:
            print(f"[worker] posted alert, score={motion_score}")
    except Exception as exc:
        print("[worker] failed to post alert", exc)


def open_capture(url: str):
    cap = cv2.VideoCapture(url)
    # Try a few times for streams that need startup
    for _ in range(5):
        if cap.isOpened():
            return cap
        time.sleep(1)
    return cap


def main():
    print(f"[worker] starting behavior worker, stream={STREAM_URL}, api={API_ENDPOINT}")
    prev_gray = None
    cap = None
    while True:
        try:
            if cap is None or not cap.isOpened():
                cap = open_capture(STREAM_URL)
                if not cap.isOpened():
                    print("[worker] unable to open stream, retrying in 5s")
                    time.sleep(5)
                    continue

            ret, frame = cap.read()
            if not ret or frame is None:
                # stream may have rotated segments; reopen
                print("[worker] empty frame, reopening capture")
                cap.release()
                cap = None
                time.sleep(1)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_gray is None:
                prev_gray = gray
                time.sleep(CHECK_INTERVAL)
                continue

            frame_delta = cv2.absdiff(prev_gray, gray)
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            non_zero = int(np.count_nonzero(thresh))

            if non_zero > MOTION_THRESHOLD:
                # create a small JPEG thumbnail for visual context
                try:
                    small = cv2.resize(frame, (320, 180))
                    _, imgenc = cv2.imencode('.jpg', small, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                    thumb_b64 = base64.b64encode(imgenc.tobytes()).decode('ascii')
                except Exception:
                    thumb_b64 = None

                print(f"[worker] motion detected: score={non_zero} > {MOTION_THRESHOLD}")
                # attach thumbnail when available
                if thumb_b64:
                    payload_with_thumb = {
                        "event_type": "behavior_analysis",
                        "severity": "MEDIUM",
                        "source": "behavior_worker",
                        "payload": {"motion_score": int(non_zero), "thumbnail_base64": thumb_b64},
                        "description": f"Motion detected (score={non_zero})",
                    }
                    try:
                        resp = requests.post(API_ENDPOINT, json=payload_with_thumb, headers=HEADERS, timeout=5)
                        if resp.status_code >= 400:
                            print(f"[worker] alert post failed: {resp.status_code} {resp.text}")
                        else:
                            print(f"[worker] posted alert with thumbnail, score={non_zero}")
                    except Exception as exc:
                        print("[worker] failed to post alert with thumbnail", exc)
                else:
                    post_alert(non_zero)

            prev_gray = gray
            time.sleep(CHECK_INTERVAL)

        except Exception:
            print("[worker] unexpected error:")
            traceback.print_exc()
            time.sleep(2)


if __name__ == "__main__":
    main()
