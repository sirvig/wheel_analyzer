# Task 005: Implement Automated Scanner Cron Job Deployment

**Implementation Location**: `/Users/danvigliotti/Development/Webvig/webvig-ansible/playbooks/deploy_wheel_analyzer.yml`

This task is implemented in the separate webvig-ansible repository. The deployment playbook includes cron job configuration as part of the comprehensive Wheel Analyzer deployment to Docker Swarm.

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Add cron job task to deployment playbook
- [ ] Step 2: Configure cron schedule and command
- [ ] Step 3: Ensure Docker network availability
- [ ] Step 4: Test cron job deployment
- [ ] Step 5: Verify cron execution
- [ ] Step 6: Monitor and validate scanning
- [ ] Step 7: Update documentation

## Overview

Implement automated options scanning via cron job on the uss-web1 server. This completes **Phase 1: Option scanner MVP** from the roadmap. The cron job will:

- Run every 15 minutes between 10 AM and 4 PM (trading hours) on Monday-Friday
- Execute the `cron_scanner` Django management command in a Docker container
- Use the environment configuration from `/etc/wheel-analyzer/.env.docker`
- Connect to existing PostgreSQL and Redis services via `app_main` network

This enables automated discovery of options trading opportunities without manual intervention.

## Current State Analysis

### Existing Components

**Django Management Command:**
- `scanner/management/commands/cron_scanner.py` exists
- Scans options for stocks in the OptionsWatch list
- Caches results in Redis for performance
- Designed to be run via cron

**Docker Infrastructure:**
- Docker image built and pushed to ghcr.io
- Image contains full Django application
- Command: `uv run manage.py cron_scanner`

**Deployment Configuration (from Task 002):**
- Ansible playbook at `ansible/playbooks/deploy.yml`
- Environment file template at `ansible/templates/.env.docker.j2`
- Environment deployed to `/etc/wheel-analyzer/.env.docker`
- File permissions set to `0600`

### Missing Components

- Cron job creation in Ansible playbook
- Docker network `app_main` creation
- Cron job testing and validation

## Target State

### Cron Job Configuration

**Schedule:** `*/15 10-16 * * 1-5`
- Every 15 minutes
- Between 10:00 AM and 4:59 PM
- Every Monday-Friday
- US/Eastern timezone (server timezone)

**Command:**
```bash
docker run --rm --network app_main --env-file /etc/wheel-analyzer/.env.docker ghcr.io/sirvig/wheel-analyzer:latest uv run manage.py cron_scanner
```

**Flags explained:**
- `--rm`: Automatically remove container after execution (no cleanup needed)
- `--network app_main`: Connect to Docker network for PostgreSQL/Redis access
- `--env-file`: Load environment variables from deployed file
- `ghcr.io/sirvig/wheel-analyzer:latest`: Use latest Docker image
- `uv run manage.py cron_scanner`: Execute scanner management command

### Docker Network

**Network name:** `app_main`
- Type: Bridge network (or Swarm overlay if using Docker Swarm)
- Purpose: Allow cron-launched containers to communicate with PostgreSQL and Redis
- Persistence: Created once, used by all containers

## Implementation Steps

### Step 1: Add Cron Job Task to Deployment Playbook

Update `ansible/playbooks/deploy.yml` to include cron job creation:

**Add task:**
```yaml
- name: Create cron job for automated options scanning
  cron:
    name: "Wheel Analyzer - Automated Options Scanner"
    minute: "*/15"
    hour: "10-16"
    weekday: "1-5"
    job: "docker run --rm --network app_main --env-file /etc/wheel-analyzer/.env.docker ghcr.io/sirvig/wheel-analyzer:latest uv run manage.py cron_scanner >> /var/log/wheel-analyzer/cron.log 2>&1"
    user: root
    state: present
```

**Notes:**
- Logs are redirected to `/var/log/wheel-analyzer/cron.log`
- User is `root` to ensure Docker access
- State `present` ensures cron job exists

**Files to modify:**
- `ansible/playbooks/deploy.yml`

**Acceptance:**
- Cron task is added to playbook
- Schedule matches roadmap specification
- Command is correct and complete
- Logging is configured

### Step 2: Configure Cron Schedule and Command

Verify the cron configuration:

**Schedule validation:**
- `*/15`: Every 15 minutes
- `10-16`: Hours 10 through 16 (10:00 AM - 4:59 PM)
- `1-5`: Weekdays Monday - Friday
- Timezone: Assumes server is set to US/Eastern

**Command validation:**
- Network name: `app_main`
- Environment file path: `/etc/wheel-analyzer/.env.docker`
- Image name: `ghcr.io/sirvig/wheel-analyzer:latest`
- Management command: `cron_scanner`

**Add log directory creation:**
```yaml
- name: Create log directory for cron jobs
  file:
    path: /var/log/wheel-analyzer
    state: directory
    mode: '0755'
    owner: root
    group: root
```

**Files to modify:**
- `ansible/playbooks/deploy.yml`

**Acceptance:**
- Log directory is created before cron job
- Directory has correct permissions
- Cron job can write to log file

### Step 3: Ensure Docker Network Availability

Add task to create Docker network if it doesn't exist:

**Add task:**
```yaml
- name: Create Docker network for wheel-analyzer
  docker_network:
    name: app_main
    state: present
    driver: bridge
```

**Note:** If using Docker Swarm, change driver to `overlay` and add `scope: swarm`.

**Files to modify:**
- `ansible/playbooks/deploy.yml`

**Acceptance:**
- Network creation task is added
- Network is created before cron job task
- Network configuration matches infrastructure needs

### Step 4: Test Cron Job Deployment

Deploy the updated playbook to uss-web1:

**Deployment steps:**
1. Run syntax check:
```bash
cd ansible
ansible-playbook playbooks/deploy.yml --syntax-check
```

2. Run in check mode:
```bash
ansible-playbook playbooks/deploy.yml --check
```

3. Deploy to server:
```bash
ansible-playbook playbooks/deploy.yml
```

**Verification:**
```bash
# SSH to server and check cron
ssh uss-web1.webviglabs.com
crontab -l | grep wheel-analyzer
```

**Files affected:**
- Cron configuration on uss-web1.webviglabs.com

**Acceptance:**
- Playbook deploys without errors
- Cron job appears in server crontab
- Log directory exists
- Docker network exists

### Step 5: Verify Cron Execution

Manually trigger the cron command to verify it works:

**Manual test:**
```bash
# SSH to server
ssh uss-web1.webviglabs.com

# Verify environment file exists
ls -la /etc/wheel-analyzer/.env.docker

# Verify Docker network exists
docker network ls | grep app_main

# Run the cron command manually
docker run --rm --network app_main --env-file /etc/wheel-analyzer/.env.docker ghcr.io/sirvig/wheel-analyzer:latest uv run manage.py cron_scanner
```

**Check for errors:**
- Database connection errors
- Redis connection errors
- API key issues
- Permission issues

**Files affected:**
None - this is verification only

**Acceptance:**
- Command executes without errors
- Database connection succeeds
- Redis connection succeeds
- Options data is scanned and cached

### Step 6: Monitor and Validate Scanning

Monitor the cron job execution:

**Wait for scheduled execution:**
- Check cron log: `tail -f /var/log/wheel-analyzer/cron.log`
- Verify job runs at scheduled times
- Check for errors or failures

**Validate data:**
- Connect to Redis: `redis-cli -h localhost -p 36379 -a myStrongPassword`
- Check for cached options data: `KEYS scanner:*`
- Verify data freshness: Check timestamps

**Monitoring period:**
- At least one hour (4 executions)
- Verify consistent execution

**Acceptance:**
- Cron job executes on schedule
- No errors in logs
- Options data is cached in Redis
- Data is fresh and updated

### Step 7: Update Documentation

Update project documentation with cron deployment information:

**Update README.md:**
- Add "Automated Scanning" section
- Explain cron schedule and purpose
- Document how to check cron status
- Document log location

**Update ROADMAP.md:**
- Mark Phase 1 as completed ✅
- Reference this task file
- Update status

**Files to modify:**
- `README.md`
- `reference/ROADMAP.md`

**Acceptance:**
- README.md documents automated scanning
- ROADMAP.md reflects Phase 1 completion
- Documentation is clear and accurate

## Acceptance Criteria

### Functional Requirements

- [ ] Cron job is created on uss-web1 server
- [ ] Cron job runs every 15 minutes from 10 AM to 4 PM
- [ ] Docker container launches successfully
- [ ] Scanner command executes without errors
- [ ] Options data is cached in Redis
- [ ] Container auto-removes after execution

### Infrastructure Requirements

- [ ] Docker network `app_main` exists
- [ ] Network provides access to PostgreSQL and Redis
- [ ] Environment file exists at `/etc/wheel-analyzer/.env.docker`
- [ ] Environment file has correct permissions (0600)
- [ ] Log directory exists at `/var/log/wheel-analyzer/`

### Deployment Requirements

- [ ] Ansible playbook includes cron job creation
- [ ] Ansible playbook includes network creation
- [ ] Ansible playbook includes log directory creation
- [ ] Playbook deploys without errors
- [ ] Playbook is idempotent (can run multiple times safely)

### Monitoring Requirements

- [ ] Cron execution is logged to `/var/log/wheel-analyzer/cron.log`
- [ ] Logs are accessible and readable
- [ ] Errors are captured in logs
- [ ] Log rotation is configured (optional but recommended)

### Documentation Requirements

- [ ] README.md explains automated scanning
- [ ] Cron schedule is documented
- [ ] Log location is documented
- [ ] Troubleshooting steps are included
- [ ] ROADMAP.md reflects completion

## Files Involved

### Modified Files

- `ansible/playbooks/deploy.yml` - Add cron job, network, and log directory tasks
- `README.md` - Add automated scanning documentation
- `reference/ROADMAP.md` - Mark Phase 1 complete

### Server Files (uss-web1.webviglabs.com)

- `/etc/wheel-analyzer/.env.docker` - Environment configuration (from Task 002)
- `/var/cron/tabs/root` - Cron configuration (managed by Ansible)
- `/var/log/wheel-analyzer/cron.log` - Cron execution log
- Docker network `app_main` - Network configuration

### Potentially Affected Files

- `scanner/management/commands/cron_scanner.py` - May need updates if issues found
- Redis data - Will contain cached scanner results

## Notes

### Timing Considerations

- Market hours: 9:30 AM - 4:00 PM Eastern
- Cron runs: 10:00 AM - 4:59 PM Eastern (aligned with market hours)
- Pre-market scanning starts at 10:00 AM
- Continues through market close

### Resource Considerations

- Each container execution is ephemeral (auto-removed)
- Database connections are pooled
- Redis cache has TTL settings
- Monitor server resources if needed

### Error Handling

- Docker will retry if container fails to start
- Management command should handle API errors gracefully
- Logs should capture all errors for debugging
- Consider adding alert mechanisms for failures

### Future Enhancements

- Add email/Slack notifications for failures
- Implement log rotation with logrotate
- Add monitoring/alerting integration
- Consider running additional scans (e.g., SMA calculations)

## Dependencies

- Task 002 completed (Ansible consolidation)
- Docker image published to ghcr.io
- PostgreSQL accessible on uss-web1
- Redis accessible on uss-web1
- SSH access to uss-web1.webviglabs.com
- `cron_scanner` management command tested and working
