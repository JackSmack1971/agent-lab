# Observability Guide

This document outlines the observability features implemented in Agent Lab, including metrics, health checks, logging, SLOs, and error budgets.

## Metrics

Agent Lab exposes Prometheus-compatible metrics at the `/metrics` endpoint.

### Available Metrics

#### Request Metrics
- `agent_lab_requests_total{method, endpoint, status}` - Total number of HTTP requests
- `agent_lab_request_duration_seconds{method, endpoint}` - Request duration histogram

#### Application Metrics
- `agent_lab_health_checks_total{status}` - Total health checks performed
- `agent_lab_agent_builds_total{success}` - Total agent builds (success/failure)
- `agent_lab_agent_runs_total{aborted}` - Total agent runs (completed/aborted)

### Scraping

Configure Prometheus to scrape the `/metrics` endpoint:

```yaml
scrape_configs:
  - job_name: 'agent-lab'
    static_configs:
      - targets: ['localhost:7860']
    metrics_path: '/metrics'
```

## Health Checks

The `/health` endpoint provides comprehensive health status information.

### Health Check Response

```json
{
  "status": "healthy|degraded|unhealthy",
  "version": "1.0.0",
  "timestamp": "2025-01-01T12:00:00.000Z",
  "dependencies": {
    "api_key": true,
    "database": true,
    "api_connectivity": true,
    "web_tool": true
  }
}
```

### Dependency Checks

- **api_key**: Presence of OPENROUTER_API_KEY environment variable
- **database**: Existence and accessibility of data/runs.csv
- **api_connectivity**: Successful connection to OpenRouter API
- **web_tool**: Availability of web fetch tool (optional)

### Status Logic

- **healthy**: All critical dependencies (api_key, database, api_connectivity) and optional dependencies working
- **degraded**: Critical dependencies working, some optional dependencies failing
- **unhealthy**: One or more critical dependencies failing

## Logging

Agent Lab uses structured JSON logging with correlation IDs for request tracing.

### Log Format

All logs are output as JSON with the following structure:

```json
{
  "timestamp": "2025-01-01T12:00:00.123456Z",
  "level": "INFO",
  "message": "Agent streaming completed",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_length": 42,
  "agent_model": "openai/gpt-4",
  "response_length": 150,
  "latency_ms": 1250,
  "aborted": false,
  "usage_available": true
}
```

### Correlation IDs

Each user request generates a unique correlation ID that is included in all related log entries across:
- Application layer (app.py)
- Runtime layer (agents/runtime.py)
- Persistence layer (services/persist.py)

This enables end-to-end tracing of requests through the system.

### Log Levels

- **INFO**: Normal operations, request completions
- **WARNING**: Recoverable issues, fallback behaviors
- **ERROR**: Failures that prevent operation

## SLOs (Service Level Objectives)

### Response Time SLO
- **Target**: 95% of requests complete within 5 seconds
- **Measurement**: `agent_lab_request_duration_seconds`
- **Alert Threshold**: 5% of requests exceed 5 seconds over 5-minute window

### Availability SLO
- **Target**: 99.9% uptime
- **Measurement**: Health check status over time
- **Alert Threshold**: 0.1% downtime over 1-hour window

### Agent Build Success SLO
- **Target**: 99% of agent builds succeed
- **Measurement**: `agent_lab_agent_builds_total{success="true"} / agent_lab_agent_builds_total`
- **Alert Threshold**: Success rate drops below 99% over 1-hour window

### Agent Run Completion SLO
- **Target**: 95% of agent runs complete without abortion
- **Measurement**: `agent_lab_agent_runs_total{aborted="false"} / agent_lab_agent_runs_total`
- **Alert Threshold**: Completion rate drops below 95% over 1-hour window

## Error Budgets

Error budgets are calculated as 100% - SLO target, allowing controlled degradation.

### Response Time Error Budget
- **Budget**: 5% of requests can exceed 5 seconds
- **Burn Rate Alert**: 2% of budget consumed in 1 hour
- **Burn Rate Critical**: 5% of budget consumed in 1 hour

### Availability Error Budget
- **Budget**: 0.1% downtime allowed
- **Monthly Budget**: ~43 minutes
- **Burn Rate Alert**: 2% of budget consumed in 1 hour
- **Burn Rate Critical**: 5% of budget consumed in 1 hour

### Agent Build Error Budget
- **Budget**: 1% of builds can fail
- **Burn Rate Alert**: 2% of budget consumed in 1 hour
- **Burn Rate Critical**: 5% of budget consumed in 1 hour

### Agent Run Error Budget
- **Budget**: 5% of runs can abort
- **Burn Rate Alert**: 2% of budget consumed in 1 hour
- **Burn Rate Critical**: 5% of budget consumed in 1 hour

## Alerting Rules

### Prometheus Alerting Rules

```yaml
groups:
  - name: agent_lab_alerts
    rules:
      - alert: HighRequestLatency
        expr: histogram_quantile(0.95, rate(agent_lab_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High request latency detected"
          description: "95th percentile request latency > 5s for 5 minutes"

      - alert: ServiceDown
        expr: up == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Agent Lab service is down"
          description: "Agent Lab has been down for 5 minutes"

      - alert: HealthCheckFailing
        expr: rate(agent_lab_health_checks_total{status="healthy"}[5m]) / rate(agent_lab_health_checks_total[5m]) < 0.999
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Health checks failing"
          description: "Less than 99.9% of health checks are healthy over 5 minutes"

      - alert: AgentBuildFailures
        expr: rate(agent_lab_agent_builds_total{success="false"}[1h]) / rate(agent_lab_agent_builds_total[1h]) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High agent build failure rate"
          description: "Agent build failure rate > 1% over 1 hour"

      - alert: AgentRunAborts
        expr: rate(agent_lab_agent_runs_total{aborted="true"}[1h]) / rate(agent_lab_agent_runs_total[1h]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High agent run abort rate"
          description: "Agent run abort rate > 5% over 1 hour"
```

## Dashboards

### Grafana Dashboard

Import the following dashboard JSON to visualize Agent Lab metrics:

```json
{
  "dashboard": {
    "title": "Agent Lab Observability",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_lab_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Request Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(agent_lab_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(agent_lab_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Health Status",
        "type": "stat",
        "targets": [
          {
            "expr": "agent_lab_health_checks_total{status='healthy'} / agent_lab_health_checks_total",
            "legendFormat": "Health Rate"
          }
        ]
      },
      {
        "title": "Agent Build Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(agent_lab_agent_builds_total{success='true'}[1h]) / rate(agent_lab_agent_builds_total[1h])",
            "legendFormat": "Build Success Rate"
          }
        ]
      },
      {
        "title": "Agent Run Completion Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(agent_lab_agent_runs_total{aborted='false'}[1h]) / rate(agent_lab_agent_runs_total[1h])",
            "legendFormat": "Run Completion Rate"
          }
        ]
      }
    ]
  }
}
```

## Runbooks

See `docs/operations/runbooks.md` for detailed incident response procedures based on these alerts.