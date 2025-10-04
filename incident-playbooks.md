# Incident Response Playbooks - Agent Lab

## Overview

This document contains detailed playbooks for responding to specific types of incidents in Agent Lab. Each playbook provides step-by-step instructions for detection, containment, recovery, and post-incident analysis. Playbooks are designed to be followed by on-call engineers and incident response teams.

## General Incident Response Process

### Phase 1: Detection & Triage (0-5 minutes)
1. **Acknowledge Alert**: Confirm alert receipt within 2 minutes
2. **Assess Severity**: Determine P0-P3 based on impact and scope
3. **Gather Initial Data**: Collect basic system metrics and logs
4. **Notify Team**: Alert appropriate responders based on severity

### Phase 2: Investigation (5-30 minutes)
1. **Isolate Affected Systems**: Prevent further impact
2. **Collect Evidence**: Gather logs, metrics, and system state
3. **Identify Root Cause**: Determine what caused the incident
4. **Assess Impact**: Understand scope and user impact

### Phase 3: Containment & Recovery (30-120 minutes)
1. **Implement Mitigations**: Apply temporary fixes
2. **Begin Recovery**: Restore service using documented procedures
3. **Validate Fixes**: Ensure recovery is successful
4. **Monitor Recovery**: Watch for side effects or regressions

### Phase 4: Post-Incident (2-24 hours)
1. **Document Timeline**: Record all actions and findings
2. **Conduct Post-Mortem**: Analyze root cause and improvements
3. **Implement Fixes**: Apply permanent solutions
4. **Update Documentation**: Improve playbooks and monitoring

## Playbook: Application Down (P0)

### Detection
- **Alert Source**: Health monitoring workflow fails
- **Symptoms**: `/health` endpoint returns 5xx or times out
- **Impact**: Complete service outage, users cannot access application

### Immediate Actions (0-2 minutes)
```bash
# Check application status
curl -f --max-time 10 https://agent-lab.your-domain.com/health

# If failed, check system resources
ssh user@server "top -b -n1 | head -20"
ssh user@server "df -h"
ssh user@server "free -h"
```

### Investigation (2-10 minutes)
1. **Check Application Logs**:
   ```bash
   # View recent application logs
   ssh user@server "tail -100 /var/log/agent-lab/app.log"

   # Check for error patterns
   ssh user@server "grep -i error /var/log/agent-lab/app.log | tail -20"
   ```

2. **Verify Dependencies**:
   ```bash
   # Test OpenRouter API connectivity
   curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
        https://openrouter.ai/api/v1/models

   # Check database/file system access
   ssh user@server "ls -la /app/data/"
   ssh user@server "head -5 /app/data/runs.csv"
   ```

3. **Check System Resources**:
   ```bash
   # Monitor system resources
   ssh user@server "ps aux | grep python"
   ssh user@server "netstat -tlnp | grep :7860"
   ```

### Containment (10-30 minutes)
1. **Restart Application** (if process crashed):
   ```bash
   ssh user@server "cd /app && python app.py &"
   ```

2. **Scale Resources** (if resource exhaustion):
   ```bash
   # If on cloud platform, increase instance size
   # AWS example
   aws ec2 modify-instance-attribute \
     --instance-id i-1234567890abcdef0 \
     --instance-type t3.medium
   ```

3. **Enable Maintenance Mode** (if needed):
   ```bash
   # Create maintenance page
   ssh user@server "cp maintenance.html /var/www/html/index.html"
   ```

### Recovery (30-60 minutes)
1. **Verify Recovery**:
   ```bash
   # Test health endpoint
   curl https://agent-lab.your-domain.com/health/detailed

   # Test core functionality
   curl -X POST https://agent-lab.your-domain.com/api/agents \
        -H "Content-Type: application/json" \
        -d '{"name":"test","model":"gpt-3.5-turbo","system_prompt":"test"}'
   ```

2. **Gradual Traffic Restoration**:
   ```bash
   # Remove maintenance mode
   ssh user@server "cp index.html.backup /var/www/html/index.html"
   ```

3. **Monitor Post-Recovery**:
   ```bash
   # Watch logs for errors
   ssh user@server "tail -f /var/log/agent-lab/app.log"
   ```

### Post-Incident Actions
- **Root Cause Analysis**: Identify why application crashed
- **Capacity Planning**: Review resource allocation
- **Monitoring Improvements**: Add alerts for crash precursors
- **Documentation**: Update runbooks with new failure modes

---

## Playbook: High Error Rate (P1)

### Detection
- **Alert Source**: SLO monitoring detects >1% error rate
- **Symptoms**: Increased 4xx/5xx responses in metrics
- **Impact**: Degraded user experience, potential functionality issues

### Investigation (5-15 minutes)
1. **Analyze Error Patterns**:
   ```bash
   # Check recent error logs
   ssh user@server "grep 'ERROR\|Exception' /var/log/agent-lab/app.log | tail -50"

   # Group errors by type
   ssh user@server "grep 'ERROR' /var/log/agent-lab/app.log | cut -d' ' -f4- | sort | uniq -c | sort -nr"
   ```

2. **Check External Dependencies**:
   ```bash
   # Test OpenRouter API
   for i in {1..5}; do
     curl -w "@curl-format.txt" -o /dev/null -s \
          -H "Authorization: Bearer $OPENROUTER_API_KEY" \
          https://openrouter.ai/api/v1/chat/completions \
          -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"test"}]}'
   done
   ```

3. **Review Recent Changes**:
   ```bash
   # Check recent deployments
   git log --oneline -10

   # Check if recent changes affected error-prone code
   git diff HEAD~1..HEAD -- agents/runtime.py
   ```

### Containment (15-45 minutes)
1. **Rate Limiting** (if API abuse):
   ```python
   # Add rate limiting middleware
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```

2. **Circuit Breaker** (if external service issues):
   ```python
   # Implement circuit breaker for OpenRouter calls
   import circuitbreaker

   @circuitbreaker(circuit_breaker_failure_threshold=5, recovery_timeout=60)
   def call_openrouter_api(request_data):
       # API call with circuit breaker
       pass
   ```

3. **Rollback** (if recent deployment caused issues):
   ```bash
   # Trigger rollback workflow
   gh workflow run rollback.yml -R your-org/agent-lab \
     -f reason="High error rate detected"
   ```

### Recovery (45-90 minutes)
1. **Validate Error Reduction**:
   ```bash
   # Monitor error rate over time
   watch -n 60 "curl -s https://agent-lab.your-domain.com/metrics | jq '.error_rate_sli'"
   ```

2. **Test Critical Paths**:
   ```bash
   # Run integration tests
   python -m pytest tests/integration/ -v
   ```

3. **Gradual Feature Enablement**:
   ```bash
   # If features were disabled, re-enable gradually
   # Monitor for error rate increases
   ```

### Post-Incident Actions
- **Error Analysis**: Categorize and prioritize error types
- **Testing Improvements**: Add tests for error conditions
- **Monitoring Enhancements**: Add alerts for specific error patterns
- **Capacity Planning**: Review if load caused errors

---

## Playbook: Data Corruption (P1)

### Detection
- **Alert Source**: Data integrity monitoring fails
- **Symptoms**: JSON parsing errors, CSV format issues, missing sessions
- **Impact**: User data loss, application errors, trust issues

### Investigation (5-20 minutes)
1. **Assess Corruption Scope**:
   ```bash
   # Check session files
   find data/sessions/ -name "*.json" -exec python -m json.tool {} \; 2>&1 | grep -v "No JSON object" | head -10

   # Check CSV integrity
   python -c "
   import csv
   with open('data/runs.csv', 'r') as f:
       reader = csv.reader(f)
       header = next(reader)
       print('Header:', header)
       for i, row in enumerate(reader):
           if len(row) != len(header):
               print(f'Row {i}: length mismatch {len(row)} != {len(header)}')
               break
   "
   ```

2. **Identify Corruption Source**:
   ```bash
   # Check recent writes
   ls -la data/sessions/ | tail -10

   # Check application logs for write errors
   grep -i "write\|save\|persist" /var/log/agent-lab/app.log | tail -20
   ```

3. **Verify Backup Integrity**:
   ```bash
   # List recent backups
   aws s3 ls s3://agent-lab-backups/sessions/ --recursive | sort | tail -10

   # Test backup restoration
   aws s3 cp s3://agent-lab-backups/sessions/$(date +%Y%m%d)/test.json /tmp/test.json
   python -m json.tool /tmp/test.json
   ```

### Containment (20-60 minutes)
1. **Stop Write Operations**:
   ```bash
   # Enable read-only mode
   ssh user@server "touch /app/READ_ONLY_MODE"

   # Modify application to check for read-only flag
   ```

2. **Quarantine Corrupted Data**:
   ```bash
   # Move corrupted files
   mkdir -p data/quarantined/$(date +%Y%m%d_%H%M%S)
   mv data/sessions/corrupted_file.json data/quarantined/$(date +%Y%m%d_%H%M%S)/
   ```

3. **Preserve Evidence**:
   ```bash
   # Create forensic copy
   tar -czf evidence-$(date +%Y%m%d_%H%M%S).tar.gz data/
   aws s3 cp evidence-*.tar.gz s3://agent-lab-backups/forensics/
   ```

### Recovery (60-180 minutes)
1. **Restore from Backup**:
   ```bash
   # Use restoration script
   python scripts/restore_data.py --type sessions --date $(date -d '1 hour ago' +%Y%m%d)

   # Validate restoration
   find data/sessions/ -name "*.json" | wc -l
   ```

2. **Rebuild Missing Data** (if needed):
   ```python
   # Script to rebuild CSV from sessions
   import json
   from pathlib import Path
   import csv

   sessions_dir = Path('data/sessions')
   csv_file = Path('data/runs.csv')

   with open(csv_file, 'w', newline='') as f:
       writer = csv.writer(f)
       writer.writerow(['ts', 'agent_name', 'model', 'prompt_tokens', 'completion_tokens',
                       'total_tokens', 'latency_ms', 'cost_usd', 'experiment_id',
                       'task_label', 'run_notes', 'streaming', 'model_list_source',
                       'tool_web_enabled', 'web_status', 'aborted'])

       for session_file in sessions_dir.glob('*.json'):
           try:
               with open(session_file, 'r') as sf:
                   session = json.load(sf)
                   # Extract run data from session
                   # Write to CSV
           except json.JSONDecodeError:
               print(f"Skipping corrupted file: {session_file}")
   ```

3. **Validate Data Integrity**:
   ```bash
   # Run integrity checks
   python -c "
   import json
   from pathlib import Path

   sessions_dir = Path('data/sessions')
   valid = 0
   invalid = 0

   for session_file in sessions_dir.glob('*.json'):
       try:
           with open(session_file, 'r') as f:
               json.load(f)
           valid += 1
       except json.JSONDecodeError:
           invalid += 1

   print(f'Valid sessions: {valid}, Invalid: {invalid}')
   "
   ```

### Post-Incident Actions
- **Root Cause Analysis**: Determine corruption cause (bug, disk failure, etc.)
- **Backup Verification**: Improve backup integrity checks
- **Data Validation**: Add real-time corruption detection
- **Recovery Testing**: Regular DR testing including data corruption scenarios

---

## Playbook: Streaming Failure (P2)

### Detection
- **Alert Source**: Streaming continuity SLO violation
- **Symptoms**: Agent responses cut off, connection errors, timeout errors
- **Impact**: Poor user experience, incomplete responses

### Investigation (5-15 minutes)
1. **Check Streaming Logs**:
   ```bash
   # Look for streaming-related errors
   grep -i "stream\|chunk\|disconnect" /var/log/agent-lab/app.log | tail -20

   # Check OpenRouter streaming endpoints
   curl -N -X POST \
        -H "Authorization: Bearer $OPENROUTER_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Hello"}],"stream":true}' \
        https://openrouter.ai/api/v1/chat/completions
   ```

2. **Network Connectivity**:
   ```bash
   # Test network stability
   ping -c 10 openrouter.ai

   # Check for packet loss
   mtr -c 10 openrouter.ai
   ```

3. **Client-Side Issues**:
   ```bash
   # Check Gradio streaming implementation
   # Review browser console for JavaScript errors
   ```

### Containment (15-30 minutes)
1. **Disable Streaming Temporarily**:
   ```python
   # Modify app to disable streaming
   STREAMING_ENABLED = False  # Configuration flag
   ```

2. **Implement Retry Logic**:
   ```python
   # Add retry for streaming failures
   @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
   async def stream_response():
       # Streaming implementation with retry
       pass
   ```

3. **Reduce Chunk Size**:
   ```python
   # Smaller chunks to reduce failure likelihood
   CHUNK_SIZE = 50  # characters instead of 100
   ```

### Recovery (30-60 minutes)
1. **Test Streaming Recovery**:
   ```bash
   # Test streaming endpoint
   curl -N https://agent-lab.your-domain.com/api/stream/test
   ```

2. **Gradual Rollout**:
   ```bash
   # Enable streaming for subset of users
   # Monitor for continued issues
   ```

3. **Performance Monitoring**:
   ```bash
   # Monitor streaming metrics
   watch -n 30 "curl -s https://agent-lab.your-domain.com/metrics | jq '.streaming_metrics'"
   ```

### Post-Incident Actions
- **Network Analysis**: Investigate connectivity issues
- **API Reliability**: Review OpenRouter streaming reliability
- **Client Improvements**: Enhance Gradio streaming handling
- **Fallback Options**: Implement non-streaming fallback

---

## Playbook: Performance Degradation (P2)

### Detection
- **Alert Source**: Latency SLO violations, high resource usage
- **Symptoms**: Slow response times, high CPU/memory usage
- **Impact**: Poor user experience, potential timeouts

### Investigation (5-15 minutes)
1. **Performance Metrics**:
   ```bash
   # Check system resources
   top -b -n1 | head -20
   iostat -x 1 5
   free -h

   # Check application metrics
   curl https://agent-lab.your-domain.com/metrics
   ```

2. **Identify Bottlenecks**:
   ```bash
   # Profile application
   python -m cProfile -s cumtime app.py 2>&1 | head -30

   # Check database query performance
   # Analyze slowest requests
   ```

3. **Recent Changes**:
   ```bash
   # Check for performance regressions
   git log --oneline --since="1 week ago"
   ```

### Containment (15-45 minutes)
1. **Resource Scaling**:
   ```bash
   # Increase instance size or add instances
   aws ec2 modify-instance-attribute --instance-id $INSTANCE_ID --instance-type t3.large
   ```

2. **Request Throttling**:
   ```python
   # Implement request rate limiting
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   ```

3. **Cache Optimization**:
   ```bash
   # Clear application caches if applicable
   # Optimize model catalog caching
   ```

### Recovery (45-120 minutes)
1. **Performance Validation**:
   ```bash
   # Load testing
   ab -n 1000 -c 10 https://agent-lab.your-domain.com/health

   # Monitor resource usage during load
   ```

2. **Optimization Deployment**:
   ```bash
   # Deploy performance fixes
   git tag performance-fix-$(date +%Y%m%d)
   git push origin main
   ```

3. **Monitoring**:
   ```bash
   # Watch performance metrics
   watch -n 60 "curl -s https://agent-lab.your-domain.com/metrics | jq '.performance'"
   ```

### Post-Incident Actions
- **Performance Analysis**: Identify bottleneck causes
- **Capacity Planning**: Review resource requirements
- **Code Optimization**: Implement performance improvements
- **Load Testing**: Regular performance regression testing

---

## Playbook: Security Incident (P0)

### Detection
- **Alert Source**: Security monitoring, unusual access patterns
- **Symptoms**: Unauthorized access, data exfiltration, suspicious API calls
- **Impact**: Data breach, compliance violations, legal issues

### Immediate Actions (0-5 minutes)
```bash
# Isolate affected systems
# Rotate credentials immediately
aws iam update-access-key --access-key-id $COMPROMISED_KEY --status Inactive

# Block suspicious IPs
aws waf update-ip-set --scope REGIONAL --name suspicious-ips \
    --id $IP_SET_ID --addresses $SUSPICIOUS_IP
```

### Investigation (5-60 minutes)
1. **Access Log Analysis**:
   ```bash
   # Review access logs for suspicious activity
   aws s3 cp s3://agent-lab-logs/$(date +%Y/%m/%d/) /tmp/logs/
   grep -i "error\|fail\|invalid" /tmp/logs/access.log | head -50

   # Check for unusual API usage
   awk '{print $1}' /tmp/logs/access.log | sort | uniq -c | sort -nr | head -20
   ```

2. **Compromised Data Assessment**:
   ```bash
   # Check for data exfiltration
   aws s3 ls s3://agent-lab-backups/ --recursive | tail -50

   # Review session data access
   find data/sessions/ -newer $(date -d '1 hour ago' +%Y%m%d%H%M) | wc -l
   ```

3. **Attack Vector Identification**:
   ```bash
   # Check for common attack patterns
   grep -i "sql\|xss\|injection" /var/log/agent-lab/app.log
   ```

### Containment (60-120 minutes)
1. **System Isolation**:
   ```bash
   # Disconnect from network if needed
   # Create forensic images
   aws ec2 create-snapshot --instance-id $INSTANCE_ID --description "Security incident forensics"
   ```

2. **Credential Rotation**:
   ```bash
   # Rotate all secrets
   aws secretsmanager update-secret --secret-id agent-lab-api-key --secret-string $NEW_KEY

   # Update application configuration
   ssh user@server "sed -i 's/OLD_KEY/NEW_KEY/' .env"
   ```

3. **Access Control**:
   ```bash
   # Implement stricter access controls
   # Enable additional logging
   # Set up intrusion detection
   ```

### Recovery (120-480 minutes)
1. **Clean System Restoration**:
   ```bash
   # Restore from known clean backup
   # Rebuild systems from trusted images
   # Validate system integrity
   ```

2. **Security Hardening**:
   ```bash
   # Implement security improvements
   # Update dependencies for security patches
   # Configure additional monitoring
   ```

3. **Validation**:
   ```bash
   # Security testing
   # Penetration testing
   # Compliance verification
   ```

### Post-Incident Actions
- **Forensic Analysis**: Complete investigation report
- **Legal Compliance**: Notify authorities if required
- **Security Improvements**: Implement lessons learned
- **Communication**: User notification if data breached
- **Insurance**: File incident reports for coverage

---

## Playbook: Deployment Failure (P1)

### Detection
- **Alert Source**: CI/CD pipeline failures, health check failures post-deployment
- **Symptoms**: Deployment workflow fails, application errors after update
- **Impact**: Service disruption, broken functionality

### Investigation (5-20 minutes)
1. **Deployment Log Analysis**:
   ```bash
   # Check GitHub Actions logs
   gh run view $RUN_ID --log

   # Check deployment scripts
   cat .github/workflows/deploy.yml
   ```

2. **Error Identification**:
   ```bash
   # Check application startup logs
   ssh user@server "journalctl -u agent-lab -n 50"

   # Test individual components
   ssh user@server "cd /app && python -c 'import app; print(\"Import OK\")'"
   ```

3. **Change Analysis**:
   ```bash
   # Review what changed
   git diff HEAD~1..HEAD

   # Check for breaking changes
   git log --oneline -5
   ```

### Containment (20-40 minutes)
1. **Stop Broken Deployment**:
   ```bash
   # Disable failing deployment
   gh workflow run disable deploy.yml
   ```

2. **Rollback to Previous Version**:
   ```bash
   # Trigger rollback workflow
   gh workflow run rollback.yml -R your-org/agent-lab \
     -f reason="Deployment failure - rolling back"
   ```

3. **Temporary Mitigation**:
   ```bash
   # Enable maintenance mode
   ssh user@server "cp maintenance.html /var/www/html/index.html"
   ```

### Recovery (40-90 minutes)
1. **Validate Rollback**:
   ```bash
   # Test health after rollback
   curl https://agent-lab.your-domain.com/health

   # Run smoke tests
   python -m pytest tests/integration/test_smoke.py -v
   ```

2. **Fix Deployment Issues**:
   ```bash
   # Identify and fix deployment problems
   # Test fixes in staging
   # Redeploy with fixes
   ```

3. **Gradual Traffic Restoration**:
   ```bash
   # Remove maintenance mode
   # Monitor for issues
   ```

### Post-Incident Actions
- **Deployment Analysis**: Review pipeline and scripts
- **Testing Improvements**: Enhance pre-deployment testing
- **Rollback Procedures**: Test rollback processes regularly
- **Change Management**: Implement stricter change controls

---

## Communication Templates

### Incident Status Update
```
🚨 INCIDENT UPDATE: [Incident Title]

Status: [Active/Investigating/Resolved]
Impact: [Description of user impact]
Timeline: [When detected, current status, ETA]

Actions Taken: [What has been done]
Next Steps: [What's happening next]

On-call: [Engineer name]
Issue: [GitHub issue link]
```

### User-Facing Communication
```
Service Update: [Brief description]

We are experiencing [issue description]. Our team is working to resolve this.

Current Status: 🔴 [Major/Minor] Issue
Start Time: [Timestamp]
Estimated Resolution: [Time or "Monitoring"]

Affected: [What users/services are impacted]
Workaround: [Any available workarounds]

We apologize for the inconvenience and will provide updates.
```

### Post-Incident Report
```
# Incident Summary: [Title]

📅 Timeline
- Detected: [Time]
- Resolved: [Time]
- Duration: [Duration]

👥 Impact
- Users affected: [Number/percentage]
- Functionality impacted: [Description]

🔍 Root Cause
[Detailed technical analysis]

🛠️ Resolution
[Steps taken to resolve]

📈 Prevention
[Measures implemented]

🎯 Lessons Learned
[Key insights and improvements]
```

These playbooks provide structured responses to common incident types, ensuring consistent and effective incident management for Agent Lab.