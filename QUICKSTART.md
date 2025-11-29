# Quick Start Guide - DayPilot Orchestration Hub

Get up and running with the DayPilot Orchestration Hub in 5 minutes!

## Step 1: Install Dependencies (1 minute)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## Step 2: Start Application (30 seconds)

```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**All operations are logged to `trace/` folder!**

## Step 3: Test the API (2 minutes)

### 3.1 Check Health

```bash
curl http://localhost:8000/api/v1/health
```

### 3.2 Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=demo&password=demo123"
```

Save the `access_token` from response.

### 3.3 Upload User Data

```bash
TOKEN="<your-access-token>"

curl -X POST http://localhost:8000/api/v1/users/demo_user_001/data \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2024-01-15T14:30:00Z",
    "sensor_data": {
      "imu": {"acceleration": [0.1, 0.2, 9.8]},
      "hrv": {"heart_rate": 72},
      "environment": {"temperature": 22.5}
    }
  }'
```

### 3.4 Get User Status

```bash
curl http://localhost:8000/api/v1/users/demo_user_001/status \
  -H "Authorization: Bearer $TOKEN"
```

## Step 4: View Trace Logs (1 minute)

```bash
# View current session logs
tail -f trace/session_*.log

# View all operations
tail -f trace/trace_*.log

# View errors only
tail -f trace/error_*.log
```

## Step 5: Explore API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

## Docker Quick Start

Prefer Docker? Even faster!

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f orchestrator

# Check trace logs
tail -f trace/session_*.log
```

Access:
- API: http://localhost:8000
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

## What's Next?

1. **Explore the API**: Check out `API_DOCUMENTATION.md`
2. **Customize**: Edit `.env` file for your configuration
3. **Deploy**: Follow `DEPLOYMENT_GUIDE.md` for production
4. **Debug**: Always check `trace/` folder for detailed logs

## Demo Credentials

- **Username**: demo
- **Password**: demo123

## Key Features Demonstrated

✅ Workflow orchestration with LangGraph
✅ Multi-agent coordination
✅ Event-driven architecture
✅ Real-time WebSocket updates
✅ Comprehensive trace logging
✅ System health monitoring
✅ RESTful API with authentication

## Troubleshooting

**Port 8000 already in use?**
```bash
# Change port in .env
PORT=8001
```

**Import errors?**
```bash
# Make sure you're in virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

**Application errors?**
```bash
# Check trace logs for details
tail -f trace/error_*.log
```

## Important: Trace Logging

🔍 **All system operations are logged to files in `trace/` folder**

- No console logs (they disappear!)
- All errors, warnings, and debug info saved
- Includes full context for debugging
- Check logs FIRST when debugging issues

Example trace log entry:
```
[2024-01-15T14:30:00.123456] [INFO] main::upload_user_data:145
  Message: API call: POST /api/v1/users/demo_user_001/data
  Context: {
    "user_id": "demo_user_001",
    "timestamp": "2024-01-15T14:30:00Z"
  }
```

## Next Steps

- Read the full [README.md](README.md)
- Check [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- Follow [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for production

**Happy orchestrating! 🚀**
