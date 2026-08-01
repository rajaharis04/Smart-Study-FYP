#!/bin/bash
# ============================================================
# SmartStudy - Start All Services
# Runs:
#   - Admin Backend       → http://localhost:8001
#   - AI Video Backend    → http://localhost:8000
#   - Teacher Portal UI   → http://localhost:5173
# ============================================================

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$ROOT_DIR/.." && pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     SmartStudy — Starting All Services       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. Start Admin Backend (port 8001) ─────────────────────
echo "[1/3] Starting Admin Backend on port 8001..."
cd "$ROOT_DIR/backend"
uvicorn main:app --host 0.0.0.0 --port 8001 --reload &
ADMIN_PID=$!
echo "      Admin Backend PID: $ADMIN_PID"

# ── 2. Start AI Video Backend (port 8000) ──────────────────
echo "[2/3] Starting AI Video Backend on port 8000..."
cd "$PROJECT_DIR/video-lecture/backend"
python3 start_server.py &
VIDEO_PID=$!
echo "      AI Video Backend PID: $VIDEO_PID"

# ── 3. Start Teacher Portal Frontend (port 5173) ───────────
echo "[3/3] Starting Teacher Portal Frontend on port 5173..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "      Frontend PID: $FRONTEND_PID"

echo ""
echo "✅  All services started!"
echo "   Admin API:      http://localhost:8001/docs"
echo "   AI Video API:   http://localhost:8000/docs"
echo "   Teacher Portal: http://localhost:5173"
echo ""
echo "   Press Ctrl+C to stop all services."
echo ""

# Wait and cleanup on exit
trap "echo ''; echo 'Stopping all services...'; kill $ADMIN_PID $VIDEO_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
