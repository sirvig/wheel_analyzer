# Task 004: Deploy Redis Cache Using Docker Swarm

**Implementation Location**: `/Users/danvigliotti/Development/Webvig/webvig-ansible/playbooks/deploy_wheel_analyzer.yml`

This task is implemented in the separate webvig-ansible repository. The deployment playbook includes Redis deployment as part of the comprehensive Wheel Analyzer deployment to Docker Swarm.

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Add Redis service deployment to Ansible playbook
- [ ] Step 2: Configure Redis Docker volume and network
- [ ] Step 3: Configure Redis persistence and security
- [ ] Step 4: Add Redis health checks and resource limits
- [ ] Step 5: Test Redis deployment and connectivity
- [ ] Step 6: Verify Redis persistence and data
- [ ] Step 7: Update documentation

## Overview

Deploy Redis cache container on uss-web1 server using Docker Swarm. This task establishes the caching layer required for the Wheel Analyzer application to store and retrieve options data efficiently. Redis provides high-performance in-memory data storage with persistence for the scanner's cached results.

The deployment will:
- Deploy Redis 6.2 container via Docker Swarm
- Configure persistent storage with Docker volumes (RDB and AOF)
- Set up Redis authentication securely via Ansible vault
- Configure memory limits and eviction policies
- Enable Redis persistence for data durability
- Verify Redis connectivity and data persistence

This task is a prerequisite for Task 005 (automated scanner cron job) as the scanner requires Redis to cache options data for performance.

## Current State Analysis

### Existing Infrastructure

**Local Development Setup:**
- Redis runs via docker-compose on port 36379
- Uses `app_main` Docker network
- Password: "myStrongPassword" (from CLAUDE.md)
- No persistence configured in local setup

**Docker Configuration:**
- `docker-compose.yml` defines local Redis service as `app_redis`
- Image: `library/redis:6.2-alpine`
- Container name: `app_redis`, hostname: `redis`
- Environment: Password set via Redis command arguments
- No volumes configured (ephemeral in local dev)

**Django Configuration:**
- Redis used by scanner app for caching options data
- Connection via `REDIS_URL` or similar environment variable
- Scanner management commands depend on Redis availability

**Deployment Configuration (from Task 002):**
- Ansible playbook at `ansible/playbooks/deploy.yml` (to be created)
- Environment template at `ansible/templates/.env.docker.j2` (to be created)
- Vault-encrypted credentials in `ansible/inventory/production.yml` (to be created)

**Existing Ansible Redis Deployment:**
- Current deployment in `webvig-ansible` uses Redis 7-alpine
- Deployed as part of `redis_metrics` stack with redis_exporter
- Port: 6379 (standard)
- Persistence enabled with `--appendonly yes`

### Missing Components

- Redis deployment in Wheel Analyzer Ansible playbook
- Production Redis configuration with authentication
- Redis persistence configuration (RDB + AOF)
- Health check and validation tasks
- Integration with `app_main` network for application access

## Target State

### Redis Container Configuration

**Service Name:** `wheel_analyzer_redis`
**Image:** `redis:6.2-alpine`
**Network:** `app_main` (shared with PostgreSQL and application containers)
**Port:** 6379 (internal to Docker network, not exposed externally for security)

**Environment Variables:**
- Redis authentication via password (set in command)
- Password from vault: `{{ wheel_analyzer.redis_password }}`

**Volumes:**
- `wheel_analyzer_redis_data`: Redis data directory (`/data`)

**Deployment Method:**
- Docker Swarm service deployment (consistent with PostgreSQL approach)
- Persistent storage via named volume
- Restart policy: Always restart on failure
- Placement: Worker nodes

**Redis Configuration:**
- Authentication: Required password
- Persistence: RDB + AOF (Append-Only File)
- Memory limit: 512MB (configurable)
- Maxmemory policy: `allkeys-lru` (evict least recently used keys when memory full)
- Save intervals: `900 1 300 10 60 10000` (RDB snapshots)

### Security Configuration

- Redis password stored in Ansible vault
- Redis not exposed to external network (internal Docker network only)
- Application connects via `REDIS_URL` environment variable
- AOF persistence for crash recovery

### Performance Configuration

- Memory limit prevents Redis from consuming all server memory
- LRU eviction policy ensures cache stays within memory limits
- AOF persistence provides durability with minimal performance impact
- RDB snapshots provide point-in-time backups

## Implementation Steps

### Step 1: Add Redis Service Deployment to Ansible Playbook

Add tasks to deploy Redis service using Docker Swarm in `ansible/playbooks/deploy.yml`:

**Add tasks:**
```yaml
- name: Create Redis data volume
  docker_volume:
    name: wheel_analyzer_redis_data
    state: present

- name: Deploy Redis service to Docker Swarm
  docker_swarm_service:
    name: wheel_analyzer_redis
    image: redis:6.2-alpine
    state: present
    networks:
      - app_main
    mounts:
      - source: wheel_analyzer_redis_data
        target: /data
        type: volume
    args:
      - redis-server
      - --requirepass
      - "{{ wheel_analyzer.redis_password }}"
      - --appendonly
      - "yes"
      - --appendfsync
      - "everysec"
      - --save
      - "900 1"
      - --save
      - "300 10"
      - --save
      - "60 10000"
      - --maxmemory
      - "512mb"
      - --maxmemory-policy
      - "allkeys-lru"
    placement:
      constraints:
        - node.role == worker
    restart_config:
      condition: any
      delay: 5s
      max_attempts: 3
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    limits:
      memory: 512M
    reservations:
      memory: 256M
```

**Redis Command Arguments Explained:**
- `--requirepass`: Set password for authentication
- `--appendonly yes`: Enable AOF persistence
- `--appendfsync everysec`: Sync AOF to disk every second (balance between performance and durability)
- `--save 900 1`: Save RDB snapshot if 1 key changed in 900 seconds (15 min)
- `--save 300 10`: Save RDB snapshot if 10 keys changed in 300 seconds (5 min)
- `--save 60 10000`: Save RDB snapshot if 10000 keys changed in 60 seconds (1 min)
- `--maxmemory 512mb`: Maximum memory Redis can use
- `--maxmemory-policy allkeys-lru`: Evict least recently used keys when maxmemory reached

**Notes:**
- Volume name uses `wheel_analyzer_` prefix for clarity
- Service name: `wheel_analyzer_redis` (distinguishes from other Redis instances)
- Health check ensures Redis is ready before application starts
- Restart policy ensures Redis survives node failures
- Memory limits prevent Redis from consuming all server memory
- Placement on worker nodes for resource isolation

**Files to modify:**
- `ansible/playbooks/deploy.yml` (to be created in Task 002)

**Acceptance:**
- Redis service deployment tasks are added to playbook
- Volume is created before service deployment
- Network connection is configured
- Redis password is templated from vault-encrypted inventory
- Health check is configured
- Resource limits are set

### Step 2: Configure Redis Docker Volume and Network

Ensure Docker network and volumes are properly configured:

**Network configuration (verify from Task 002):**
```yaml
- name: Create Docker network for wheel-analyzer
  docker_network:
    name: app_main
    state: present
    driver: overlay
    scope: swarm
```

**Note:** For Docker Swarm, network must use `overlay` driver with `swarm` scope to allow service-to-service communication across nodes.

**Volume configuration:**
- Volume uses local driver (default)
- Data persists across service updates and node restarts
- Redis data includes both RDB snapshots and AOF logs

**Verification tasks:**
```yaml
- name: Verify Redis volume exists
  docker_volume_info:
    name: wheel_analyzer_redis_data
  register: volume_info

- name: Verify app_main network exists
  docker_network_info:
    name: app_main
  register: network_info

- name: Display network and volume info
  debug:
    msg:
      - "Network: {{ network_info.network.Name }}"
      - "Volume: {{ volume_info.volume.Name }}"
```

**Files to modify:**
- `ansible/playbooks/deploy.yml`

**Acceptance:**
- Network creation happens before Redis deployment
- Network uses overlay driver for Swarm
- Volume is created with correct name
- Verification tasks confirm infrastructure is ready

### Step 3: Configure Redis Persistence and Security

Add tasks to verify Redis authentication and persistence configuration:

**Test Redis authentication:**
```yaml
- name: Wait for Redis to be ready
  shell: >
    docker exec $(docker ps -q -f name=wheel_analyzer_redis)
    redis-cli -a "{{ wheel_analyzer.redis_password }}" ping
  register: result
  until: result.stdout == "PONG"
  retries: 10
  delay: 3
  no_log: true
```

**Verify persistence configuration:**
```yaml
- name: Verify Redis persistence settings
  shell: >
    docker exec $(docker ps -q -f name=wheel_analyzer_redis)
    redis-cli -a "{{ wheel_analyzer.redis_password }}" CONFIG GET save
  register: redis_config
  no_log: true

- name: Display Redis persistence configuration
  debug:
    var: redis_config.stdout_lines
```

**Verify AOF configuration:**
```yaml
- name: Verify Redis AOF settings
  shell: >
    docker exec $(docker ps -q -f name=wheel_analyzer_redis)
    redis-cli -a "{{ wheel_analyzer.redis_password }}" CONFIG GET appendonly
  register: redis_aof
  no_log: true

- name: Ensure AOF is enabled
  assert:
    that:
      - "'yes' in redis_aof.stdout"
    fail_msg: "Redis AOF persistence is not enabled"
    success_msg: "Redis AOF persistence is enabled"
```

**Notes:**
- `no_log: true` prevents password from appearing in Ansible output
- Verification ensures Redis is configured correctly
- Both RDB and AOF persistence should be active

**Files to modify:**
- `ansible/playbooks/deploy.yml`

**Acceptance:**
- Redis authentication works with vault password
- RDB save intervals are configured correctly
- AOF persistence is enabled
- Verification tasks pass without errors

### Step 4: Add Redis Health Checks and Resource Limits

Configure health checks and resource limits for Redis:

**Health check configuration:**
- Already included in service definition (Step 1)
- Uses `redis-cli incr ping` command
- Interval: 10 seconds between checks
- Timeout: 3 seconds for each check
- Retries: 3 failed checks before marking unhealthy

**Resource limits configuration:**
- Already included in service definition (Step 1)
- Memory limit: 512MB hard limit
- Memory reservation: 256MB guaranteed
- Prevents Redis from consuming all server memory

**Monitor service health:**
```yaml
- name: Check Redis service status
  docker_service_info:
    name: wheel_analyzer_redis
  register: redis_service

- name: Display Redis service health
  debug:
    msg:
      - "Service State: {{ redis_service.service.UpdateStatus.State }}"
      - "Replicas: {{ redis_service.service.Spec.Mode.Replicated.Replicas }}"
```

**Files to modify:**
- `ansible/playbooks/deploy.yml`

**Acceptance:**
- Health check is properly configured
- Resource limits prevent memory exhaustion
- Service reports as healthy after deployment
- Monitoring tasks show service status

### Step 5: Test Redis Deployment and Connectivity

Test the Redis deployment locally using Ansible:

**Syntax check:**
```bash
cd ansible
ansible-playbook playbooks/deploy.yml --syntax-check
```

**Check mode (dry run):**
```bash
ansible-playbook playbooks/deploy.yml --check
```

**Deploy to server:**
```bash
ansible-playbook playbooks/deploy.yml
```

**Verification commands:**
```bash
# SSH to server
ssh uss-web1.webviglabs.com

# Check Redis service is running
docker service ls | grep wheel_analyzer_redis

# Check service details
docker service ps wheel_analyzer_redis

# Check service logs
docker service logs wheel_analyzer_redis

# Verify volume exists
docker volume ls | grep wheel_analyzer_redis

# Test Redis connectivity (replace PASSWORD with actual password)
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  redis-cli -a PASSWORD ping

# Test authentication required
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  redis-cli ping  # Should fail without password

# Check network connectivity
docker network inspect app_main
```

**Files affected:**
- Redis service on uss-web1.webviglabs.com
- Docker volume on uss-web1.webviglabs.com

**Acceptance:**
- Playbook deploys without errors
- Redis service is running
- Service is connected to `app_main` network
- Redis is accessible from within Docker network with password
- Redis denies access without authentication
- Volume is mounted correctly
- Logs show no errors

### Step 6: Verify Redis Persistence and Data

Verify that Redis persistence is working correctly:

**Test data persistence:**
```bash
# SSH to server
ssh uss-web1.webviglabs.com

# Set a test key (replace PASSWORD with actual password)
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  redis-cli -a PASSWORD SET test_key "test_value"

# Verify key exists
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  redis-cli -a PASSWORD GET test_key

# Check if AOF file exists
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  ls -la /data/

# Verify RDB snapshot exists (may take time based on save intervals)
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  ls -la /data/*.rdb

# Verify AOF file exists
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  ls -la /data/*.aof
```

**Test persistence after restart:**
```bash
# Update service to trigger restart (no changes, just refresh)
docker service update --force wheel_analyzer_redis

# Wait for service to be ready
sleep 10

# Verify test key still exists after restart
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  redis-cli -a PASSWORD GET test_key

# Clean up test key
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  redis-cli -a PASSWORD DEL test_key
```

**Expected files in /data directory:**
- `appendonly.aof` - AOF persistence file
- `dump.rdb` - RDB snapshot file (created after save intervals)

**Files affected:**
None - this is verification only

**Acceptance:**
- Test data can be written to Redis
- Test data can be read from Redis
- AOF file is created in /data directory
- RDB snapshot is created (or will be based on save intervals)
- Data persists after service restart
- Test cleanup succeeds

### Step 7: Update Documentation

Update project documentation with Redis deployment information:

**Update README.md:**
Add "Redis Cache Deployment" section:
- Explain Redis deployment via Ansible and Docker Swarm
- Document connection details (internal to Docker network)
- Explain volume configuration and persistence
- Document persistence strategy (RDB + AOF)
- Document memory limits and eviction policies
- Explain health check configuration

**Update ansible/playbooks/deploy.yml comments:**
- Add comments explaining Redis deployment tasks
- Document Redis configuration arguments
- Explain persistence settings
- Document health check and resource limits

**Update reference/ROADMAP.md:**
- Add Task 004 to task list
- Update Phase 1 dependencies
- Reference this task file

**Files to modify:**
- `README.md` - Add Redis deployment documentation
- `ansible/playbooks/deploy.yml` - Add explanatory comments
- `reference/ROADMAP.md` - Add task reference

**Acceptance:**
- README.md contains clear Redis deployment documentation
- Deployment process is explained step-by-step
- Troubleshooting tips are included
- ROADMAP.md references this task
- Comments in playbook explain each step

## Acceptance Criteria

### Functional Requirements

- [ ] Redis 6.2 service is deployed on uss-web1 via Docker Swarm
- [ ] Redis is accessible via `app_main` Docker network
- [ ] Redis password is configured via Ansible vault
- [ ] Redis requires authentication for all operations
- [ ] Redis data persists across service restarts
- [ ] Cache operations work correctly

### Infrastructure Requirements

- [ ] Docker volume is created for Redis data
- [ ] Redis service is connected to `app_main` network
- [ ] Service has health check configured
- [ ] Restart policy is configured for high availability
- [ ] Redis is not exposed to external network
- [ ] Volume uses persistent storage

### Deployment Requirements

- [ ] Ansible playbook includes Redis deployment
- [ ] Playbook deploys without errors
- [ ] Playbook is idempotent (can run multiple times safely)
- [ ] Redis password is templated from vault-encrypted inventory
- [ ] Service is deployed using Docker Swarm
- [ ] Placement constraints route to worker nodes

### Security Requirements

- [ ] Redis password stored in Ansible vault
- [ ] `.env.docker` file has 0600 permissions (from Task 002)
- [ ] Redis requires password authentication
- [ ] Redis not exposed to external network
- [ ] Only application containers can access Redis
- [ ] Password not logged in Ansible output

### Performance Requirements

- [ ] Memory limit is set to 512MB
- [ ] Memory reservation is set to 256MB
- [ ] Maxmemory policy is configured (allkeys-lru)
- [ ] Health checks don't impact performance
- [ ] Resource limits prevent memory exhaustion

### Persistence Requirements

- [ ] AOF persistence is enabled
- [ ] AOF sync is configured (everysec)
- [ ] RDB snapshots are configured with save intervals
- [ ] Data persists in Docker volume
- [ ] AOF file exists in /data directory
- [ ] RDB snapshot is created based on save intervals

### Documentation Requirements

- [ ] README.md explains Redis deployment
- [ ] Connection configuration is documented
- [ ] Persistence strategy is documented
- [ ] Troubleshooting steps are included
- [ ] Playbook has explanatory comments
- [ ] ROADMAP.md references this task

## Files Involved

### Modified Files

- `ansible/playbooks/deploy.yml` - Add Redis deployment tasks
- `ansible/inventory/production.yml` - Add Redis password (vault-encrypted)
- `ansible/templates/.env.docker.j2` - Ensure REDIS_URL is templated
- `README.md` - Add Redis deployment documentation
- `reference/ROADMAP.md` - Add task reference

### Server Files (uss-web1.webviglabs.com)

- Redis service: `wheel_analyzer_redis`
- Docker volume: `wheel_analyzer_redis_data`
- Docker network: `app_main` (shared with PostgreSQL and application)
- Environment file: `/etc/wheel-analyzer/.env.docker` (from Task 002)

### Potentially Affected Files

- `.gitignore` - Ensure local `.env` files are excluded
- `docker-compose.yml` - Local dev setup (no changes needed)
- `scanner/management/commands/cron_scanner.py` - Uses Redis (no changes needed)

## Notes

### Redis Connectivity

**Connection String Format:**
```
REDIS_URL=redis://:password@wheel_analyzer_redis:6379/0
```

**Key points:**
- Hostname: `wheel_analyzer_redis` (service name, resolvable within Docker overlay network)
- Port: `6379` (internal Redis port)
- Database: `0` (default database)
- Password: Required (from vault)
- Network: `app_main` (containers must be on this network)

### Persistence Strategy

**AOF (Append-Only File):**
- Every write operation is logged
- Synced to disk every second (everysec)
- Provides crash recovery with minimal data loss (up to 1 second)
- File grows continuously, rewritten periodically by Redis

**RDB (Redis Database Snapshots):**
- Point-in-time snapshots at configured intervals
- Compact binary format
- Faster to load on restart than AOF
- May lose data between snapshots

**Combined approach:**
- AOF for durability and minimal data loss
- RDB for faster restarts and backups
- Redis loads AOF on startup if available (prioritizes durability)

### Memory Management

**Maxmemory Configuration:**
- Hard limit: 512MB (prevents Redis from consuming all server memory)
- LRU eviction: Evicts least recently used keys when limit reached
- Appropriate for cache usage (scanner results)
- Adjust limit based on server capacity and workload

**Memory monitoring:**
```bash
# Check Redis memory usage
docker exec $(docker ps -q -f name=wheel_analyzer_redis) \
  redis-cli -a PASSWORD INFO memory
```

### Health Check

Redis health check ensures:
- Redis process is running
- Redis is accepting connections
- Redis can execute commands

Health check command: `redis-cli --raw incr ping`

### Volume Management

**Data persistence:**
- All data stored in `wheel_analyzer_redis_data` volume
- Volume persists even if service is removed
- Volume includes AOF file and RDB snapshots

**Volume location:**
- Managed by Docker on the node where service is running
- Accessible via Docker commands on that node

### Comparison with Local Development

**Local (docker-compose):**
- Container: `app_redis`, hostname: `redis`
- Port: 36379 (exposed to host)
- Password: "myStrongPassword"
- No persistence (ephemeral)

**Production (uss-web1):**
- Service: `wheel_analyzer_redis`, hostname: same
- Port: 6379 (internal only)
- Password: From vault-encrypted inventory
- Persistence enabled (AOF + RDB)
- Environment: `/etc/wheel-analyzer/.env.docker` (deployed via Ansible)

### Docker Swarm Considerations

**Service deployment:**
- Services are distributed across Swarm nodes
- Volume is local to the node running the Redis task
- If node fails, service restarts on another node (volume may not follow without shared storage)
- For production, consider shared storage solutions if high availability is required

**Network:**
- Overlay network allows service-to-service communication across nodes
- Service name provides DNS resolution within Swarm
- No need to know which node is running which service

## Dependencies

- Task 002 completed (Ansible consolidation)
  - `ansible/` directory structure exists
  - `ansible.cfg` configured
  - `vault-password.txt` set up
  - Inventory file created with vault-encrypted credentials
  - `.env.docker.j2` template created
- Docker Swarm initialized on uss-web1.webviglabs.com
- SSH access to uss-web1.webviglabs.com
- `app_main` Docker overlay network creation (added in Task 002 or Task 003)
