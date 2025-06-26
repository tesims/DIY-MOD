# DIY-MOD FastAPI Deployment Instructions

## Quick Start (Manual)

1. SSH into the EC2 instance:
```bash
ssh -i /path/to/keypair.pem ubuntu@ec2-13-58-180-224.us-east-2.compute.amazonaws.com
```

2. Navigate to the Backend directory:
```bash
cd /opt/DIY-MOD/Backend
```

3. Pull the latest code:
```bash
git pull origin main
```

4. Install/update dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

5. Start the FastAPI server:
```bash
./start_fastapi_server.sh
```

## Systemd Service Setup (Recommended)

1. Copy the service file:
```bash
sudo cp /opt/DIY-MOD/Backend/diy-mod-fastapi.service /etc/systemd/system/
```

2. Reload systemd:
```bash
sudo systemctl daemon-reload
```

3. Enable and start the service:
```bash
sudo systemctl enable diy-mod-fastapi
sudo systemctl start diy-mod-fastapi
```

4. Check service status:
```bash
sudo systemctl status diy-mod-fastapi
```

## Celery Workers

Start Celery workers in a separate terminal or screen session:
```bash
cd /opt/DIY-MOD/Backend
source venv/bin/activate
celery -A CartoonImager worker --loglevel=info
```

## Testing

1. Test HTTP endpoints:
```bash
curl http://localhost:5000/health
curl http://localhost:5000/test
```

2. Test WebSocket connection:
```bash
cd /opt/DIY-MOD/Backend
python test_websocket_client.py
```

## Monitoring

- View FastAPI logs: `sudo journalctl -u diy-mod-fastapi -f`
- View Celery logs: Check the terminal where Celery is running
- Check Redis: `redis-cli ping`

## Common Issues

1. **Port already in use**: Kill existing processes
   ```bash
   pkill -f uvicorn
   pkill -f hypercorn
   ```

2. **Import errors**: Ensure you're using the virtual environment
   ```bash
   source venv/bin/activate
   ```

3. **Redis connection errors**: Ensure Redis is running
   ```bash
   sudo systemctl status redis
   sudo systemctl start redis
   ``` 