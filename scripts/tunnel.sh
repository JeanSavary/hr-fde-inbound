#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Copy .env.example to .env and fill in your values."
  exit 1
fi

if ! grep -q "NGROK_AUTHTOKEN" .env || [ -z "$(grep NGROK_AUTHTOKEN .env | cut -d= -f2-)" ]; then
  echo "ERROR: NGROK_AUTHTOKEN is not set in .env"
  echo "  Get a free token at https://dashboard.ngrok.com/get-started/your-authtoken"
  exit 1
fi

echo "Building and starting services..."
docker compose up -d --build

echo "Waiting for ngrok tunnel..."
MAX_WAIT=20
for i in $(seq 1 $MAX_WAIT); do
  URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null) \
    && break
  sleep 1
done

if [ -z "${URL:-}" ]; then
  echo "ERROR: Could not retrieve ngrok URL after ${MAX_WAIT}s."
  echo "  Check logs: docker compose logs ngrok"
  exit 1
fi

echo ""
echo "========================================"
echo "  PUBLIC URL (paste into HappyRobot):"
echo "  $URL"
echo "========================================"
echo ""
echo "  Local API:      http://localhost:8000"
echo "  Swagger docs:   http://localhost:8000/docs"
echo "  ngrok inspect:  http://localhost:4040"
echo ""
echo "Tailing API logs (Ctrl+C to stop)..."
docker compose logs -f api
