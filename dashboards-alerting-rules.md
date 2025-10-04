# Dashboards and Alerting Rules - Agent Lab

## Overview

This document defines the dashboards and alerting rules for monitoring Agent Lab's reliability, performance, and operational health. It includes real-time dashboards, alert configurations, and escalation procedures.

## Dashboard Architecture

### Dashboard Types
1. **Executive Dashboard**: High-level business metrics and SLO status
2. **Operations Dashboard**: Real-time system health and alerts
3. **Development Dashboard**: CI/CD and release health
4. **Incident Dashboard**: Active incident tracking and response

### Dashboard Implementation
Dashboards are implemented using:
- **GitHub Pages**: Static HTML/CSS/JS dashboards
- **Real-time Updates**: JavaScript polling metrics endpoints
- **Mobile Responsive**: Accessible on all devices
- **Accessible**: WCAG compliant color schemes and navigation

## Executive Dashboard

### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Agent Lab - Executive Overview                    [Refresh] │
├─────────────────────────────────────────────────────────────┤
│ SLO Status                    │ Error Budget Status         │
│ ┌─────────────────────────┐   │ ┌─────────────────────────┐ │
│ │ ✅ Availability 99.95% │   │ │ 🟢 87% Remaining       │ │
│ │ ✅ Error Rate 0.8%     │   │ │ Budget: 43.8 min/month │ │
│ │ ✅ Latency 96% <2s     │   │ │ Zone: Green            │ │
│ │ ✅ Streaming 99.2%     │   │ └─────────────────────────┘ │
│ └─────────────────────────┘   │                            │
│                               │ Incident Summary           │
│ Key Metrics                   │ ┌─────────────────────────┐ │
│ ┌─────────────────────────┐   │ │ Active: 0              │ │
│ │ Users: 1,234           │   │ │ This Week: 2           │ │
│ │ Sessions: 5,678        │   │ │ MTTR: 45 min          │ │
│ │ API Calls: 45,678      │   │ └─────────────────────────┘ │
│ │ Uptime: 99.95%         │   │                            │
│ └─────────────────────────┘   └────────────────────────────┘
├─────────────────────────────────────────────────────────────┤
│ System Health Trend (24h)                                  │
│ [Line chart: Availability, Error Rate, Latency over time]   │
└─────────────────────────────────────────────────────────────┘
```

### Key Metrics Displayed
- **SLO Status**: Real-time compliance indicators
- **Error Budget**: Remaining budget and consumption rate
- **Incident Summary**: Active incidents and recent history
- **Business Metrics**: User counts, session volumes
- **System Health**: Overall availability and performance

### Refresh Rate
- **Real-time**: SLO status and active alerts
- **5-minute**: Error budget calculations
- **15-minute**: Trend data and historical metrics

## Operations Dashboard

### System Health Panel
```html
<div class="health-panel">
  <h3>System Components</h3>
  <div class="component-status">
    <div class="component" data-status="healthy">
      <span class="indicator">🟢</span>
      <span class="name">Application</span>
      <span class="metric">99.9% uptime</span>
    </div>
    <div class="component" data-status="healthy">
      <span class="indicator">🟢</span>
      <span class="name">OpenRouter API</span>
      <span class="metric">99.5% success</span>
    </div>
    <div class="component" data-status="warning">
      <span class="indicator">🟡</span>
      <span class="name">Data Storage</span>
      <span class="metric">95.2% integrity</span>
    </div>
  </div>
</div>
```

### Performance Metrics Panel
```
┌─ Performance Metrics ──────────────────────────────┐
│ Response Time Distribution                        │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 95% < 500ms          │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░ 99% < 1s             │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░ 99.9% < 2s           │
│                                                   │
│ Throughput: 1,234 req/min                        │
│ Error Rate: 0.8%                                  │
│ Active Users: 89                                  │
└───────────────────────────────────────────────────┘
```

### Alert Status Panel
```
┌─ Active Alerts ───────────────────────────────────┐
│ 🔴 CRITICAL: Application down (server-01)        │
│     Started: 5 min ago                            │
│     Impact: All users                             │
│     [Acknowledge] [Escalate]                      │
│                                                   │
│ 🟡 WARNING: High error rate (12% > 1%)           │
│     Started: 15 min ago                           │
│     Impact: 25% of requests                       │
│     [Acknowledge]                                 │
│                                                   │
│ 🟢 RESOLVED: Latency spike (resolved 2h ago)     │
│     Duration: 45 minutes                          │
└───────────────────────────────────────────────────┘
```

## Alerting Rules

### Alert Severity Levels

#### Critical (P0) - Immediate Action Required
**Response Time**: Acknowledge within 5 minutes, resolve within 1 hour
**Escalation**: Page on-call engineer, notify management

#### High (P1) - Urgent Action Needed
**Response Time**: Acknowledge within 15 minutes, resolve within 4 hours
**Escalation**: Alert on-call engineer

#### Medium (P2) - Action Needed Soon
**Response Time**: Acknowledge within 1 hour, resolve within 1 day
**Escalation**: Create ticket, assign to team

#### Low (P3) - Monitor and Plan
**Response Time**: Acknowledge within 1 day, resolve within 1 week
**Escalation**: Add to backlog

### Specific Alert Rules

#### 1. Application Availability Alert
```yaml
alert: ApplicationDown
expr: up{job="agent-lab"} == 0
for: 5m
labels:
  severity: critical
  service: agent-lab
annotations:
  summary: "Application is down"
  description: "Agent Lab application has been down for 5+ minutes"
  runbook_url: "https://agent-lab.your-domain.com/runbooks/application-down"
```

**Thresholds**:
- **Critical**: 100% downtime for 5+ minutes
- **Warning**: 99% availability (any sustained outage)

**Actions**:
1. Auto-create incident ticket
2. Send Slack alert to #incidents
3. Page on-call engineer
4. Start incident response process

#### 2. SLO Violation Alert
```yaml
alert: SLOViolation
expr: slo_error_budget_remaining_percentage < 10
for: 5m
labels:
  severity: high
  slo: "{{ $labels.slo }}"
annotations:
  summary: "SLO violation: {{ $labels.slo }}"
  description: "Error budget for {{ $labels.slo }} is below 10% ({{ $value }}% remaining)"
  dashboard_url: "https://agent-lab.your-domain.com/dashboards/slo"
```

**Per-SLO Thresholds**:
- **Availability**: Alert when < 10% budget remaining
- **Error Rate**: Alert when > 1.5% (150% of budget)
- **Latency**: Alert when > 10% of requests exceed target
- **Data Integrity**: Alert when > 0.02% operations fail

#### 3. Error Rate Spike Alert
```yaml
alert: ErrorRateSpike
expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
for: 2m
labels:
  severity: high
annotations:
  summary: "High error rate detected"
  description: "Error rate is {{ $value | humanizePercentage }} over last 5 minutes"
```

**Thresholds**:
- **Critical**: > 20% error rate for 2+ minutes
- **High**: > 5% error rate for 2+ minutes
- **Warning**: > 1% error rate for 5+ minutes

#### 4. Latency Degradation Alert
```yaml
alert: LatencyDegradation
expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
for: 5m
labels:
  severity: medium
annotations:
  summary: "High latency detected"
  description: "95th percentile latency is {{ $value }}s (target: <2s)"
```

**Thresholds**:
- **Critical**: 95th percentile > 30 seconds
- **High**: 95th percentile > 5 seconds
- **Warning**: 95th percentile > 2 seconds

#### 5. Data Integrity Alert
```yaml
alert: DataIntegrityFailure
expr: rate(data_operation_failures_total[5m]) / rate(data_operations_total[5m]) > 0.0001
for: 5m
labels:
  severity: high
annotations:
  summary: "Data integrity issues detected"
  description: "Data operation failure rate is {{ $value | humanizePercentage }}"
```

**Thresholds**:
- **Critical**: > 0.1% failure rate
- **High**: > 0.01% failure rate
- **Warning**: > 0.001% failure rate

#### 6. Resource Exhaustion Alert
```yaml
alert: ResourceExhaustion
expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.9
for: 5m
labels:
  severity: high
annotations:
  summary: "High resource usage"
  description: "Memory usage is {{ $value | humanizePercentage }} on {{ $labels.instance }}"
```

**Resource Thresholds**:
- **Memory**: > 90% usage
- **CPU**: > 95% usage sustained
- **Disk**: > 85% usage
- **Network**: > 80% saturation

#### 7. External Dependency Alert
```yaml
alert: ExternalDependencyFailure
expr: probe_success{job="openrouter-api"} == 0
for: 2m
labels:
  severity: high
annotations:
  summary: "External dependency failure"
  description: "OpenRouter API is unreachable"
```

#### 8. Backup Failure Alert
```yaml
alert: BackupFailure
expr: backup_success == 0
for: 1h
labels:
  severity: medium
annotations:
  summary: "Backup failure"
  description: "Automated backup failed for {{ $labels.backup_type }}"
```

### Alert Grouping and Routing

#### Alert Groups
```yaml
# Group related alerts to reduce noise
groups:
  - name: agent-lab.rules
    rules:
    - alert: ApplicationDown
      expr: up{job="agent-lab"} == 0
      for: 5m
      labels:
        team: sre
        severity: critical

    - alert: SLOViolation
      expr: slo_error_budget_remaining_percentage{slo="availability"} < 10
      for: 5m
      labels:
        team: sre
        severity: high

# Route alerts to appropriate channels
route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'slack-notifications'

  routes:
  - match:
      severity: critical
    receiver: 'pager-duty'
    continue: true

  - match:
      team: sre
    receiver: 'sre-slack'
```

### Notification Channels

#### Slack Notifications
```json
{
  "channel": "#agent-lab-alerts",
  "username": "Agent Lab Monitor",
  "icon_emoji": ":robot_face:",
  "attachments": [
    {
      "color": "{{ .StatusColor }}",
      "title": "{{ .GroupLabels.alertname }}",
      "text": "{{ .CommonAnnotations.description }}",
      "fields": [
        {
          "title": "Severity",
          "value": "{{ .GroupLabels.severity }}",
          "short": true
        },
        {
          "title": "Service",
          "value": "{{ .GroupLabels.service }}",
          "short": true
        }
      ],
      "footer": "Agent Lab Monitoring",
      "ts": "{{ .StartsAt.Unix }}"
    }
  ]
}
```

#### PagerDuty Integration
- **Critical Alerts**: Immediate page to on-call engineer
- **High Alerts**: Phone call after 5 minutes if unacknowledged
- **Escalation**: Management notification after 15 minutes

#### Email Notifications
- **Daily Digest**: Summary of all alerts from previous day
- **Weekly Report**: Alert trends and patterns
- **Monthly Review**: Alert effectiveness and false positive analysis

## Dashboard Implementation Details

### Real-time Updates
```javascript
class DashboardUpdater {
  constructor() {
    this.updateInterval = 30000; // 30 seconds
    this.metricsEndpoint = '/metrics';
    this.sloEndpoint = '/metrics/slo';
  }

  async update() {
    try {
      const [metrics, sloData] = await Promise.all([
        fetch(this.metricsEndpoint).then(r => r.json()),
        fetch(this.sloEndpoint).then(r => r.json())
      ]);

      this.updateSLIStatus(sloData);
      this.updateErrorBudget(metrics);
      this.updateAlerts(metrics);
      this.updateCharts(metrics);

    } catch (error) {
      console.error('Dashboard update failed:', error);
      this.showError('Failed to update dashboard');
    }
  }

  updateSLIStatus(data) {
    // Update SLO status indicators
    Object.entries(data).forEach(([sloName, slo]) => {
      const element = document.getElementById(`${sloName}-status`);
      element.className = this.getStatusClass(slo.status);
      element.textContent = `${slo.current}%`;
    });
  }

  getStatusClass(status) {
    switch(status) {
      case 'healthy': return 'status-healthy';
      case 'warning': return 'status-warning';
      case 'critical': return 'status-critical';
      default: return 'status-unknown';
    }
  }
}

// Initialize dashboard
const dashboard = new DashboardUpdater();
dashboard.update();
setInterval(() => dashboard.update(), dashboard.updateInterval);
```

### Historical Data Visualization
```javascript
class MetricsChart {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.chart = new Chart(this.canvas, {
      type: 'line',
      data: {
        datasets: [{
          label: 'Availability %',
          data: [],
          borderColor: 'rgb(75, 192, 192)',
          tension: 0.1
        }]
      },
      options: {
        responsive: true,
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'hour'
            }
          },
          y: {
            beginAtZero: true,
            max: 100
          }
        }
      }
    });
  }

  updateData(newData) {
    this.chart.data.datasets[0].data = newData;
    this.chart.update();
  }
}
```

### Alert Management Interface
```html
<div class="alert-manager">
  <div class="alert-filters">
    <button class="filter active" data-severity="all">All</button>
    <button class="filter" data-severity="critical">Critical</button>
    <button class="filter" data-severity="high">High</button>
    <button class="filter" data-severity="medium">Medium</button>
  </div>

  <div class="alert-list">
    <!-- Dynamic alert items -->
  </div>

  <div class="alert-actions">
    <button id="acknowledge-selected">Acknowledge Selected</button>
    <button id="escalate-selected">Escalate Selected</button>
    <button id="create-incident">Create Incident</button>
  </div>
</div>
```

## Alert Effectiveness Monitoring

### Alert Quality Metrics
- **True Positive Rate**: Percentage of alerts that indicate real issues
- **False Positive Rate**: Percentage of alerts that are incorrect
- **Mean Time to Acknowledge**: Average time to acknowledge alerts
- **Alert Volume**: Number of alerts per day/week

### Continuous Improvement
```yaml
# .github/workflows/alert-quality-review.yml
name: Alert Quality Review

on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly on Monday
  workflow_dispatch:

jobs:
  review-alerts:
    runs-on: ubuntu-latest
    steps:
    - name: Analyze alert patterns
      run: |
        # Fetch alert data from monitoring system
        # Calculate quality metrics
        # Generate improvement recommendations

    - name: Generate report
      run: |
        cat > alert-quality-report.md << 'EOF'
        # Weekly Alert Quality Report

        ## Metrics Summary
        - True Positive Rate: 94%
        - False Positive Rate: 6%
        - Average MTTA: 12 minutes
        - Total Alerts: 47

        ## Top False Positives
        1. Resource usage alerts (3 instances)
        2. Temporary network issues (2 instances)

        ## Recommendations
        - Adjust resource alert thresholds
        - Implement alert correlation
        - Add alert suppression for known maintenance windows
        EOF

    - name: Send report
      run: |
        # Send to Slack or email
```

## Maintenance and Testing

### Alert Test Procedures
```bash
# Test alert delivery
curl -X POST https://alertmanager.example.com/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{"labels": {"alertname": "TestAlert", "severity": "info"}, "annotations": {"summary": "Test alert"}}]'

# Test dashboard updates
curl https://agent-lab.your-domain.com/metrics/test

# Validate alert rules
promtool check rules alert-rules.yml
```

### Maintenance Windows
- **Alert Suppression**: Automatically suppress alerts during planned maintenance
- **Testing Windows**: Designated times for alert testing
- **Review Periods**: Regular review and tuning of alert rules

This comprehensive alerting and dashboard system ensures Agent Lab's reliability team has complete visibility into system health and can respond quickly to issues.