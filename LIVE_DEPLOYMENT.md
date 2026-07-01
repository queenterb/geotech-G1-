Live deployment (local / cloud)
--------------------------------

Quick start (local Docker Compose):

1. Build and start services:

```
docker-compose up -d --build
```

2. Frontend UI: http://localhost:4173

3. Backend API: http://localhost:8000/api

4. HLS stream URL (player): http://localhost:8082/hls/stream.m3u8

RTMP ingest (from OBS or other encoder):

- RTMP URL: rtmp://<host>:1935/live
- Stream key: stream

Example OBS settings: set the server to `rtmp://localhost:1935/live` and the stream key to `stream`. Start streaming — the HLS playlist will be available at `/hls/stream.m3u8`.

Exposing to the internet:

- For quick remote access, use a TCP tunnel (ngrok/tailscale) to expose ports `4173` (frontend) and `1935` (RTMP). For production, put the stack behind a TLS-terminating reverse proxy and secure the SIEM endpoints with tokens.

Next steps (recommended):
- Add a behavior analysis worker that subscribes to streams or pulls frames and posts analysis results to `/api/alerts`.
- Replace the HLS path with a low-latency WebRTC pipeline for sub-second latency if required.
