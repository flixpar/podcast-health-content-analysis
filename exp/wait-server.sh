#!/bin/bash
# Wait until the server on 8222 answers /v1/models, or its log shows it died.
LOG=$1
until curl -sf --noproxy '*' http://127.0.0.1:8222/v1/models >/dev/null; do
  if grep -q "SERVER_EXITED\|Traceback" "$LOG" 2>/dev/null; then echo "SERVER FAILED"; grep -m3 -i "error" "$LOG" | tail -3; exit 1; fi
  sleep 5
done
echo READY
