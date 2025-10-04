# Service Level Indicators (SLI) and Objectives (SLO) Framework - Agent Lab

## Overview

This document defines the Service Level Indicators (SLIs) and Service Level Objectives (SLOs) for the Agent Lab application. SLIs measure the reliability and performance of the service, while SLOs set quantitative targets for these measurements. Error budgets are calculated based on SLOs to guide development and operational decisions.

## Service Architecture Context

Agent Lab is a Gradio-based web application that:
- Provides a UI for configuring and running AI agents
- Streams responses from OpenRouter API
- Persists user sessions and telemetry data
- Runs on GitHub Actions for CI/CD

## Core SLIs and SLOs

### 1. Availability SLI/SLO

**SLI: Application Availability**
- **Definition**: Percentage of time the application is accessible and functional
- **Measurement**: HTTP 200 responses to health check endpoint over 5-minute windows
- **Implementation**:
  ```python
  # app.py - Health check endpoint
  @app.get("/health")
  def health_check():
      # Check core dependencies
      try:
          # Test OpenRouter API connectivity
          # Test data directory access
          # Test CSV file integrity
          return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
      except Exception as e:
          return {"status": "unhealthy", "error": str(e)}, 500
  ```

**SLO Target**: 99.9% availability (8.77 hours downtime per year)
- **Measurement Window**: Rolling 30 days
- **Error Budget**: 0.1% (43.8 minutes per month)

### 2. Latency SLI/SLO

**SLI: Response Time**
- **Definition**: Time from user request to initial response (TTFB - Time To First Byte)
- **Measurement**: 95th percentile response time for agent creation and chat requests
- **Buckets**: [0.1s, 0.5s, 1s, 2s, 5s, 10s, 30s]

**SLO Targets**:
- Agent Creation: 95% of requests < 2 seconds
- Chat Streaming Start: 95% of requests < 5 seconds
- Model Catalog Fetch: 95% of requests < 10 seconds

**Error Budget**: 5% of requests can exceed latency targets per month

### 3. Error Rate SLI/SLO

**SLI: Request Error Rate**
- **Definition**: Percentage of requests that result in 5xx errors
- **Measurement**: HTTP 5xx responses / total requests over 5-minute windows
- **Scope**: All API endpoints and UI interactions

**SLO Target**: < 1% error rate (99% success rate)
- **Measurement Window**: Rolling 7 days
- **Error Budget**: 1% of requests can fail per week

**SLI: Functional Errors**
- **Definition**: Requests that return 200 but fail to complete intended function
- **Measurement**: Agent runs that fail due to tool errors, streaming interruptions, or data corruption
- **SLO Target**: < 2% functional error rate

### 4. Data Integrity SLI/SLO

**SLI: Session Persistence Success**
- **Definition**: Percentage of user sessions that save/load successfully
- **Measurement**: Successful JSON parse operations / total save/load attempts

**SLO Target**: 99.99% session persistence success
- **Error Budget**: 0.01% of sessions can fail to persist

**SLI: Telemetry Data Integrity**
- **Definition**: Percentage of telemetry records written without corruption
- **Measurement**: Valid CSV rows / total rows written
- **SLO Target**: 99.999% data integrity

### 5. Streaming Performance SLI/SLO

**SLI: Streaming Continuity**
- **Definition**: Percentage of streaming responses that complete without interruption
- **Measurement**: Completed streams / total streams started

**SLO Target**: 99% streaming completion rate
- **Error Budget**: 1% of streams can fail per month

**SLI: Streaming Latency**
- **Definition**: Time between streaming chunks
- **Measurement**: 95th percentile inter-chunk delay
- **SLO Target**: < 500ms inter-chunk latency

## SLI Measurement Implementation

### Health Check Monitoring
```python
# services/monitoring.py
import time
import requests
from datetime import datetime, timedelta

class SLIMonitor:
    def __init__(self):
        self.metrics = {}

    def record_request(self, endpoint: str, status_code: int, duration: float):
        """Record request metrics for SLI calculation."""
        window = datetime.utcnow().replace(second=0, microsecond=0)

        if endpoint not in self.metrics:
            self.metrics[endpoint] = {}

        if window not in self.metrics[endpoint]:
            self.metrics[endpoint][window] = {
                'total_requests': 0,
                'error_requests': 0,
                'latencies': [],
                'last_updated': datetime.utcnow()
            }

        self.metrics[endpoint][window]['total_requests'] += 1
        self.metrics[endpoint][window]['latencies'].append(duration)

        if status_code >= 500:
            self.metrics[endpoint][window]['error_requests'] += 1

    def calculate_availability_sli(self, endpoint: str, window_minutes: int = 5) -> float:
        """Calculate availability SLI for given time window."""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)

        total_requests = 0
        successful_requests = 0

        for timestamp, data in self.metrics.get(endpoint, {}).items():
            if timestamp >= window_start:
                total_requests += data['total_requests']
                successful_requests += data['total_requests'] - data['error_requests']

        return (successful_requests / total_requests * 100) if total_requests > 0 else 100.0

    def calculate_latency_sli(self, endpoint: str, percentile: float = 95.0) -> float:
        """Calculate latency SLI (95th percentile)."""
        all_latencies = []
        for data in self.metrics.get(endpoint, {}).values():
            all_latencies.extend(data['latencies'])

        if not all_latencies:
            return 0.0

        all_latencies.sort()
        index = int(len(all_latencies) * percentile / 100)
        return all_latencies[min(index, len(all_latencies) - 1)]
```

### Integration with Application
```python
# app.py - SLI tracking middleware
@app.middleware("http")
async def track_sli_metrics(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    sli_monitor.record_request(
        endpoint=request.url.path,
        status_code=response.status_code,
        duration=duration
    )

    return response
```

## SLO Compliance and Error Budgets

### Error Budget Calculation
```python
# services/slo.py
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class SLO:
    name: str
    target_percentage: float  # e.g., 99.9 for 99.9%
    measurement_window_days: int
    current_sli_percentage: float = 0.0
    last_updated: datetime = None

    @property
    def error_budget_percentage(self) -> float:
        """Remaining error budget as percentage."""
        return 100.0 - self.target_percentage

    @property
    def error_budget_remaining(self) -> float:
        """Calculate remaining error budget based on current performance."""
        if self.current_sli_percentage >= self.target_percentage:
            return self.error_budget_percentage
        return max(0, self.error_budget_percentage - (self.target_percentage - self.current_sli_percentage))

class SLOTracker:
    def __init__(self):
        self.slos = {
            'availability': SLO('Application Availability', 99.9, 30),
            'latency_agent_creation': SLO('Agent Creation Latency', 95.0, 7),  # 95% < 2s
            'latency_chat_start': SLO('Chat Start Latency', 95.0, 7),  # 95% < 5s
            'error_rate': SLO('Request Error Rate', 99.0, 7),  # < 1% errors
            'streaming_continuity': SLO('Streaming Continuity', 99.0, 30),
            'data_integrity': SLO('Data Integrity', 99.99, 30),
        }

    def update_sli(self, slo_name: str, sli_value: float):
        """Update SLI measurement and recalculate error budget."""
        if slo_name in self.slos:
            slo = self.slos[slo_name]
            slo.current_sli_percentage = sli_value
            slo.last_updated = datetime.utcnow()

    def get_error_budget_status(self) -> dict:
        """Return current error budget status for all SLOs."""
        return {
            name: {
                'target': slo.target_percentage,
                'current': slo.current_sli_percentage,
                'error_budget_remaining': slo.error_budget_remaining,
                'status': 'healthy' if slo.error_budget_remaining > 0 else 'exceeded'
            }
            for name, slo in self.slos.items()
        }
```

### Error Budget Policy
- **Green Zone**: Error budget > 50% remaining - Normal development velocity
- **Yellow Zone**: Error budget 10-50% remaining - Increased monitoring, consider slowing feature releases
- **Red Zone**: Error budget < 10% remaining - Stop non-critical releases, focus on reliability improvements

## Monitoring and Alerting Integration

### SLO-Based Alerting Rules
```yaml
# .github/workflows/slo-monitoring.yml
name: SLO Monitoring

on:
  schedule:
    - cron: '*/5 * * * *'  # Every 5 minutes
  workflow_dispatch:

jobs:
  monitor-slos:
    runs-on: ubuntu-latest
    steps:
    - name: Check SLO compliance
      run: |
        # Calculate current SLI values
        AVAILABILITY=$(curl -s https://agent-lab.your-domain.com/metrics | jq '.availability_sli')
        ERROR_RATE=$(curl -s https://agent-lab.your-domain.com/metrics | jq '.error_rate_sli')

        # Check error budgets
        if (( $(echo "$AVAILABILITY < 99.9" | bc -l) )); then
          echo "🚨 ALERT: Availability SLO violated - $AVAILABILITY%"
          # Trigger alert
        fi

        if (( $(echo "$ERROR_RATE > 1.0" | bc -l) )); then
          echo "🚨 ALERT: Error Rate SLO violated - $ERROR_RATE%"
          # Trigger alert
        fi
```

## Dashboard and Reporting

### SLO Dashboard
- **Real-time SLI Values**: Current availability, latency, error rates
- **Error Budget Burn Rate**: Daily/weekly consumption of error budget
- **Historical Trends**: 30-day rolling averages
- **Incident Correlation**: SLO violations aligned with incidents

### Weekly SLO Report
```markdown
# Weekly SLO Report - Week of [Date]

## SLO Status Summary
| SLO | Target | Current | Error Budget | Status |
|-----|--------|---------|--------------|--------|
| Availability | 99.9% | 99.95% | 87% remaining | ✅ |
| Error Rate | <1% | 0.8% | 20% remaining | ⚠️ |
| Latency (Agent) | 95%<2s | 96% | 80% remaining | ✅ |

## Key Insights
- Availability improved by 0.1% due to infrastructure optimizations
- Error rate increase due to [specific incident]
- Error budget for [SLO] is at risk - consider reliability improvements

## Action Items
- [ ] Investigate error rate increase
- [ ] Plan reliability improvements if budget continues to burn
- [ ] Update monitoring thresholds based on learnings
```

## Error Budget Governance

### Development Guidelines
1. **Feature Development**: Monitor error budget consumption during development
2. **Testing**: Include SLO validation in CI/CD pipelines
3. **Rollbacks**: Automatic rollback triggers when SLOs are violated
4. **Blame-Free Culture**: Error budgets encourage learning from failures

### Operational Procedures
1. **Daily Checks**: Review SLO dashboard and error budget status
2. **Incident Response**: SLO violations trigger incident response procedures
3. **Capacity Planning**: Monitor error budget trends to plan infrastructure scaling
4. **Communication**: Regular updates to stakeholders on SLO performance

## Continuous Improvement

### SLO Review Process
- **Monthly Review**: Assess SLO targets vs. user needs and business requirements
- **Quarterly Adjustment**: Update SLO targets based on user feedback and system capabilities
- **Annual Calibration**: Major reviews of SLO framework effectiveness

### Metrics Evolution
- **New SLIs**: Add SLIs for new features or user journeys
- **Threshold Updates**: Adjust SLO targets based on performance improvements
- **Measurement Refinement**: Improve SLI accuracy and reduce measurement noise

This SLI/SLO framework provides quantitative measures of Agent Lab's reliability, enabling data-driven decisions about development priorities and operational improvements.