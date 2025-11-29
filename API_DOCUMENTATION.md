# DayPilot Orchestration Hub - API Documentation

## Overview
Complete API reference for the DayPilot Orchestration Hub, the central coordination platform for the multi-agent vitality monitoring system.

**Base URL**: `http://localhost:8000/api/v1`

**All operations are logged to the `trace/` folder for debugging.**

## Authentication

### Login
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=demo&password=demo123
```

**Response**:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Create API Key
```http
POST /api/v1/auth/api-key
Authorization: Bearer {token}
```

**Response**:
```json
{
  "api_key": "dpoh_abc123...",
  "user_id": "demo_user_001",
  "created_at": "2024-01-15T14:30:00Z"
}
```

## Authentication Methods

The API supports two authentication methods:

1. **Bearer Token** (JWT):
   ```http
   Authorization: Bearer {token}
   ```

2. **API Key**:
   ```http
   X-API-Key: {api_key}
   ```

## User Data Endpoints

### Upload User Data
Upload sensor data and trigger workflow processing.

```http
POST /api/v1/users/{user_id}/data
Authorization: Bearer {token}
Content-Type: application/json

{
  "timestamp": "2024-01-15T14:30:00Z",
  "sensor_data": {
    "imu": {
      "acceleration": [0.1, 0.2, 9.8],
      "gyroscope": [0.01, 0.02, 0.01]
    },
    "hrv": {
      "heart_rate": 72,
      "rmssd": 45,
      "sdnn": 52
    },
    "environment": {
      "temperature": 22.5,
      "humidity": 45,
      "light_level": 300
    }
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "workflow_id": "abc123-...",
    "result": {
      "validated_data": {...},
      "rhythm_analysis": {
        "vitality_score": 0.72,
        "energy_state": "moderate",
        "risk_level": "low"
      },
      "intervention_plan": {
        "recommendations": [
          "Take a 10-minute break",
          "Practice deep breathing"
        ]
      }
    }
  },
  "timestamp": "2024-01-15T14:30:01Z",
  "request_id": "req_1234567890"
}
```

### Get User Status
Get current vitality status for a user.

```http
GET /api/v1/users/{user_id}/status
Authorization: Bearer {token}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "vitality_score": 0.72,
    "energy_state": "moderate",
    "risk_level": "low",
    "next_intervention": "2024-01-15T15:30:00Z",
    "recommendations": [
      "Take a short break",
      "Stay hydrated",
      "Practice deep breathing"
    ]
  },
  "timestamp": "2024-01-15T14:30:00Z",
  "request_id": "req_1234567891"
}
```

## System Endpoints

### System Health
Check overall system health (no authentication required).

```http
GET /api/v1/health
```

**Response**:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "services": {
    "workflow_engine": true,
    "agent_coordinator": true,
    "event_dispatcher": true,
    "rest_gateway": true
  },
  "metrics": {
    "workflow_engine": {
      "total_workflows": 150,
      "active_workflows": 5,
      "success_rate": 0.98
    },
    "agent_coordinator": {
      "total_agents": 3,
      "busy_agents": 1,
      "success_rate": 0.99
    }
  }
}
```

### Performance Metrics
Get detailed performance metrics.

```http
GET /api/v1/metrics/performance
Authorization: Bearer {token}
```

**Response**:
```json
{
  "timestamp": "2024-01-15T14:30:00Z",
  "uptime_seconds": 3600.5,
  "workflow_engine": {
    "total_workflows": 150,
    "active_workflows": 5,
    "completed_workflows": 142,
    "failed_workflows": 3,
    "success_rate": 0.98
  },
  "api_gateway": {
    "total_requests": 1250,
    "error_count": 5,
    "success_rate": 0.996
  },
  "websocket": {
    "active_connections": 45,
    "messages_sent": 2340,
    "messages_received": 890
  }
}
```

## Dashboard Endpoints

### Dashboard Overview
Get complete dashboard data.

```http
GET /api/v1/dashboard/overview
Authorization: Bearer {token}
```

**Response**: Complete system overview including health, performance, workflows, and alerts.

### Vitality Trend
Get vitality trend for a user.

```http
GET /api/v1/dashboard/vitality-trend/{user_id}?hours=24
Authorization: Bearer {token}
```

**Response**:
```json
{
  "user_id": "user123",
  "period_hours": 24,
  "data_points": [
    {
      "timestamp": "2024-01-15T14:00:00Z",
      "vitality_score": 0.72,
      "energy_state": "moderate"
    }
  ],
  "statistics": {
    "average": 0.71,
    "min": 0.55,
    "max": 0.85
  }
}
```

### System Performance Chart
Get system performance data for charting.

```http
GET /api/v1/dashboard/system-performance?minutes=60
Authorization: Bearer {token}
```

## Workflow Endpoints

### Get Workflow Status
Get status of a specific workflow execution.

```http
GET /api/v1/workflows/{workflow_id}
Authorization: Bearer {token}
```

**Response**:
```json
{
  "workflow_id": "abc123-...",
  "user_id": "user123",
  "start_time": "2024-01-15T14:30:00Z",
  "end_time": "2024-01-15T14:30:01Z",
  "status": "completed",
  "steps": [
    {
      "step_name": "perception",
      "status": "completed",
      "duration_ms": 50
    },
    {
      "step_name": "analysis",
      "status": "completed",
      "duration_ms": 120
    }
  ],
  "result": {...}
}
```

## WebSocket Real-time Updates

Connect to real-time updates via WebSocket.

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/realtime?token=YOUR_TOKEN');

ws.onopen = () => {
  console.log('Connected to DayPilot Hub');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'connection.established') {
    console.log('Connection established:', data.payload);
  }

  if (data.type === 'vitality_update') {
    console.log('Vitality update:', data.payload);
    updateDashboard(data.payload);
  }

  if (data.type === 'alert') {
    console.log('Alert:', data.payload);
    showAlert(data.payload);
  }
};

// Send ping
ws.send(JSON.stringify({
  type: 'ping'
}));

// Subscribe to topics
ws.send(JSON.stringify({
  type: 'subscribe',
  topics: ['vitality_updates', 'system_alerts']
}));
```

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message here",
  "timestamp": "2024-01-15T14:30:00Z",
  "request_id": "req_1234567890"
}
```

### Common Error Codes

- `401 Unauthorized`: Invalid or missing authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error (check trace logs)

## Rate Limiting

- **Default**: 60 requests per minute per client
- **Burst**: 10 additional requests allowed
- **Headers**: Rate limit info in response headers

## Trace Logging

All API operations are logged to files in the `trace/` folder:

- `trace/trace_YYYY-MM-DD.log` - All operations
- `trace/error_YYYY-MM-DD.log` - Errors only
- `trace/debug_YYYY-MM-DD.log` - Debug information
- `trace/session_YYYYMMDD_HHMMSS.log` - Current session

**For debugging, always check trace logs to identify root cause before making changes.**

## Demo Credentials

**Username**: demo
**Password**: demo123
**API Key**: Check trace logs after first startup for the generated demo API key

## Support

For issues or questions, check the trace logs in the `trace/` folder for detailed debugging information.
