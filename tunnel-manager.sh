#!/bin/bash

# This script manages the SSH tunnel and server processes for the DIY Content Moderation system.
# It ensures that the tunnel is always running and that the remote server is active.

# --- Configuration ---
SERVER_HOST="YOUR_EC2_HOST_HERE"
SSH_KEY="YOUR_SSH_KEY_PATH_HERE"
LOCAL_PORT="5001"
REMOTE_PORT="5000"
SERVER_USER="ubuntu"
MAX_RETRIES=10
RETRY_DELAY=5

# --- Logging ---
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] - $1"
}

success() {
    echo -e "\033[0;32m[SUCCESS] $1\033[0m"
}

error() {
    echo -e "\033[0;31m[ERROR] $1\033[0m"
}

# --- Functions ---
cleanup() {
    log "Performing cleanup..."
    
    # Kill existing SSH tunnels
    pkill -f "ssh.*${SERVER_HOST}.*${LOCAL_PORT}" 2>/dev/null
    
    # Kill processes using local port
    lsof -ti:${LOCAL_PORT} | xargs kill -9 2>/dev/null || true
    
    # Kill remote server processes
    ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_HOST} "pkill -f uvicorn" 2>/dev/null || true
    
    sleep 3
    log "Cleanup complete."
}

test_ssh() {
    log "Testing SSH connectivity..."
    if ssh -i ${SSH_KEY} -o ConnectTimeout=10 -o BatchMode=yes ${SERVER_USER}@${SERVER_HOST} "echo 'SSH test successful'" >/dev/null 2>&1; then
        success "SSH connection successful"
        return 0
    else
        error "SSH connection failed. Check your key, host, and security groups."
        return 1
    fi
}

start_remote_server() {
    log "Starting remote server..."
    
    # Create startup script on remote server
    ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_HOST} "cat > /tmp/start_diy_server.sh << 'EOF'
#!/bin/bash
export GOOGLE_API_KEY='${GOOGLE_API_KEY}'
export OPENAI_API_KEY='${OPENAI_API_KEY}'
cd /opt/DIY-MOD/Backend
source venv/bin/activate
nohup uvicorn fastapi_app:app --host 127.0.0.1 --port ${REMOTE_PORT} > /tmp/server.log 2>&1 &
EOF"

    # Make script executable and run it
    ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_HOST} "chmod +x /tmp/start_diy_server.sh && /tmp/start_diy_server.sh"
    
    # Check if server is running
    sleep 10
    if ssh -i ${SSH_KEY} ${SERVER_USER}@${SERVER_HOST} "curl -s http://localhost:${REMOTE_PORT}/ping" >/dev/null 2>&1; then
        success "Remote server started successfully"
        return 0
    else
        error "Failed to start remote server. Check /tmp/server.log on the EC2 instance."
        return 1
    fi
}

start_tunnel() {
    log "Starting SSH tunnel..."
    
    for ((i=1; i<=MAX_RETRIES; i++)); do
        # Start tunnel in background
        ssh -i ${SSH_KEY} -L ${LOCAL_PORT}:localhost:${REMOTE_PORT} -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 ${SERVER_USER}@${SERVER_HOST} &
        TUNNEL_PID=$!
        
        sleep 5
        
        # Test connection
        if curl -s "http://localhost:${LOCAL_PORT}/ping" > /dev/null; then
            success "SSH tunnel is active (PID: ${TUNNEL_PID})."
            return 0
        else
            error "Tunnel connection failed (attempt ${i}/${MAX_RETRIES}). Retrying..."
            kill ${TUNNEL_PID}
            sleep ${RETRY_DELAY}
        fi
    done
    
    error "Could not establish SSH tunnel after ${MAX_RETRIES} attempts."
    return 1
}

# --- Main Script ---
trap "cleanup; exit" SIGINT SIGTERM

cleanup
test_ssh || exit 1
start_remote_server || exit 1
start_tunnel 