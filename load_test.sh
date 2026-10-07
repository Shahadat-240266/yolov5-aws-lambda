#!/bin/bash
# Concurrency test for the detection API (run in AWS CloudShell).
# Usage: ./load_test.sh <invoke-url>/detect <api-key> [total_requests] [parallel]
# Example: ./load_test.sh https://abc123.execute-api.us-east-1.amazonaws.com/prod/detect MY_KEY 50 10
URL="$1"; KEY="$2"; TOTAL="${3:-50}"; PARALLEL="${4:-10}"
if [ -z "$URL" ] || [ -z "$KEY" ]; then
  echo "Usage: $0 <invoke-url>/detect <api-key> [total_requests] [parallel]"; exit 1
fi
OUT=$(mktemp)
START=$(date +%s.%N)
seq 1 "$TOTAL" | xargs -P "$PARALLEL" -I{} \
  curl -s -o /dev/null -w "%{http_code} %{time_total}\n" -X POST "$URL" \
  -H "x-api-key: $KEY" -H "Content-Type: application/json" \
  -d '{"image_key": "input-images/1.jpg"}' >> "$OUT"
END=$(date +%s.%N)
echo "Requests sent  : $TOTAL (parallel: $PARALLEL)"
awk -v s="$START" -v e="$END" 'BEGIN{printf "Wall-clock time: %.2f s\n", e-s}'
echo "HTTP status codes (count code):"
cut -d' ' -f1 "$OUT" | sort | uniq -c
awk '{s+=$2; if($2>m)m=$2; if(min==""||$2<min)min=$2} END {printf "Latency (s)    : avg %.3f, min %.3f, max %.3f\n", s/NR, min, m}' "$OUT"
rm -f "$OUT"
