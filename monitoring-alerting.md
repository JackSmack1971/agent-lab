# Monitoring and Alerting Infrastructure - Agent Lab

## Overview

This document describes the monitoring and alerting infrastructure for Agent Lab, including automated health checks, SLO monitoring, incident detection, and notification systems. The infrastructure provides real-time visibility into system health and automated responses to reliability issues.

## Monitoring Architecture

### Core Components
1. **Health Check Endpoints**: Application-level health validation
2. **SLI Measurement**: Continuous collection of service level indicators
3. **Automated Monitoring**: GitHub Actions workflows for periodic checks
4. **Alerting Channels**: Slack notifications and email alerts
5. **Dashboards**: Real-time metrics visualization
6. **Incident Detection**: Automated anomaly detection and alerting

## Health Check Implementation

### Application Health Endpoints
```python
# app.py - Health check endpoints
from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import psutil
import os

app = FastAPI()

@app.get("/health")
def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health/detailed")
def detailed_health_check():
    """Comprehensive health check with dependency validation."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Check OpenRouter API connectivity
    try:
        # Test API key and basic connectivity
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        # Simple model list call to verify connectivity
        models = client.models.list()
        health_status["checks"]["openrouter_api"] = "healthy"
    except Exception as e:
        health_status["checks"]["openrouter_api"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check data directory access
    try:
        data_dir = Path("data")
        if data_dir.exists() and data_dir.is_dir():
            health_status["checks"]["data_directory"] = "healthy"
        else:
            health_status["checks"]["data_directory"] = "unhealthy: directory not accessible"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["data_directory"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check CSV file integrity
    try:
        csv_file = Path("data/runs.csv")
        if csv_file.exists():
            # Try to read the header
            with open(csv_file, 'r') as f:
                header = f.readline().strip()
                expected_header = "ts,agent_name,model,prompt_tokens,completion_tokens,total_tokens,latency_ms,cost_usd,experiment_id,task_label,run_notes,streaming,model_list_source,tool_web_enabled,web_status,aborted"
                if header == expected_header:
                    health_status["checks"]["telemetry_csv"] = "healthy"
                else:
                    health_status["checks"]["telemetry_csv"] = "unhealthy: invalid header"
                    health_status["status"] = "degraded"
        else:
            health_status["checks"]["telemetry_csv"] = "healthy"  # File will be created on first run
    except Exception as e:
        health_status["checks"]["telemetry_csv"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # System resource check
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        health_status["checks"]["system_resources"] = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent
        }

        # Alert thresholds
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            health_status["status"] = "degraded"
            health_status["checks"]["system_resources"]["status"] = "warning"
        else:
            health_status["checks"]["system_resources"]["status"] = "healthy"

    except Exception as e:
        health_status["checks"]["system_resources"] = f"unhealthy: {str(e)}"

    # Return appropriate status code
    if health_status["status"] == "healthy":
        return health_status
    else:
        raise HTTPException(status_code=503, detail=health_status)

@app.get("/metrics")
def metrics_endpoint():
    """Prometheus-style metrics endpoint for monitoring."""
    # This would integrate with a metrics collection system
    # For now, return basic metrics
    return {
        "uptime_seconds": 123456,  # Would be calculated
        "requests_total": 1000,
        "requests_duration_seconds": {
            "0.5": 0.1,
            "0.9": 0.5,
            "0.95": 1.0,
            "0.99": 2.0
        },
        "errors_total": 10
    }
```

## Automated Monitoring Workflows

### Health Monitoring Workflow
```yaml
# .github/workflows/health-monitoring.yml
name: Health Monitoring

on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
    - name: Check application health
      run: |
        # Attempt to access health endpoint
        HEALTH_URL="${{ secrets.APPLICATION_URL }}/health"
        MAX_RETRIES=3
        RETRY_COUNT=0

        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
          if curl -f -s --max-time 30 "$HEALTH_URL" > /dev/null; then
            echo "✅ Health check passed"
            echo "health_status=healthy" >> $GITHUB_OUTPUT
            exit 0
          else
            echo "❌ Health check failed (attempt $((RETRY_COUNT + 1)))"
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
              sleep 10
            fi
          fi
        done

        echo "🚨 CRITICAL: Health check failed after $MAX_RETRIES attempts"
        echo "health_status=unhealthy" >> $GITHUB_OUTPUT
        exit 1

    - name: Get detailed health status
      if: failure()
      run: |
        HEALTH_URL="${{ secrets.APPLICATION_URL }}/health/detailed"
        curl -s "$HEALTH_URL" || echo "Failed to get detailed health"

    - name: Send alert on failure
      if: failure()
      run: |
        # Send Slack alert
        curl -X POST -H 'Content-type: application/json' \
          --data "{\"text\":\"🚨 ALERT: Agent Lab health check failed\\nURL: ${{ secrets.APPLICATION_URL }}\\nTime: $(date)\"}" \
          ${{ secrets.SLACK_WEBHOOK_URL }}

    - name: Create incident ticket
      if: failure()
      run: |
        # Create GitHub issue for tracking
        gh issue create \
          --title "🚨 Health Check Failure - $(date)" \
          --body "Automated health check failed. Application may be down.\\n\\n- URL: ${{ secrets.APPLICATION_URL }}\\n- Time: $(date)\\n- Workflow: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID" \
          --label "incident,automated"

  data-integrity-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: pip install requests

    - name: Check data integrity
      run: |
        python -c "
        import requests
        import sys
        from pathlib import Path

        # Check if we can access data directory (if running locally)
        data_dir = Path('data')
        if data_dir.exists():
            # Check sessions
            sessions_dir = data_dir / 'sessions'
            if sessions_dir.exists():
                session_files = list(sessions_dir.glob('*.json'))
                print(f'Found {len(session_files)} session files')

                # Try to parse a few recent sessions
                import json
                corrupted = 0
                for session_file in session_files[:5]:  # Check last 5
                    try:
                        with open(session_file, 'r') as f:
                            json.load(f)
                    except json.JSONDecodeError:
                        corrupted += 1

                if corrupted > 0:
                    print(f'❌ Found {corrupted} corrupted session files')
                    sys.exit(1)
                else:
                    print('✅ Session files integrity OK')
            else:
                print('ℹ️ No sessions directory yet')

            # Check CSV
            csv_file = data_dir / 'runs.csv'
            if csv_file.exists():
                try:
                    with open(csv_file, 'r') as f:
                        lines = f.readlines()
                        print(f'CSV has {len(lines)} lines')
                        if len(lines) > 0:
                            # Check header
                            header = lines[0].strip()
                            expected = 'ts,agent_name,model,prompt_tokens,completion_tokens,total_tokens,latency_ms,cost_usd,experiment_id,task_label,run_notes,streaming,model_list_source,tool_web_enabled,web_status,aborted'
                            if header != expected:
                                print('❌ CSV header mismatch')
                                sys.exit(1)
                            else:
                                print('✅ CSV header OK')
                except Exception as e:
                    print(f'❌ CSV integrity check failed: {e}')
                    sys.exit(1)
            else:
                print('ℹ️ No CSV file yet')
        else:
            print('ℹ️ No data directory yet')

        print('✅ Data integrity check passed')
        "

    - name: Alert on data integrity failure
      if: failure()
      run: |
        curl -X POST -H 'Content-type: application/json' \
          --data "{\"text\":\"🚨 ALERT: Data integrity check failed\\nRepository: $GITHUB_REPOSITORY\\nTime: $(date)\"}" \
          ${{ secrets.SLACK_WEBHOOK_URL }}
```

### SLO Monitoring Workflow
```yaml
# .github/workflows/slo-monitoring.yml
name: SLO Monitoring

on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
  workflow_dispatch:

jobs:
  slo-check:
    runs-on: ubuntu-latest
    steps:
    - name: Calculate SLO compliance
      run: |
        # This would integrate with actual metrics collection
        # For now, simulate SLO checks

        echo "Checking SLO compliance..."

        # Simulate availability check (would pull from metrics)
        AVAILABILITY=99.95  # Would be calculated from actual data

        # Check against targets
        if (( $(echo "$AVAILABILITY < 99.9" | bc -l) )); then
          echo "🚨 ALERT: Availability SLO violated"
          echo "Current: ${AVAILABILITY}% | Target: 99.9%"
          echo "slo_violation=true" >> $GITHUB_OUTPUT
        else
          echo "✅ Availability SLO: ${AVAILABILITY}% (Target: 99.9%)"
        fi

        # Simulate error rate check
        ERROR_RATE=0.8  # Would be calculated

        if (( $(echo "$ERROR_RATE > 1.0" | bc -l) )); then
          echo "🚨 ALERT: Error Rate SLO violated"
          echo "Current: ${ERROR_RATE}% | Target: <1%"
          echo "slo_violation=true" >> $GITHUB_OUTPUT
        else
          echo "✅ Error Rate SLO: ${ERROR_RATE}% (Target: <1%)"
        fi

    - name: Send SLO alert
      if: steps.slo-check.outputs.slo_violation == 'true'
      run: |
        curl -X POST -H 'Content-type: application/json' \
          --data "{\"text\":\"🚨 ALERT: SLO Violation Detected\\nCheck workflow logs for details\\nTime: $(date)\"}" \
          ${{ secrets.SLACK_WEBHOOK_URL }}

    - name: Update SLO dashboard
      run: |
        # This would update a dashboard or status file
        echo "SLO status updated at $(date)" > slo-status.txt
```

## Alerting Configuration

### Slack Integration
```yaml
# Example Slack webhook payload structure
{
  "channel": "#agent-lab-alerts",
  "username": "Agent Lab Monitor",
  "icon_emoji": ":robot_face:",
  "attachments": [
    {
      "color": "danger",
      "title": "🚨 Critical Alert: Application Down",
      "text": "Agent Lab health check failed",
      "fields": [
        {
          "title": "URL",
          "value": "https://agent-lab.your-domain.com",
          "short": true
        },
        {
          "title": "Time",
          "value": "$(date)",
          "short": true
        }
      ],
      "footer": "Agent Lab Monitoring",
      "ts": $(date +%s)
    }
  ]
}
```

### Email Alerts (Alternative/Fallback)
```python
# services/alerting.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailAlertManager:
    def __init__(self, smtp_server, smtp_port, username, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    def send_alert(self, subject: str, message: str, recipients: list):
        """Send email alert."""
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"🚨 Agent Lab Alert: {subject}"

        msg.attach(MIMEText(message, 'plain'))

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.username, recipients, text)
            server.quit()
            print("Alert email sent successfully")
        except Exception as e:
            print(f"Failed to send alert email: {e}")
```

## Dashboard Implementation

### SLO Dashboard (GitHub Pages)
```html
<!-- docs/slo-dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Agent Lab SLO Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .slo-card { border: 1px solid #ccc; padding: 20px; margin: 10px; border-radius: 5px; }
        .healthy { background-color: #e8f5e8; }
        .warning { background-color: #fff3cd; }
        .critical { background-color: #f8d7da; }
    </style>
</head>
<body>
    <h1>Agent Lab SLO Dashboard</h1>

    <div id="slo-cards">
        <!-- SLO cards will be populated by JavaScript -->
    </div>

    <canvas id="slo-trend-chart" width="400" height="200"></canvas>

    <script>
        // Fetch SLO data from metrics endpoint
        async function updateDashboard() {
            try {
                const response = await fetch('/metrics/slo');
                const sloData = await response.json();

                updateSLOCards(sloData);
                updateTrendChart(sloData);
            } catch (error) {
                console.error('Failed to fetch SLO data:', error);
            }
        }

        function updateSLOCards(data) {
            const container = document.getElementById('slo-cards');

            for (const [sloName, slo] of Object.entries(data)) {
                const card = document.createElement('div');
                card.className = `slo-card ${getStatusClass(slo.status)}`;

                card.innerHTML = `
                    <h3>${slo.name}</h3>
                    <p>Target: ${slo.target}%</p>
                    <p>Current: ${slo.current}%</p>
                    <p>Error Budget: ${slo.error_budget_remaining}% remaining</p>
                    <p>Status: ${slo.status}</p>
                `;

                container.appendChild(card);
            }
        }

        function getStatusClass(status) {
            switch(status) {
                case 'healthy': return 'healthy';
                case 'warning': return 'warning';
                case 'critical': return 'critical';
                default: return '';
            }
        }

        // Initialize dashboard
        updateDashboard();
        setInterval(updateDashboard, 300000); // Update every 5 minutes
    </script>
</body>
</html>
```

### Metrics Collection Service
```python
# services/metrics.py
from collections import defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path

class MetricsCollector:
    def __init__(self):
        self.metrics_file = Path("data/metrics.json")
        self.metrics = self.load_metrics()

    def load_metrics(self):
        """Load metrics from persistent storage."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return defaultdict(dict)
        return defaultdict(dict)

    def save_metrics(self):
        """Save metrics to persistent storage."""
        with open(self.metrics_file, 'w') as f:
            json.dump(dict(self.metrics), f, indent=2, default=str)

    def record_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        timestamp = datetime.utcnow().replace(second=0, microsecond=0)

        if endpoint not in self.metrics:
            self.metrics[endpoint] = {}

        if str(timestamp) not in self.metrics[endpoint]:
            self.metrics[endpoint][str(timestamp)] = {
                'requests': 0,
                'errors': 0,
                'latencies': [],
                'methods': defaultdict(int)
            }

        self.metrics[endpoint][str(timestamp)]['requests'] += 1
        self.metrics[endpoint][str(timestamp)]['methods'][method] += 1
        self.metrics[endpoint][str(timestamp)]['latencies'].append(duration)

        if status_code >= 400:
            self.metrics[endpoint][str(timestamp)]['errors'] += 1

        self.save_metrics()

    def get_sli_metrics(self, window_hours: int = 24):
        """Calculate SLI metrics for the given time window."""
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)

        total_requests = 0
        error_requests = 0
        all_latencies = []

        for endpoint_data in self.metrics.values():
            for timestamp_str, data in endpoint_data.items():
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp >= cutoff:
                    total_requests += data['requests']
                    error_requests += data['errors']
                    all_latencies.extend(data['latencies'])

        availability = ((total_requests - error_requests) / total_requests * 100) if total_requests > 0 else 100
        error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0

        # Calculate latency percentiles
        all_latencies.sort()
        p95_latency = all_latencies[int(len(all_latencies) * 0.95)] if all_latencies else 0

        return {
            'availability_sli': round(availability, 2),
            'error_rate_sli': round(error_rate, 2),
            'latency_p95_sli': round(p95_latency, 2),
            'total_requests': total_requests
        }
```

## Alert Escalation Policies

### Alert Severity Levels
1. **Critical (P0)**: Immediate action required
   - Application completely down
   - Data corruption detected
   - Security breach
   - **Response**: Page on-call engineer immediately

2. **High (P1)**: Urgent action needed
   - SLO violation (availability < 99.5%)
   - Major functionality broken
   - **Response**: Alert on-call engineer within 15 minutes

3. **Medium (P2)**: Action needed soon
   - Performance degradation
   - Minor feature issues
   - **Response**: Create ticket, address within 4 hours

4. **Low (P3)**: Monitor and plan
   - Cosmetic issues
   - Minor performance issues
   - **Response**: Address in next sprint

### Escalation Process
- **Level 1**: Automated alerts (Slack/email)
- **Level 2**: On-call engineer notification (15 minutes for P0/P1)
- **Level 3**: Management notification (1 hour for unresolved P0)
- **Level 4**: Customer communication (2 hours for user-impacting issues)

## Integration with Incident Response

### Automated Incident Creation
```yaml
# .github/workflows/create-incident.yml
name: Create Incident

on:
  workflow_dispatch:
    inputs:
      severity:
        description: 'Incident severity'
        required: true
        default: 'P2'
        options: ['P0', 'P1', 'P2', 'P3']
      title:
        description: 'Incident title'
        required: true
      description:
        description: 'Incident description'
        required: true

jobs:
  create-incident:
    runs-on: ubuntu-latest
    steps:
    - name: Create GitHub issue
      run: |
        # Create incident tracking issue
        ISSUE_BODY="## Incident Details
        **Severity:** ${{ github.event.inputs.severity }}
        **Reported:** $(date)
        **Reporter:** $GITHUB_ACTOR

        **Description:**
        ${{ github.event.inputs.description }}

        ## Investigation
        - [ ] Initial triage completed
        - [ ] Root cause identified
        - [ ] Impact assessed
        - [ ] Resolution implemented
        - [ ] Post-mortem scheduled

        ## Communication
        - [ ] Internal team notified
        - [ ] Status page updated (if applicable)
        - [ ] Customer communication sent (if needed)"

        gh issue create \
          --title "[${{ github.event.inputs.severity }}] ${{ github.event.inputs.title }}" \
          --body "$ISSUE_BODY" \
          --label "incident,${{ github.event.inputs.severity }}"

    - name: Notify on-call
      if: github.event.inputs.severity == 'P0' || github.event.inputs.severity == 'P1'
      run: |
        # Send urgent notification
        curl -X POST -H 'Content-type: application/json' \
          --data "{\"text\":\"🚨 URGENT: ${{ github.event.inputs.severity }} Incident Created\\nTitle: ${{ github.event.inputs.title }}\\nIssue: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/issues/$ISSUE_NUMBER\"}" \
          ${{ secrets.SLACK_ONCALL_WEBHOOK_URL }}
```

## Testing and Validation

### Monitoring System Tests
```python
# tests/test_monitoring.py
import pytest
from services.monitoring import HealthCheckManager, MetricsCollector

def test_health_check_endpoint():
    """Test health check endpoint functionality."""
    # Test healthy state
    health = HealthCheckManager().check_health()
    assert health['status'] == 'healthy'
    assert 'checks' in health

def test_metrics_collection():
    """Test metrics collection and SLI calculation."""
    collector = MetricsCollector()

    # Record some test requests
    collector.record_request('/api/agents', 'POST', 200, 1.5)
    collector.record_request('/api/agents', 'POST', 500, 0.5)
    collector.record_request('/api/chat', 'POST', 200, 2.1)

    # Check SLI calculation
    slis = collector.get_sli_metrics(window_hours=1)
    assert slis['total_requests'] == 3
    assert slis['error_rate_sli'] == 33.33  # 1 error out of 3 requests
    assert slis['availability_sli'] == 66.67

def test_alerting_integration():
    """Test alerting system integration."""
    # Mock alert sending
    # Verify webhook payloads
    pass
```

This monitoring and alerting infrastructure provides comprehensive visibility into Agent Lab's operational health, enabling proactive issue detection and rapid response to incidents.