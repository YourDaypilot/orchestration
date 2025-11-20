# DayPilot Orchestration Hub - Deployment Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- PostgreSQL 16+ (if not using Docker)
- Redis 7+ (if not using Docker)
- MongoDB 7+ (if not using Docker)

## Quick Start (Development)

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/daypilot-orchestration-hub.git
cd daypilot-orchestration-hub
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Run Application

```bash
python main.py
```

The application will start on `http://localhost:8000`

**Check trace logs**: All operations are logged to `trace/` folder for debugging.

## Docker Deployment (Recommended for Production)

### 1. Build and Start Services

```bash
docker-compose up -d
```

This starts:
- Orchestration Hub (port 8000)
- PostgreSQL (port 5432)
- Redis (port 6379)
- MongoDB (port 27017)
- Prometheus (port 9090)
- Grafana (port 3000)

### 2. Check Logs

```bash
# Application logs
docker-compose logs -f orchestrator

# Check trace logs (mounted volume)
tail -f trace/session_*.log
```

### 3. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

### 4. Stop Services

```bash
docker-compose down
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace daypilot
```

### 2. Apply Configurations

```bash
# Create secrets
kubectl create secret generic daypilot-secrets \
  --from-literal=database-url='postgresql://...' \
  --from-literal=secret-key='your-secret-key' \
  -n daypilot

# Deploy application
kubectl apply -f k8s/deployment.yaml -n daypilot
kubectl apply -f k8s/service.yaml -n daypilot
kubectl apply -f k8s/ingress.yaml -n daypilot
```

### 3. Monitor Deployment

```bash
kubectl get pods -n daypilot
kubectl logs -f deployment/daypilot-orchestrator -n daypilot
```

## Configuration

### Environment Variables

Key configuration variables (see `.env.example` for full list):

```bash
# Application
DEBUG=false                    # Set to false in production
HOST=0.0.0.0
PORT=8000
WORKERS=4                      # Number of worker processes

# Security
SECRET_KEY=<strong-random-key> # CHANGE THIS!
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql://user:pass@host:5432/daypilot
REDIS_URL=redis://host:6379/0
MONGODB_URL=mongodb://host:27017/daypilot

# Performance
MAX_CONCURRENT_WORKFLOWS=100
REQUEST_TIMEOUT_SECONDS=30
WORKFLOW_TIMEOUT_SECONDS=60

# Monitoring
ENABLE_METRICS=true
HEALTH_CHECK_INTERVAL=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Tracing
TRACE_RETENTION_DAYS=30       # Keep trace logs for 30 days
```

## Security Considerations

### 1. Change Default Credentials

```bash
# Generate strong secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Update .env file
SECRET_KEY=<generated-key>
```

### 2. Use HTTPS in Production

Configure reverse proxy (nginx/traefik) with SSL/TLS certificates.

### 3. Secure Database Connections

- Use strong passwords
- Enable SSL/TLS for database connections
- Restrict network access with firewall rules

### 4. API Key Management

- Rotate API keys regularly
- Store keys securely (use secrets management)
- Monitor API key usage in trace logs

## Monitoring and Observability

### Trace Logging

All operations are logged to `trace/` folder:

```bash
# View current session logs
tail -f trace/session_*.log

# View errors only
tail -f trace/error_*.log

# View debug logs
tail -f trace/debug_*.log

# Search for specific issues
grep "ERROR" trace/trace_*.log
grep "workflow_id" trace/session_*.log
```

**IMPORTANT**: Always check trace logs when debugging issues. They contain complete context about all operations.

### Prometheus Metrics

Access metrics at `http://localhost:9090`

Key metrics to monitor:
- Workflow success rate
- API response times
- Error rates
- Active connections
- Resource usage

### Grafana Dashboards

Access Grafana at `http://localhost:3000`

Import dashboards for:
- System health overview
- API performance
- Workflow execution
- Resource utilization

## Performance Tuning

### 1. Worker Processes

Adjust based on CPU cores:
```bash
WORKERS=$(nproc)  # Use all CPU cores
```

### 2. Database Connection Pool

Configure in `config/settings.py`:
```python
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### 3. Redis Cache

Increase cache size for better performance:
```bash
# In docker-compose.yml
redis:
  command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

### 4. Rate Limiting

Adjust based on expected load:
```bash
RATE_LIMIT_PER_MINUTE=120  # Increase for higher traffic
```

## Backup and Recovery

### 1. Database Backup

```bash
# PostgreSQL
docker exec daypilot-postgres pg_dump -U daypilot daypilot > backup.sql

# MongoDB
docker exec daypilot-mongo mongodump --out=/backup
```

### 2. Trace Logs Backup

```bash
# Archive old logs
tar -czf trace_backup_$(date +%Y%m%d).tar.gz trace/

# Upload to S3 or other storage
aws s3 cp trace_backup_*.tar.gz s3://your-bucket/backups/
```

### 3. Configuration Backup

```bash
# Backup environment and configs
tar -czf config_backup.tar.gz .env docker-compose.yml monitoring/
```

## Troubleshooting

### Application Won't Start

1. Check trace logs: `tail -f trace/session_*.log`
2. Verify dependencies: `pip list`
3. Check ports: `netstat -tulpn | grep 8000`
4. Review configuration: `cat .env`

### High Error Rate

1. Check error logs: `tail -f trace/error_*.log`
2. Review system health: `curl http://localhost:8000/api/v1/health`
3. Check database connections
4. Monitor resource usage: `docker stats`

### Slow Performance

1. Check trace logs for slow operations
2. Review workflow execution times
3. Monitor database query performance
4. Check network latency
5. Increase worker processes if CPU-bound

### Database Connection Issues

1. Verify database is running: `docker ps`
2. Check connection string in .env
3. Test connection: `docker exec -it daypilot-postgres psql -U daypilot`
4. Review trace logs for connection errors

## Health Checks

### Automated Health Checks

```bash
# HTTP health check
curl http://localhost:8000/api/v1/health

# Docker health check
docker inspect daypilot-orchestrator --format='{{.State.Health.Status}}'
```

### Manual Verification

```bash
# Check all services
docker-compose ps

# Check trace logs
ls -lh trace/

# Test API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=demo&password=demo123"
```

## Scaling

### Horizontal Scaling

Deploy multiple instances behind load balancer:

```bash
docker-compose up -d --scale orchestrator=3
```

### Load Balancing

Use nginx or HAProxy:

```nginx
upstream daypilot {
    server orchestrator1:8000;
    server orchestrator2:8000;
    server orchestrator3:8000;
}
```

## Production Checklist

- [ ] Change all default passwords and secret keys
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up automated backups
- [ ] Configure monitoring and alerting
- [ ] Set DEBUG=false
- [ ] Configure log rotation for trace logs
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Document disaster recovery procedures
- [ ] Perform load testing
- [ ] Set up CI/CD pipeline
- [ ] Configure rate limiting
- [ ] Review trace log retention policy

## Support

For issues:
1. Check trace logs in `trace/` folder first
2. Review error logs: `trace/error_*.log`
3. Search session logs for specific request IDs
4. Check system health endpoint
5. Review monitoring dashboards

Remember: **All operations are traced to files. Always check trace logs to identify root cause before debugging.**
