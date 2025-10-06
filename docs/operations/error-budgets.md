# Error Budgets and Reliability Governance - Agent Lab

## Overview

Error budgets quantify the acceptable level of system unreliability, providing a framework for balancing innovation with reliability. This document defines error budgets for Agent Lab, their calculation, monitoring, and governance processes.

## Error Budget Fundamentals

### Definition
An error budget is the maximum amount of time a service is allowed to be unavailable or degraded within a measurement period. It represents the acceptable risk tolerance for reliability vs. innovation trade-offs.

### Calculation
```
Error Budget = 100% - SLO Target
```

For example:
- SLO Target: 99.9% availability
- Error Budget: 0.1% (43.8 minutes per month)

### Budget Units
- **Time-based**: Minutes/hours of downtime
- **Percentage-based**: Percentage of requests that can fail
- **Event-based**: Number of incidents or errors allowed

## Agent Lab Error Budgets

### 1. Availability Error Budget

**SLO**: 99.9% availability (8.77 hours downtime per year)
**Measurement Window**: Rolling 30 days
**Error Budget**: 0.1% of time (43.8 minutes per month)

**Calculation**:
```
Monthly budget = 30 days × 24 hours × 60 minutes × 0.001 = 43.8 minutes
Annual budget = 365.25 days × 24 hours × 60 minutes × 0.001 = 525.96 minutes (8.77 hours)
```

**Budget Consumption Tracking**:
```python
class AvailabilityBudgetTracker:
    def __init__(self):
        self.slo_target = 99.9  # 99.9%
        self.measurement_window_days = 30

    def calculate_budget_consumed(self, actual_uptime_percentage: float) -> float:
        """Calculate percentage of error budget consumed."""
        if actual_uptime_percentage >= self.slo_target:
            return 0.0
        budget_used = self.slo_target - actual_uptime_percentage
        total_budget = 100.0 - self.slo_target
        return (budget_used / total_budget) * 100.0

    def get_remaining_budget_minutes(self, actual_uptime_percentage: float) -> float:
        """Get remaining error budget in minutes."""
        total_budget_minutes = self.measurement_window_days * 24 * 60 * (100.0 - self.slo_target) / 100.0
        consumed_percentage = self.calculate_budget_consumed(actual_uptime_percentage)
        return total_budget_minutes * (1 - consumed_percentage / 100.0)
```

### 2. Request Error Rate Budget

**SLO**: < 1% error rate
**Measurement Window**: Rolling 7 days
**Error Budget**: 1% of requests can fail per week

**Budget Tracking**:
```python
class ErrorRateBudgetTracker:
    def __init__(self):
        self.slo_target = 1.0  # 1% max error rate
        self.measurement_window_days = 7

    def calculate_budget_consumed(self, actual_error_rate: float) -> float:
        """Calculate error budget consumption."""
        if actual_error_rate <= self.slo_target:
            return 0.0
        budget_used = actual_error_rate - self.slo_target
        total_budget = self.slo_target  # Since SLO is "less than X", budget is X%
        return (budget_used / total_budget) * 100.0
```

### 3. Latency Error Budget

**SLO**: 95% of requests < 2 seconds (agent creation)
**Measurement Window**: Rolling 7 days
**Error Budget**: 5% of requests can exceed latency target

### 4. Streaming Continuity Budget

**SLO**: 99% streaming completion rate
**Measurement Window**: Rolling 30 days
**Error Budget**: 1% of streams can fail per month

### 5. Data Integrity Budget

**SLO**: 99.99% data persistence success
**Measurement Window**: Rolling 30 days
**Error Budget**: 0.01% of data operations can fail

## Error Budget Zones

### Green Zone (Healthy - > 50% Budget Remaining)
**Characteristics**:
- Normal development velocity
- Standard release processes
- Focus on feature development
- Reliability improvements as regular work

**Actions**:
- Continue normal development
- Monitor budget trends
- Plan reliability improvements
- Celebrate good reliability performance

### Yellow Zone (Warning - 10-50% Budget Remaining)
**Characteristics**:
- Increased monitoring attention
- Consider slowing feature releases
- Focus on reliability improvements
- Regular stakeholder communication

**Actions**:
- Increase monitoring frequency
- Review upcoming releases for risk
- Prioritize reliability over features
- Schedule reliability-focused sprint
- Daily error budget reviews

### Red Zone (Critical - < 10% Budget Remaining)
**Characteristics**:
- Stop non-critical releases
- Emergency reliability focus
- Intensive monitoring and response
- Stakeholder escalation

**Actions**:
- Halt feature development
- Focus all engineering on reliability
- Implement emergency measures
- Daily executive updates
- Consider rollback of recent changes

## Budget Governance Process

### Daily Monitoring
```yaml
# .github/workflows/error-budget-daily.yml
name: Error Budget Daily Review

on:
  schedule:
    - cron: '0 9 * * 1-5'  # 9 AM weekdays
  workflow_dispatch:

jobs:
  budget-review:
    runs-on: ubuntu-latest
    steps:
    - name: Calculate current error budgets
      run: |
        # Fetch current SLI values
        AVAILABILITY=$(curl -s https://agent-lab.your-domain.com/metrics/slo | jq '.availability_sli')
        ERROR_RATE=$(curl -s https://agent-lab.your-domain.com/metrics/slo | jq '.error_rate_sli')

        echo "Availability SLI: ${AVAILABILITY}%"
        echo "Error Rate SLI: ${ERROR_RATE}%"

        # Calculate budget consumption
        AVAILABILITY_BUDGET_CONSUMED=$(python3 -c "
        slo_target = 99.9
        actual = ${AVAILABILITY}
        if actual >= slo_target:
            print('0.0')
        else:
            budget_used = slo_target - actual
            total_budget = 100.0 - slo_target
            print(f'{(budget_used / total_budget) * 100:.1f}')
        ")

        echo "Availability budget consumed: ${AVAILABILITY_BUDGET_CONSUMED}%"

    - name: Determine budget zone
      run: |
        if (( $(echo "$AVAILABILITY_BUDGET_CONSUMED < 50" | bc -l) )); then
          echo "🟢 GREEN ZONE: Budget healthy"
          echo "budget_zone=green" >> $GITHUB_OUTPUT
        elif (( $(echo "$AVAILABILITY_BUDGET_CONSUMED < 90" | bc -l) )); then
          echo "🟡 YELLOW ZONE: Budget warning"
          echo "budget_zone=yellow" >> $GITHUB_OUTPUT
        else
          echo "🔴 RED ZONE: Budget critical"
          echo "budget_zone=red" >> $GITHUB_OUTPUT
        fi

    - name: Send zone-appropriate notifications
      if: steps.zone.outputs.budget_zone != 'green'
      run: |
        ZONE=${{ steps.zone.outputs.budget_zone }}

        if [ "$ZONE" = "yellow" ]; then
          MESSAGE="🟡 YELLOW ZONE: Error budget consumption is high. Consider focusing on reliability improvements."
        elif [ "$ZONE" = "red" ]; then
          MESSAGE="🔴 RED ZONE: Error budget nearly exhausted. Emergency reliability measures required."
        fi

        curl -X POST -H 'Content-type: application/json' \
          --data "{\"text\":\"$MESSAGE\\nBudget consumed: ${AVAILABILITY_BUDGET_CONSUMED}%\"}" \
          ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Weekly Budget Review
**Cadence**: Every Monday
**Attendees**: Engineering team, Product, SRE
**Agenda**:
1. Review budget consumption trends
2. Analyze incidents and their impact on budgets
3. Discuss upcoming releases and risk assessment
4. Plan reliability improvements
5. Update SLO targets if needed

**Template**:
```markdown
# Weekly Error Budget Review - Week of [Date]

## Budget Status Summary
| SLO | Target | Current | Budget Consumed | Zone | Trend |
|-----|--------|---------|-----------------|------|-------|
| Availability | 99.9% | 99.95% | 12% | 🟢 Green | ↗️ |
| Error Rate | <1% | 0.8% | 0% | 🟢 Green | → |
| Latency | 95%<2s | 96% | 0% | 🟢 Green | → |

## Key Incidents
- [Incident 1]: Impacted availability by 0.05%
- [Incident 2]: No budget impact

## Upcoming Releases
- [Release 1]: Low risk, proceed
- [Release 2]: High risk, additional testing required

## Action Items
- [ ] Implement reliability improvement for [component]
- [ ] Add monitoring for [new feature]
- [ ] Review SLO targets for [service]
```

### Monthly Budget Planning
**Cadence**: First Monday of month
**Attendees**: Engineering, Product, Leadership
**Focus**:
- Review long-term budget trends
- Plan reliability initiatives
- Adjust SLO targets based on business needs
- Budget for infrastructure improvements

## Error Budget Burn Rate Alerts

### Definition
Burn rate is the speed at which error budget is being consumed.

**Calculation**:
```
Burn Rate = (Budget Consumed) / (Time Period)
```

### Alert Thresholds
- **Slow Burn**: Consuming budget slower than planned (good)
- **Normal Burn**: Consuming budget at expected rate
- **Fast Burn**: Consuming budget faster than planned (bad)
- **Critical Burn**: Consuming budget very rapidly (emergency)

### Burn Rate Monitoring
```python
class BurnRateMonitor:
    def __init__(self):
        self.budget_history = []

    def calculate_burn_rate(self, current_budget_consumed: float, time_window_hours: int) -> float:
        """Calculate burn rate as percentage per hour."""
        if len(self.budget_history) < 2:
            return 0.0

        # Calculate change over time window
        recent = self.budget_history[-1]
        older = self.budget_history[0]

        budget_change = recent['consumed'] - older['consumed']
        time_change_hours = (recent['timestamp'] - older['timestamp']).total_seconds() / 3600

        if time_change_hours == 0:
            return 0.0

        return budget_change / time_change_hours

    def get_burn_rate_alert_level(self, burn_rate: float) -> str:
        """Determine alert level based on burn rate."""
        if burn_rate <= 0.1:  # <= 0.1% per hour
            return "slow"
        elif burn_rate <= 1.0:  # <= 1% per hour
            return "normal"
        elif burn_rate <= 5.0:  # <= 5% per hour
            return "fast"
        else:  # > 5% per hour
            return "critical"
```

## Release Risk Assessment

### Pre-Release Budget Check
```yaml
# .github/workflows/release-risk-assessment.yml
name: Release Risk Assessment

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main]

jobs:
  risk-assessment:
    runs-on: ubuntu-latest
    steps:
    - name: Assess release risk
      run: |
        # Check current error budget status
        BUDGET_CONSUMED=$(curl -s https://agent-lab.your-domain.com/metrics/error-budget | jq '.availability.consumed_percentage')

        # Check change size
        CHANGED_FILES=$(git diff --name-only HEAD~1 | wc -l)
        CHANGED_LINES=$(git diff --stat HEAD~1 | tail -1 | awk '{print $4+$6}')

        # Calculate risk score
        RISK_SCORE=0

        if (( $(echo "$BUDGET_CONSUMED > 50" | bc -l) )); then
          RISK_SCORE=$((RISK_SCORE + 30))
        fi

        if (( CHANGED_FILES > 20 )); then
          RISK_SCORE=$((RISK_SCORE + 20))
        fi

        if (( CHANGED_LINES > 1000 )); then
          RISK_SCORE=$((RISK_SCORE + 20))
        fi

        # Determine risk level
        if (( RISK_SCORE < 20 )); then
          echo "🟢 LOW RISK: Proceed with standard process"
          echo "risk_level=low" >> $GITHUB_OUTPUT
        elif (( RISK_SCORE < 50 )); then
          echo "🟡 MEDIUM RISK: Additional testing required"
          echo "risk_level=medium" >> $GITHUB_OUTPUT
        else
          echo "🔴 HIGH RISK: Stop and reassess"
          echo "risk_level=high" >> $GITHUB_OUTPUT
        fi

        echo "Risk Score: $RISK_SCORE/100"
        echo "Budget Consumed: ${BUDGET_CONSUMED}%"
        echo "Files Changed: $CHANGED_FILES"
        echo "Lines Changed: $CHANGED_LINES"
```

### Risk Levels
- **Low Risk**: Standard release process
- **Medium Risk**: Additional testing, gradual rollout
- **High Risk**: Stop release, reassess changes, consider rollback

## Error Budget and Incident Response

### Budget Impact of Incidents
Incidents consume error budget based on their duration and impact:

```
Budget Consumed = (Incident Duration × Impact Percentage) / Total Budget
```

### Post-Incident Budget Review
After incidents:
1. Calculate budget consumption
2. Update budget tracking
3. Assess if incident moves system to different zone
4. Determine if emergency measures needed
5. Plan budget recovery actions

### Budget Recovery Planning
When budget is low:
1. **Short-term**: Implement quick reliability fixes
2. **Medium-term**: Schedule reliability sprint
3. **Long-term**: Architectural improvements, capacity planning

## Communication and Transparency

### Internal Communication
- **Daily**: Budget status in standup
- **Weekly**: Detailed budget review
- **Monthly**: Trend analysis and planning
- **Ad-hoc**: Alerts when entering yellow/red zones

### Stakeholder Communication
- **Product**: Impact on feature velocity
- **Leadership**: Business risk and mitigation plans
- **Users**: Service status and improvement plans

### Dashboard Transparency
```html
<!-- error-budget-dashboard.html -->
<div class="budget-dashboard">
  <h2>Error Budget Status</h2>

  <div class="budget-metrics">
    <div class="metric">
      <h3>Availability Budget</h3>
      <div class="gauge" data-value="87" data-max="100"></div>
      <p>87% remaining (12% consumed)</p>
    </div>

    <div class="metric">
      <h3>Error Rate Budget</h3>
      <div class="gauge" data-value="95" data-max="100"></div>
      <p>95% remaining (5% consumed)</p>
    </div>
  </div>

  <div class="budget-zone">
    <h3>Current Zone</h3>
    <span class="zone-indicator green">🟢 GREEN</span>
    <p>Normal development velocity</p>
  </div>

  <div class="trends">
    <h3>7-Day Trend</h3>
    <canvas id="budget-trend-chart"></canvas>
  </div>
</div>
```

## Continuous Improvement

### Budget Effectiveness Review
**Quarterly Assessment**:
- Are budgets appropriate for business needs?
- Are we spending budget wisely?
- Should SLO targets be adjusted?
- Are we improving reliability over time?

### Learning from Budget Consumption
- **High Consumption**: Identify root causes, implement fixes
- **Low Consumption**: Consider if targets are too conservative
- **Trends**: Monitor for seasonal patterns or gradual degradation

### Tooling Improvements
- **Better Monitoring**: More accurate SLI measurement
- **Automated Alerts**: Proactive budget zone notifications
- **Predictive Analytics**: Forecast budget consumption trends

## Emergency Budget Actions

### When Budget is Exhausted
1. **Immediate**: Stop all non-critical releases
2. **Assessment**: Determine cause of budget exhaustion
3. **Recovery**: Implement emergency reliability measures
4. **Communication**: Notify all stakeholders of emergency measures
5. **Review**: Post-mortem on how budget was exhausted

### Budget Reset Considerations
- **Not Recommended**: Artificially resetting budgets hides problems
- **Preferred**: Fix underlying issues and earn back budget through improved reliability
- **Exception**: Major architecture changes may warrant target adjustments

This error budget framework ensures Agent Lab maintains reliable service while enabling innovation, with clear governance processes and escalation paths.