# Disaster Recovery & Backup Strategy for Agent Lab

## Executive Summary

This document outlines a comprehensive disaster recovery and backup strategy for the Agent Lab application, ensuring business continuity, data protection, and rapid recovery from system failures. The strategy covers code, data, infrastructure, and operational procedures.

## Risk Assessment

### Critical Assets
1. **User Session Data**: JSON files containing conversation transcripts and agent configurations
2. **Telemetry Data**: CSV files with performance metrics, costs, and experiment results
3. **Source Code**: Application logic and test suites
4. **CI/CD Pipelines**: Automated testing and deployment workflows
5. **Environment Configuration**: API keys, dependencies, and infrastructure settings

### Threat Scenarios
1. **Data Loss**: Accidental deletion of session files or CSV data
2. **Deployment Failure**: Broken releases requiring immediate rollback
3. **Infrastructure Failure**: GitHub Actions outage or repository corruption
4. **Dependency Issues**: Breaking changes in upstream packages
5. **Security Breach**: Unauthorized access to sensitive data

### Recovery Objectives
- **RTO (Recovery Time Objective)**: < 4 hours for critical data, < 24 hours for full service
- **RPO (Recovery Point Objective)**: < 1 hour data loss for active sessions, < 24 hours for telemetry
- **Data Retention**: 90 days for session data, 1 year for telemetry data

## Backup Strategy

### 1. Code Repository Protection

#### Git-Based Backup
```yaml
# .github/workflows/backup.yml
name: Repository Backup

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Create backup archive
      run: |
        tar -czf agent-lab-backup-$(date +%Y%m%d).tar.gz \
          --exclude='.git' \
          --exclude='__pycache__' \
          --exclude='.pytest_cache' \
          --exclude='.coverage' \
          --exclude='node_modules' \
          .

    - name: Upload to backup storage
      uses: actions/upload-artifact@v4
      with:
        name: repository-backup
        path: agent-lab-backup-*.tar.gz
        retention-days: 30

    - name: Sync to external storage
      run: |
        # Upload to cloud storage (AWS S3, GCP Cloud Storage, etc.)
        aws s3 cp agent-lab-backup-*.tar.gz s3://agent-lab-backups/code/
```

#### Mirror Repository
- Maintain secondary Git repository on GitLab or Bitbucket
- Automated mirroring using Git hooks or scheduled sync
- Cross-platform redundancy for repository availability

### 2. Data Backup Strategy

#### User Session Data
```python
# services/backup.py
import boto3
from pathlib import Path
from datetime import datetime, timezone

class DataBackupManager:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'agent-lab-backups'
        self.data_dir = Path('data')

    def backup_sessions(self):
        """Backup all user session files."""
        sessions_dir = self.data_dir / 'sessions'
        if not sessions_dir.exists():
            return

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

        for session_file in sessions_dir.glob('*.json'):
            if session_file.name == '.gitkeep':
                continue

            key = f'sessions/{timestamp}/{session_file.name}'
            self.s3_client.upload_file(
                str(session_file),
                self.bucket_name,
                key,
                ExtraArgs={'StorageClass': 'STANDARD_IA'}
            )

    def backup_telemetry(self):
        """Backup telemetry CSV with compression."""
        csv_file = self.data_dir / 'runs.csv'
        if not csv_file.exists():
            return

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        compressed_key = f'telemetry/{timestamp}/runs.csv.gz'

        # Compress and upload
        import gzip
        with gzip.open(f'/tmp/runs.csv.gz', 'wb') as gz_file:
            gz_file.write(csv_file.read_bytes())

        self.s3_client.upload_file(
            '/tmp/runs.csv.gz',
            self.bucket_name,
            compressed_key,
            ExtraArgs={'StorageClass': 'STANDARD_IA'}
        )
```

#### Automated Backup Workflow
```yaml
# .github/workflows/data-backup.yml
name: Data Backup

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: pip install boto3

    - name: Run data backup
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        AWS_DEFAULT_REGION: ${{ secrets.AWS_DEFAULT_REGION }}
      run: |
        python -c "
        from services.backup import DataBackupManager
        backup_mgr = DataBackupManager()
        backup_mgr.backup_sessions()
        backup_mgr.backup_telemetry()
        print('Data backup completed successfully')
        "

    - name: Verify backup integrity
      run: |
        # Verify recent files exist in backup location
        aws s3 ls s3://agent-lab-backups/sessions/ --recursive | tail -5
        aws s3 ls s3://agent-lab-backups/telemetry/ --recursive | tail -5
```

### 3. Configuration Backup

#### Environment Variables
- Store encrypted secrets in GitHub Secrets
- Document all required environment variables
- Maintain `.env.example` with placeholder values
- Regular audit of secret rotation

#### Infrastructure Configuration
```yaml
# infrastructure.yml (for future containerization)
version: '3.8'
services:
  agent-lab:
    build: .
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import app; print('healthy')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Disaster Recovery Procedures

### 1. Code Repository Recovery

#### Primary Recovery (GitHub Available)
```bash
# Clone from primary repository
git clone https://github.com/your-org/agent-lab.git
cd agent-lab

# Restore from backup artifact if needed
# Download latest backup from GitHub Actions artifacts
```

#### Secondary Recovery (GitHub Unavailable)
```bash
# Clone from mirror repository
git clone https://gitlab.com/your-org/agent-lab-mirror.git
cd agent-lab

# Push to restore primary repository
git remote add origin https://github.com/your-org/agent-lab.git
git push -u origin main
```

### 2. Data Recovery

#### Session Data Recovery
```python
# scripts/restore_data.py
from services.backup import DataBackupManager
from pathlib import Path
import boto3

def restore_sessions(backup_date: str):
    """Restore session data from backup."""
    s3_client = boto3.client('s3')
    bucket_name = 'agent-lab-backups'
    sessions_dir = Path('data/sessions')

    # List available backups for the date
    prefix = f'sessions/{backup_date}/'
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix=prefix
    )

    # Download and restore each session file
    for obj in response.get('Contents', []):
        key = obj['Key']
        filename = key.split('/')[-1]
        local_path = sessions_dir / filename

        s3_client.download_file(
            bucket_name,
            key,
            str(local_path)
        )
        print(f'Restored {filename}')
```

#### Telemetry Data Recovery
```python
def restore_telemetry(backup_date: str):
    """Restore telemetry CSV from compressed backup."""
    import gzip

    s3_client = boto3.client('s3')
    bucket_name = 'agent-lab-backups'

    key = f'telemetry/{backup_date}/runs.csv.gz'
    local_gz_path = Path('/tmp/runs.csv.gz')
    local_csv_path = Path('data/runs.csv')

    # Download compressed file
    s3_client.download_file(bucket_name, key, str(local_gz_path))

    # Decompress and restore
    with gzip.open(local_gz_path, 'rb') as gz_file:
        with open(local_csv_path, 'wb') as csv_file:
            csv_file.write(gz_file.read())

    print('Telemetry data restored')
```

### 3. Application Recovery

#### Emergency Deployment Script
```bash
#!/bin/bash
# scripts/emergency-deploy.sh

echo "Starting emergency deployment..."

# 1. Restore code from backup
git checkout main
git pull origin main || git pull gitlab main

# 2. Restore environment configuration
cp .env.backup .env

# 3. Restore data if needed
python scripts/restore_data.py --date $(date +%Y%m%d)

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run health checks
python -c "import app; print('Application healthy')"

# 6. Start application
python app.py &
```

## CI/CD Pipeline Validation & Rollback

### Pipeline Rollback Strategy

#### Blue-Green Deployment Pattern
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: pip install -r requirements.txt

    - name: Run tests
      run: pytest tests/ -v --tb=short

    - name: Health check
      run: |
        timeout 30 python -c "
        import sys
        try:
          import app
          print('✅ Health check passed')
        except Exception as e:
          print(f'❌ Health check failed: {e}')
          sys.exit(1)
        "

    - name: Deploy to production
      run: |
        # Blue-green deployment logic
        # 1. Deploy to staging environment first
        # 2. Run integration tests
        # 3. Switch traffic to new version
        # 4. Keep old version as rollback option

    - name: Post-deployment validation
      run: |
        # Wait for deployment to stabilize
        sleep 60

        # Run smoke tests against production
        curl -f https://agent-lab.your-domain.com/health || exit 1

        # Validate data integrity
        # Check that recent sessions are accessible
```

#### Rollback Procedures

##### Automated Deployment Rollback
The CI/CD pipeline includes automatic rollback capabilities triggered on deployment failures:

```yaml
# Automatic rollback in .github/workflows/deploy.yml
rollback:
  needs: deploy_production
  if: failure() && (needs.deploy_production.result == 'failure')
  runs-on: ubuntu-latest
  environment: production

  steps:
  - name: Trigger rollback
    run: |
      echo "❌ Production deployment failed, initiating rollback..."

      # Execute automated rollback to previous stable version
      # Includes traffic switching, validation, and notifications
```

##### Manual Rollback Workflow
For intentional rollbacks or complex scenarios, use the dedicated rollback workflow:

```yaml
# .github/workflows/rollback.yml - Manual Rollback
name: Manual Rollback

on:
  workflow_dispatch:
    inputs:
      target_environment:
        description: 'Environment to rollback'
        options: [staging, production]
      rollback_reason:
        description: 'Reason for rollback'
        required: true
      target_version:
        description: 'Specific version/commit to rollback to'
```

**Manual Rollback Steps:**
1. **Access Rollback Workflow**: Go to GitHub Actions → Manual Rollback
2. **Specify Parameters**:
   - Target environment (staging/production)
   - Reason for rollback (required)
   - Target version/commit (optional, defaults to previous)
3. **Initiate Rollback**: Click "Run workflow"
4. **Monitor Progress**: Watch workflow execution and notifications
5. **Validate Success**: Check application health and functionality

##### Emergency Rollback Procedures
For critical production incidents requiring immediate action:

1. **Immediate Assessment**: Determine if rollback is appropriate
2. **Trigger Emergency Rollback**:
   ```bash
   # Via GitHub CLI or web interface
   gh workflow run rollback.yml \
     -f target_environment=production \
     -f rollback_reason="Critical security vulnerability"
   ```
3. **Monitor Rollback**: Watch real-time status via Slack notifications
4. **Validate Recovery**: Confirm application stability within 5 minutes
5. **Post-Incident Review**: Document lessons learned

##### Rollback Validation Checklist
- [ ] Application health endpoint responds
- [ ] Core functionality tests pass
- [ ] Data integrity verified
- [ ] Performance metrics within acceptable ranges
- [ ] User access restored
- [ ] Monitoring alerts cleared
- [ ] Team notified of successful rollback

### Pipeline Validation

#### Pre-deployment Validation
```yaml
# .github/workflows/validate-deployment.yml
name: Validate Deployment

on:
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: pip install -r requirements.txt

    - name: Run full test suite
      run: pytest tests/ --cov=agents --cov=services --cov-report=xml

    - name: Validate coverage
      run: |
        COVERAGE=$(python -c "
        import xml.etree.ElementTree as ET
        root = ET.parse('coverage.xml').getroot()
        total_coverage = float(root.get('line-rate', 0)) * 100
        print(f'{total_coverage:.1f}')
        ")
        if (( $(echo "$COVERAGE < 90" | bc -l) )); then
          echo "Coverage $COVERAGE% below 90% threshold"
          exit 1
        fi

    - name: Security scan
      run: |
        # Run security vulnerability checks
        pip install safety
        safety check

    - name: Performance baseline
      run: |
        # Record performance metrics for comparison
        python -c "
        import time
        start = time.time()
        import app
        end = time.time()
        print(f'Import time: {end - start:.2f}s')
        " > performance-baseline.txt
```

## Monitoring & Alerting

### Application Monitoring
```python
# services/monitoring.py
from datetime import datetime, timedelta
import psutil
import logging

class ApplicationMonitor:
    def __init__(self):
        self.logger = logging.getLogger('agent_lab.monitoring')

    def check_data_integrity(self):
        """Verify data files are accessible and valid."""
        from services.persist import CSV_PATH, SESSIONS_DIR

        issues = []

        # Check CSV file
        if not CSV_PATH.exists():
            issues.append("Telemetry CSV file missing")
        else:
            try:
                with open(CSV_PATH, 'r') as f:
                    lines = f.readlines()
                    if len(lines) < 1:  # At least header
                        issues.append("CSV file appears corrupted")
            except Exception as e:
                issues.append(f"CSV file unreadable: {e}")

        # Check sessions directory
        if not SESSIONS_DIR.exists():
            issues.append("Sessions directory missing")
        else:
            session_files = list(SESSIONS_DIR.glob('*.json'))
            if len(session_files) == 0:
                self.logger.warning("No session files found")

        return issues

    def check_system_resources(self):
        """Monitor system resource usage."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        if cpu_percent > 90:
            self.logger.warning(f"High CPU usage: {cpu_percent}%")

        if memory.percent > 90:
            self.logger.warning(f"High memory usage: {memory.percent}%")

        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_usage': psutil.disk_usage('/').percent
        }

    def backup_health_check(self):
        """Verify backup systems are functioning."""
        # Check last backup timestamp
        # Verify backup storage accessibility
        # Validate backup data integrity
        pass
```

### Alert Configuration
```yaml
# .github/workflows/alerts.yml
name: System Alerts

on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes

jobs:
  health-check:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Health check
      run: |
        # Check application health
        if curl -f https://agent-lab.your-domain.com/health; then
          echo "✅ Application healthy"
        else
          echo "❌ Application unhealthy"
          # Send alert
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"🚨 Agent Lab application is down!"}' \
            ${{ secrets.SLACK_WEBHOOK_URL }}
        fi

    - name: Data integrity check
      run: |
        # Check data files exist and are recent
        # Alert if no new sessions in last hour
        # Alert if CSV file corrupted

    - name: Backup verification
      run: |
        # Verify recent backups exist
        # Check backup storage accessibility
        # Alert on backup failures
```

## Emergency Response Procedures

### Incident Response Plan

#### Phase 1: Detection & Assessment (0-15 minutes)
1. **Alert Review**: Check monitoring dashboards and alerts
2. **Impact Assessment**: Determine affected systems and users
3. **Severity Classification**: Critical, High, Medium, Low

#### Phase 2: Containment (15-60 minutes)
1. **Isolate Affected Systems**: Prevent further damage
2. **Implement Temporary Fixes**: Apply workarounds if available
3. **Communicate Status**: Notify stakeholders of incident

#### Phase 3: Recovery (1-4 hours)
1. **Execute Recovery Procedures**: Follow documented DR plan
2. **Validate Recovery**: Test system functionality
3. **Data Verification**: Ensure data integrity post-recovery

#### Phase 4: Post-Incident (4+ hours)
1. **Root Cause Analysis**: Investigate incident causes
2. **Documentation Updates**: Update procedures based on lessons learned
3. **Prevention Measures**: Implement fixes to prevent recurrence

### Communication Plan

#### Internal Communication
- **Incident Response Team**: Slack channel for coordination
- **Status Updates**: Regular updates during incident
- **Post-Mortem**: Detailed analysis and action items

#### External Communication
- **User Notifications**: Status page updates for outages
- **Customer Communication**: Proactive updates for critical incidents
- **Stakeholder Updates**: Regular reports on resolution progress

## Testing & Validation

### Backup Testing
```python
# tests/test_backup.py
def test_backup_sessions(tmp_path):
    """Test session data backup functionality."""
    # Create test session files
    # Run backup process
    # Verify files uploaded to mock storage
    # Validate file integrity

def test_backup_telemetry(tmp_path):
    """Test telemetry CSV backup functionality."""
    # Create test CSV data
    # Run backup process
    # Verify compression and upload
    # Validate data integrity after restore

def test_data_restore(tmp_path):
    """Test data restoration from backup."""
    # Create backup files
    # Simulate data loss
    # Run restore process
    # Verify data integrity
```

### Disaster Recovery Testing
```yaml
# .github/workflows/dr-test.yml
name: Disaster Recovery Test

on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly on the 1st
  workflow_dispatch:

jobs:
  dr-test:
    runs-on: ubuntu-latest

    steps:
    - name: Simulate data loss
      run: |
        # Remove data files
        rm -rf data/sessions/*.json
        rm -f data/runs.csv

    - name: Execute recovery
      run: |
        # Run restore procedures
        python scripts/restore_data.py --date $(date +%Y%m%d)

    - name: Validate recovery
      run: |
        # Check data integrity
        # Run application tests
        # Verify functionality
```

#### Rollback Testing Procedures
Regular testing of rollback capabilities ensures reliability:

```yaml
# .github/workflows/test-rollback.yml
name: Test Rollback Procedures

on:
  schedule:
    - cron: '0 2 1 * *'  # Monthly on the 1st
  workflow_dispatch:
    inputs:
      test_environment:
        options: [staging, production]
      full_simulation:
        description: 'Run full rollback simulation'

jobs:
  prepare_test_environment:
    name: 'Prepare Test Environment'
    outputs:
      test_commit: ${{ steps.prepare.outputs.test_commit }}

  execute_test_rollback:
    name: 'Execute Test Rollback'
    needs: prepare_test_environment

  validate_test_rollback:
    name: 'Validate Test Rollback'
    needs: execute_test_rollback

  generate_test_report:
    name: 'Generate Test Report'
    needs: [prepare_test_environment, execute_test_rollback, validate_test_rollback]
```

**Rollback Test Scenarios:**
- **Basic Rollback Test**: Rollback to previous commit in staging
- **Production Simulation**: Full deployment + failure simulation + rollback
- **Data Integrity Test**: Verify data consistency after rollback
- **Performance Validation**: Ensure rollback doesn't impact performance

**Test Execution Steps:**
1. **Schedule**: Monthly automated tests or manual trigger
2. **Environment**: Staging (default) or production (with caution)
3. **Simulation**: Optional full deployment simulation
4. **Validation**: Health checks, functionality tests, data integrity
5. **Reporting**: Automated test reports and notifications

## Maintenance & Review

### Regular Review Schedule
- **Monthly**: Review backup logs and success rates
- **Quarterly**: Test disaster recovery procedures
- **Annually**: Complete infrastructure and process audit

### Continuous Improvement
- **Monitor Backup Performance**: Track backup duration and success rates
- **Update Recovery Procedures**: Incorporate lessons from incidents
- **Technology Refresh**: Evaluate new backup and DR technologies
- **Cost Optimization**: Balance backup retention with storage costs

This comprehensive strategy ensures Agent Lab can maintain service continuity and data integrity even in the face of significant disruptions, with clear procedures for rapid recovery and minimal data loss.