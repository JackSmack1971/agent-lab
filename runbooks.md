# Operational Runbooks - Agent Lab

## Overview

This document contains operational runbooks for routine maintenance, deployment procedures, monitoring checks, and other standard operating procedures for Agent Lab. Runbooks ensure consistent execution of operational tasks and provide step-by-step instructions for both automated and manual procedures.

## Daily Operations

### Morning Health Check Runbook

**Frequency**: Daily, 9:00 AM EST
**Duration**: 15 minutes
**Owner**: On-call SRE

#### Checklist
- [ ] **Dashboard Review**: Check executive dashboard for SLO status
- [ ] **Alert Review**: Review overnight alerts in Slack/email
- [ ] **Error Budget Check**: Verify error budget status and zone
- [ ] **Incident Review**: Check for any active incidents
- [ ] **Backup Verification**: Confirm last night's backups completed
- [ ] **Resource Monitoring**: Check system resource usage trends

#### Procedures
```bash
# 1. Check application health
curl -f https://agent-lab.your-domain.com/health/detailed

# 2. Review SLO status
curl -s https://agent-lab.your-domain.com/metrics/slo | jq '.'

# 3. Check recent backups
aws s3 ls s3://agent-lab-backups/ --recursive | tail -10

# 4. Monitor resource usage
ssh user@server "uptime && free -h && df -h"
```

#### Escalation Criteria
- Any SLO violation (red status)
- Error budget below 50%
- Failed backups
- Resource usage > 90%

### End-of-Day Handover Runbook

**Frequency**: Daily, 6:00 PM EST
**Duration**: 10 minutes

#### Checklist
- [ ] **Outstanding Issues**: Document any unresolved alerts
- [ ] **Ongoing Incidents**: Note active incident status
- [ ] **Scheduled Maintenance**: Confirm tomorrow's maintenance windows
- [ ] **On-call Handover**: Update on-call engineer contact
- [ ] **Key Metrics**: Record end-of-day SLO status

#### Handover Template
```markdown
# Daily Handover - $(date)

## Current Status
- **SLO Status**: [Green/Yellow/Red]
- **Active Alerts**: [Count]
- **Error Budget**: [Percentage remaining]

## Outstanding Items
- [Issue 1]: [Status, owner, ETA]
- [Issue 2]: [Status, owner, ETA]

## Tomorrow's Schedule
- [Maintenance window]: [Purpose, impact]
- [Release]: [Version, risk level]

## On-call Contact
- **Primary**: [Name] [Phone]
- **Backup**: [Name] [Phone]
```

## Deployment Runbooks

### Standard Deployment Runbook

**Frequency**: As needed (feature releases)
**Duration**: 30-60 minutes
**Pre-conditions**: All tests passing, error budget > 50%

#### Pre-deployment Checklist
- [ ] **Code Review**: Approved by required reviewers
- [ ] **Testing**: All unit and integration tests passing
- [ ] **Security Scan**: No critical vulnerabilities
- [ ] **Performance Test**: No performance regressions
- [ ] **Error Budget**: Sufficient budget remaining
- [ ] **Maintenance Window**: Scheduled if high-risk

#### Deployment Steps
```bash
# 1. Create deployment branch
git checkout -b deployment-$(date +%Y%m%d-%H%M%S)
git merge main

# 2. Run final validation
python -m pytest tests/ -v --tb=short
python -c "import app; print('✅ Application imports successfully')"

# 3. Tag release
git tag -a v$(cat version.txt) -m "Release v$(cat version.txt)"
git push origin v$(cat version.txt)

# 4. Deploy via GitHub Actions
gh workflow run deploy.yml -f environment=production

# 5. Monitor deployment
# Watch GitHub Actions logs
open https://github.com/your-org/agent-lab/actions

# 6. Post-deployment validation
curl -f https://agent-lab.your-domain.com/health
curl -f https://agent-lab.your-domain.com/health/detailed

# 7. Run smoke tests
python -m pytest tests/integration/test_smoke.py -v
```

#### Rollback Procedure
```bash
# Trigger automated rollback
gh workflow run rollback.yml -f reason="Post-deployment issues detected"

# Manual rollback if automated fails
ssh user@server "cd /app && git checkout HEAD~1"
ssh user@server "cd /app && python app.py &"

# Validate rollback
curl -f https://agent-lab.your-domain.com/health
```

#### Post-deployment Monitoring
- Monitor for 30 minutes after deployment
- Check SLO status every 5 minutes
- Alert if error rate increases by > 2x baseline
- Validate with manual testing if needed

### Blue-Green Deployment Runbook

**Frequency**: Major releases or high-risk deployments
**Duration**: 45-90 minutes

#### Process Overview
1. Deploy to staging environment
2. Run comprehensive testing
3. Deploy to production green environment
4. Route traffic gradually to green
5. Monitor and validate
6. Switch all traffic or rollback

#### Detailed Steps
```bash
# 1. Deploy to staging
gh workflow run deploy.yml -f environment=staging

# 2. Run staging validation
curl -f https://staging.agent-lab.your-domain.com/health
python -m pytest tests/integration/ -k "staging" -v

# 3. Deploy to production green
gh workflow run deploy.yml -f environment=production-green

# 4. Health check green environment
curl -f https://green.agent-lab.your-domain.com/health

# 5. Gradual traffic shift (if load balancer supports)
# Start with 10% traffic to green
# Monitor for 5 minutes
# Increase to 25%, monitor
# Increase to 50%, monitor
# Increase to 100%

# 6. Full switch or rollback decision
# If successful: update DNS/load balancer
# If issues: rollback to blue environment
```

## Maintenance Runbooks

### Weekly Maintenance Runbook

**Frequency**: Weekly, Sunday 2:00 AM EST
**Duration**: 60 minutes
**Impact**: 5-10 minute service interruption

#### Maintenance Tasks
- [ ] **Dependency Updates**: Update Python packages
- [ ] **Security Patches**: Apply system security updates
- [ ] **Log Rotation**: Rotate and archive application logs
- [ ] **Database Maintenance**: Optimize data structures
- [ ] **Backup Verification**: Test backup restoration
- [ ] **Certificate Renewal**: Check SSL certificates

#### Detailed Procedures
```bash
# 1. Schedule maintenance window
# Post maintenance notification
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🛠️ Scheduled maintenance starting in 30 minutes"}' \
  ${{ secrets.SLACK_WEBHOOK_URL }}

# 2. Enable maintenance mode
ssh user@server "touch /app/MAINTENANCE_MODE"

# 3. Update dependencies
ssh user@server "cd /app && pip install --upgrade -r requirements.txt"

# 4. Security updates
ssh user@server "apt update && apt upgrade -y"

# 5. Log rotation
ssh user@server "logrotate /etc/logrotate.d/agent-lab"

# 6. Backup verification
python scripts/test_backup_restoration.py

# 7. Restart services
ssh user@server "systemctl restart agent-lab"

# 8. Disable maintenance mode
ssh user@server "rm /app/MAINTENANCE_MODE"

# 9. Validation
curl -f https://agent-lab.your-domain.com/health
```

### Monthly Infrastructure Review Runbook

**Frequency**: Monthly, first Monday
**Duration**: 120 minutes

#### Review Areas
- [ ] **Capacity Planning**: Review resource utilization trends
- [ ] **Cost Optimization**: Analyze infrastructure costs
- [ ] **Security Audit**: Review access controls and vulnerabilities
- [ ] **Performance Optimization**: Identify bottlenecks
- [ ] **Backup Strategy**: Validate backup effectiveness
- [ ] **Disaster Recovery**: Test DR procedures

#### Detailed Procedures
```bash
# 1. Resource utilization analysis
# Review past month's metrics
curl -s https://agent-lab.your-domain.com/metrics/history | jq '.resources'

# 2. Cost analysis
# Check AWS billing or equivalent
aws ce get-cost-and-usage --time-period Start=$(date -d '1 month ago' +%Y-%m-%d),End=$(date +%Y-%m-%d)

# 3. Security assessment
# Run vulnerability scan
# Review access logs for anomalies

# 4. Performance analysis
# Identify slowest endpoints
# Review error patterns

# 5. Backup testing
# Restore from backup to test environment
python scripts/test_disaster_recovery.py

# 6. Generate report
# Document findings and recommendations
```

## Monitoring and Alerting Runbooks

### Alert Investigation Runbook

**Frequency**: When alerts fire
**Duration**: 15-60 minutes depending on severity

#### Investigation Steps
1. **Alert Triage**:
   ```bash
   # Check alert details
   # Review recent changes
   git log --oneline -10

   # Check system metrics
   curl https://agent-lab.your-domain.com/metrics
   ```

2. **Component Isolation**:
   ```bash
   # Test individual components
   curl -f https://agent-lab.your-domain.com/health/detailed

   # Check external dependencies
   curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/models
   ```

3. **Log Analysis**:
   ```bash
   # Search for error patterns
   grep -i "error\|exception" /var/log/agent-lab/app.log | tail -20

   # Check for recent spikes
   awk '{print $1}' /var/log/agent-lab/app.log | sort | uniq -c | sort -nr | head -10
   ```

4. **Resolution or Escalation**:
   - If known issue: Apply documented fix
   - If unknown: Escalate to incident response
   - Update alert status

### SLO Violation Response Runbook

**Frequency**: When SLO alerts fire
**Duration**: 30-120 minutes

#### Response Process
1. **Assess Impact**:
   ```bash
   # Check current SLO status
   curl -s https://agent-lab.your-domain.com/metrics/slo | jq '.'

   # Calculate error budget consumption
   python -c "
   import requests
   slo_data = requests.get('https://agent-lab.your-domain.com/metrics/slo').json()
   # Calculate budget consumption
   "
   ```

2. **Determine Zone**:
   - Green: Continue normal operations
   - Yellow: Increase monitoring, consider slowing releases
   - Red: Emergency measures, focus on reliability

3. **Implement Actions**:
   ```bash
   # For Yellow zone
   # Pause non-critical deployments
   gh workflow run disable deploy.yml

   # For Red zone
   # Enable emergency measures
   # Notify stakeholders
   ```

4. **Recovery Planning**:
   - Identify root cause
   - Plan fixes
   - Schedule reliability improvements

## Backup and Recovery Runbooks

### Backup Verification Runbook

**Frequency**: Daily, after backup completion
**Duration**: 15 minutes

#### Verification Steps
```bash
# 1. Check backup completion
BACKUP_STATUS=$(aws s3 ls s3://agent-lab-backups/ --recursive | grep $(date +%Y%m%d) | wc -l)
if [ "$BACKUP_STATUS" -eq 0 ]; then
  echo "❌ No backups found for today"
  exit 1
fi

# 2. Verify backup integrity
# Download and test a sample backup
aws s3 cp s3://agent-lab-backups/sessions/$(date +%Y%m%d)/sample.json /tmp/sample.json
python -m json.tool /tmp/sample.json > /dev/null

# 3. Check backup size trends
aws s3 ls s3://agent-lab-backups/ --recursive --summarize | grep "Total Size"

# 4. Test restoration procedure
python scripts/test_backup_restoration.py --quick
```

### Data Recovery Runbook

**Frequency**: As needed (data loss incidents)
**Duration**: 30-120 minutes

#### Recovery Process
1. **Assess Data Loss**:
   ```bash
   # Check what data is missing
   find data/sessions/ -name "*.json" | wc -l
   wc -l data/runs.csv

   # Compare with backup
   aws s3 ls s3://agent-lab-backups/sessions/ --recursive | tail -10
   ```

2. **Select Recovery Point**:
   ```bash
   # Choose appropriate backup (usually latest)
   RECOVERY_DATE=$(date -d '1 hour ago' +%Y%m%d)
   ```

3. **Execute Recovery**:
   ```bash
   # Stop application writes
   touch /app/READ_ONLY_MODE

   # Restore from backup
   python scripts/restore_data.py --date $RECOVERY_DATE --type sessions
   python scripts/restore_data.py --date $RECOVERY_DATE --type telemetry

   # Validate restoration
   find data/sessions/ -name "*.json" | head -5 | xargs -I {} python -m json.tool {} > /dev/null

   # Restart application
   rm /app/READ_ONLY_MODE
   systemctl restart agent-lab
   ```

4. **Post-Recovery Validation**:
   ```bash
   # Health checks
   curl -f https://agent-lab.your-domain.com/health

   # Data integrity checks
   python scripts/validate_data_integrity.py

   # Functional testing
   python -m pytest tests/integration/test_data_integrity.py -v
   ```

## Emergency Runbooks

### Service Restart Runbook

**Frequency**: As needed
**Duration**: 5-15 minutes

#### Restart Procedures
```bash
# 1. Graceful restart
ssh user@server "systemctl restart agent-lab"

# 2. If graceful fails, force restart
ssh user@server "pkill -f 'python app.py'"
ssh user@server "cd /app && python app.py &"

# 3. Validate restart
for i in {1..10}; do
  if curl -f -s https://agent-lab.your-domain.com/health > /dev/null; then
    echo "✅ Service restarted successfully"
    exit 0
  fi
  sleep 10
done

echo "❌ Service failed to restart"
exit 1
```

### Emergency Shutdown Runbook

**Frequency**: Critical situations only
**Duration**: 2-5 minutes

#### Shutdown Steps
```bash
# 1. Enable maintenance mode
ssh user@server "touch /app/EMERGENCY_SHUTDOWN"

# 2. Notify users (if possible)
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🚨 Emergency shutdown in progress"}' \
  ${{ secrets.SLACK_WEBHOOK_URL }}

# 3. Graceful shutdown
ssh user@server "systemctl stop agent-lab"

# 4. Force shutdown if needed
ssh user@server "pkill -9 -f 'python app.py'"

# 5. Verify shutdown
ssh user@server "ps aux | grep python | grep -v grep || echo '✅ Shutdown complete'"
```

## Capacity Planning Runbook

### Resource Scaling Runbook

**Frequency**: When resource alerts trigger or planned
**Duration**: 30-60 minutes

#### Scaling Assessment
1. **Current Usage Analysis**:
   ```bash
   # Check current resource usage
   ssh user@server "uptime && free -h && df -h && iostat -x 1 5"

   # Review historical trends
   curl -s https://agent-lab.your-domain.com/metrics/history | jq '.resources.last_30_days'
   ```

2. **Scaling Decision**:
   - **Vertical Scaling**: Increase instance size
   - **Horizontal Scaling**: Add more instances
   - **Optimization**: Improve efficiency first

3. **Implementation**:
   ```bash
   # Vertical scaling example (AWS)
   aws ec2 modify-instance-attribute \
     --instance-id i-1234567890abcdef0 \
     --instance-type t3.large

   # Horizontal scaling (if load balancer setup)
   aws elb register-instances-with-load-balancer \
     --load-balancer-name agent-lab-lb \
     --instances i-newinstance
   ```

4. **Post-Scaling Validation**:
   ```bash
   # Monitor resource usage
   watch -n 60 "ssh user@server 'uptime && free -h'"

   # Performance testing
   ab -n 1000 -c 10 https://agent-lab.your-domain.com/health
   ```

## Security Runbooks

### Access Review Runbook

**Frequency**: Quarterly
**Duration**: 60 minutes

#### Review Process
1. **Access Audit**:
   ```bash
   # Check active SSH sessions
   who

   # Review sudo access
   getent group sudo

   # Check file permissions
   ls -la /app/
   ```

2. **Credential Rotation**:
   ```bash
   # Rotate SSH keys
   ssh-keygen -t ed25519 -C "agent-lab-$(date +%Y%m%d)"

   # Update secrets
   # Follow secret rotation procedures
   ```

3. **Security Updates**:
   ```bash
   # Update system packages
   apt update && apt upgrade -y

   # Update Python dependencies
   pip install --upgrade -r requirements-security.txt
   ```

### Incident Investigation Runbook

**Frequency**: After security alerts
**Duration**: 60-240 minutes

#### Investigation Framework
1. **Evidence Collection**:
   ```bash
   # Preserve logs
   cp /var/log/auth.log /var/log/auth.log.investigation
   cp /var/log/agent-lab/app.log /var/log/agent-lab/app.log.investigation

   # Create system snapshot
   aws ec2 create-snapshot --instance-id $INSTANCE_ID --description "Security investigation"
   ```

2. **Timeline Reconstruction**:
   ```bash
   # Analyze access logs
   awk '{print $1, $2, $3}' /var/log/auth.log | sort | uniq -c | sort -nr

   # Check for suspicious activity
   grep -i "failed\|invalid" /var/log/auth.log
   ```

3. **Impact Assessment**:
   - What data was accessed?
   - Were credentials compromised?
   - What systems are affected?

4. **Containment and Recovery**:
   - Block compromised accounts
   - Rotate all credentials
   - Restore from clean backups
   - Implement additional security measures

## Testing and Validation Runbooks

### Load Testing Runbook

**Frequency**: Before major releases, quarterly
**Duration**: 60 minutes

#### Test Execution
```bash
# 1. Baseline measurement
curl -s https://agent-lab.your-domain.com/metrics > baseline.json

# 2. Execute load tests
# Using Apache Bench
ab -n 10000 -c 50 https://agent-lab.your-domain.com/api/agents

# Using custom load test script
python scripts/load_test.py --duration 300 --concurrency 20

# 3. Analyze results
python scripts/analyze_load_test_results.py

# 4. Compare with baseline
# Check for performance regressions
```

### Chaos Engineering Runbook

**Frequency**: Monthly, controlled environment
**Duration**: 30 minutes

#### Chaos Experiments
1. **Network Latency Injection**:
   ```bash
   # Add 500ms latency to OpenRouter calls
   tc qdisc add dev eth0 root netem delay 500ms
   # Run tests
   python -m pytest tests/integration/test_api_resilience.py
   # Remove latency
   tc qdisc del dev eth0 root
   ```

2. **Service Failure Simulation**:
   ```bash
   # Stop application briefly
   systemctl stop agent-lab
   sleep 30
   systemctl start agent-lab

   # Validate recovery
   curl -f https://agent-lab.your-domain.com/health
   ```

3. **Resource Exhaustion**:
   ```bash
   # Simulate memory pressure
   stress --vm 1 --vm-bytes 1G --timeout 60

   # Monitor application behavior
   ```

## Documentation and Training

### Runbook Maintenance Runbook

**Frequency**: Monthly
**Duration**: 30 minutes

#### Maintenance Tasks
- [ ] **Review Usage**: Check which runbooks are used most
- [ ] **Update Procedures**: Incorporate lessons learned
- [ ] **Validate Steps**: Test critical runbook steps
- [ ] **Training Updates**: Update training materials

#### Improvement Process
1. **Collect Feedback**: Gather input from runbook users
2. **Analyze Effectiveness**: Review success rates and time savings
3. **Update Content**: Incorporate new procedures and tools
4. **Version Control**: Track changes and maintain history

### New Team Member Onboarding Runbook

**Frequency**: When new SREs join
**Duration**: 120 minutes

#### Onboarding Steps
1. **Access Setup**: Provide necessary system access
2. **Tool Training**: Introduce monitoring and deployment tools
3. **Runbook Walkthrough**: Review key operational procedures
4. **Shadowing**: Pair with experienced team member
5. **Certification**: Validate understanding of critical procedures

This comprehensive set of operational runbooks ensures consistent, reliable execution of all operational procedures for Agent Lab.