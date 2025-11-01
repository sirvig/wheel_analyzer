# Task 002: Set up Ansible Deployment in webvig-ansible Repository

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Create feature branch in webvig-ansible repository
- [ ] Step 2: Create templates/wheel_analyzer directory and .env.docker.j2
- [ ] Step 3: Update inventory/webvig.yml with all required variables
- [ ] Step 4: Rewrite playbooks/deploy_wheel_analyzer.yml for Docker Swarm
- [ ] Step 5: Test playbook syntax and validate configuration
- [ ] Step 6: Commit changes to feature branch
- [ ] Step 7: Document deployment process

## Overview

Set up Ansible deployment configuration for Wheel Analyzer in the separate `webvig-ansible` repository located at `/Users/danvigliotti/Development/Webvig/webvig-ansible`. This keeps infrastructure-as-code separate from application code while enabling automated deployment to uss-web1.webviglabs.com.

The deployment will:
- Work in the webvig-ansible repository (not wheel-analyzer)
- Create dedicated template directory for wheel-analyzer environment configuration
- Update inventory with all necessary vault-encrypted variables
- Rewrite deployment playbook to use Docker Swarm services
- Deploy PostgreSQL, Redis, and cron job for automated scanning
- Use `/etc/wheel-analyzer/` path for configuration files on server

## Current State Analysis

### Existing Ansible Configuration (webvig-ansible repo)

Located at: `/Users/danvigliotti/Development/Webvig/webvig-ansible/`

**Key files:**
- `playbooks/deploy_wheel_analyzer.yml` - Partially complete, needs full rewrite
- `templates/.env.docker.j2` - Exists at root level, needs to be in dedicated directory
- `inventory/webvig.yml` - Contains wheel-analyzer variables with vault encryption

**Issues identified:**
1. Template needs dedicated directory: `templates/wheel_analyzer/.env.docker.j2`
2. Playbook needs complete rewrite for Docker Swarm deployment
3. Must deploy PostgreSQL, Redis, and cron job (not just image pull)
4. Network must use overlay driver with swarm scope

### Wheel-Analyzer Project Structure

Currently has:
- No ansible/ directory (deployment stays in webvig-ansible)
- Task files document specifications
- Docker image build capability (Dockerfile, docker-compose.yml for dev)

## Target State

### Webvig-Ansible Repository Structure

```
webvig-ansible/
├── playbooks/
│   └── deploy_wheel_analyzer.yml     # Fully rewritten for Docker Swarm
├── inventory/
│   └── webvig.yml                     # Updated with all required variables
└── templates/
    └── wheel_analyzer/
        └── .env.docker.j2             # Dedicated template file
```

### Deployment Configuration

- Environment file location: `/etc/wheel-analyzer/.env.docker` (on server)
- File permissions: `0600` for security
- Docker network: `app_main` (overlay, scope: swarm)
- Service names: `wheel_analyzer_db`, `wheel_analyzer_redis`
- Cron schedule: `*/15 10-16 * * 1-5` (weekdays only)

## Implementation Steps

### Step 1: Create Feature Branch in webvig-ansible Repository

Create a new feature branch for this work:

```bash
cd /Users/danvigliotti/Development/Webvig/webvig-ansible
git checkout -b feature/wheel-analyzer-docker-swarm-deployment
```

**Working directory:** `/Users/danvigliotti/Development/Webvig/webvig-ansible`

**Acceptance:**
- Feature branch created and checked out
- Clean working directory ready for changes

### Step 2: Create templates/wheel_analyzer Directory and .env.docker.j2

Create dedicated template directory and move/create environment template:

**Create directory:**
```bash
mkdir -p templates/wheel_analyzer
```

**Create template file:** `templates/wheel_analyzer/.env.docker.j2`

Template should include all environment variables for Django app:

**Django Settings:**
- `SECRET_KEY` from `{{ wheel_analyzer.django.secret }}`
- `ALLOWED_HOSTS` from `{{ wheel_analyzer.django.allowed_hosts }}`
- `DEBUG` from `{{ wheel_analyzer.django.debug }}`
- `LOGLEVEL` from `{{ wheel_analyzer.django.loglevel }}`
- `ENVIRONMENT` from `{{ wheel_analyzer.django.environment }}`
- `DJANGO_MANAGEPY_MIGRATE` from `{{ wheel_analyzer.django.migrate }}`

**Database Connection:**
- `DATABASE_URL` using service name `wheel_analyzer_db`
- Individual PostgreSQL variables (POSTGRES_USER, POSTGRES_PASSWORD, etc.)

**Redis Connection:**
- `REDIS_URL` using service name `wheel_analyzer_redis`

**API Configuration:**
- AlphaVantage API key and URL
- MarketData API key and URL

**GHCR Credentials:**
- GitHub Container Registry username and token

**Key change:** Database and Redis hosts must use Docker Swarm service names:
- Database host: `wheel_analyzer_db` (not external server)
- Redis host: `wheel_analyzer_redis` (not external server)

**Files to create:**
- `templates/wheel_analyzer/.env.docker.j2`

**Source reference:**
- Copy from existing `templates/.env.docker.j2` and adapt
- Update service hostnames for Swarm deployment

**Acceptance:**
- Template directory created
- Template file uses correct Jinja2 variable references
- All required environment variables are included
- Service names match Docker Swarm deployment

### Step 3: Update inventory/webvig.yml with All Required Variables

Verify and update the wheel_analyzer section in inventory:

**Required variable structure:**
```yaml
wheel_analyzer:
  database:
    server: wheel_analyzer_db  # Docker Swarm service name
    port: 5432
    database: wheel_analyzer
    user: !vault |
      <encrypted user>
    pass: !vault |
      <encrypted password>
  redis:
    server: wheel_analyzer_redis  # Docker Swarm service name
    port: 6379
    pass: !vault |
      <encrypted password>
  django:
    secret: !vault |
      <encrypted secret key>
    allowed_hosts: "*,"
    debug: FALSE
    loglevel: INFO
    environment: PRODUCTION
    migrate: on
  alphavantage:
    url_base: https://www.alphavantage.co/query
    api_key: !vault |
      <encrypted key>
  marketdata:
    url_base: https://api.marketdata.app/v1
    api_key: !vault |
      <encrypted key>
  ghcr:
    username: !vault |
      <encrypted username>
    token: !vault |
      <encrypted token>
```

**Key changes:**
- Database server should reference Docker Swarm service (internal)
- Redis server should reference Docker Swarm service (internal)
- Environment should be PRODUCTION (not LOCAL)

**Files to modify:**
- `inventory/webvig.yml`

**Acceptance:**
- All necessary variables are present
- Vault-encrypted values are preserved
- Service names match Docker Swarm deployment
- Configuration is consistent with template

### Step 4: Rewrite playbooks/deploy_wheel_analyzer.yml for Docker Swarm

Completely rewrite the deployment playbook using specifications from Tasks 003, 004, and 005.

**Playbook structure:**

```yaml
---
- name: Deploy Wheel Analyzer to Docker Swarm
  hosts: swarm_workers
  become: yes

  vars:
    ghcr_username: "{{ wheel_analyzer.ghcr.username }}"
    ghcr_token: "{{ wheel_analyzer.ghcr.token }}"

  tasks:
    # Infrastructure setup
    - name: Create /etc/wheel-analyzer directory
      file:
        path: /etc/wheel-analyzer
        state: directory
        mode: '0755'

    - name: Deploy .env.docker file
      template:
        src: ../templates/wheel_analyzer/.env.docker.j2
        dest: /etc/wheel-analyzer/.env.docker
        mode: '0600'

    - name: Create log directory for cron jobs
      file:
        path: /var/log/wheel-analyzer
        state: directory
        mode: '0755'

    - name: Create Docker overlay network for wheel-analyzer
      docker_network:
        name: app_main
        state: present
        driver: overlay
        scope: swarm

    - name: Login to GitHub Container Registry (ghcr.io)
      docker_login:
        registry: ghcr.io
        username: "{{ ghcr_username }}"
        password: "{{ ghcr_token }}"
        state: present
      no_log: true

    - name: Pull latest wheel-analyzer image
      docker_image:
        name: ghcr.io/sirvig/wheel-analyzer
        tag: latest
        source: pull

    # PostgreSQL deployment
    - name: Create PostgreSQL data volume
      docker_volume:
        name: wheel_analyzer_pg_data
        state: present

    - name: Create PostgreSQL backup volume
      docker_volume:
        name: wheel_analyzer_pg_backups
        state: present

    - name: Deploy PostgreSQL service to Docker Swarm
      docker_swarm_service:
        name: wheel_analyzer_db
        image: postgres:14.1
        state: present
        networks:
          - app_main
        env:
          POSTGRES_DB: "{{ wheel_analyzer.database.database }}"
          POSTGRES_USER: "{{ wheel_analyzer.database.user }}"
          POSTGRES_PASSWORD: "{{ wheel_analyzer.database.pass }}"
        mounts:
          - source: wheel_analyzer_pg_data
            target: /var/lib/postgresql/data
            type: volume
          - source: wheel_analyzer_pg_backups
            target: /backups
            type: volume
        placement:
          constraints:
            - node.role == worker
        restart_config:
          condition: any
          delay: 5s
          max_attempts: 3
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U {{ wheel_analyzer.database.user }}"]
          interval: 10s
          timeout: 5s
          retries: 5

    - name: Wait for PostgreSQL service to be ready
      shell: |
        sleep 10
        docker exec $(docker ps -q -f name=wheel_analyzer_db) pg_isready -U {{ wheel_analyzer.database.user }}
      register: result
      until: result.rc == 0
      retries: 10
      delay: 3

    # Redis deployment
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
          - "{{ wheel_analyzer.redis.pass }}"
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

    - name: Wait for Redis to be ready
      shell: >
        sleep 5
        docker exec $(docker ps -q -f name=wheel_analyzer_redis)
        redis-cli -a "{{ wheel_analyzer.redis.pass }}" ping
      register: redis_result
      until: redis_result.stdout == "PONG"
      retries: 10
      delay: 3
      no_log: true

    # Django migrations
    - name: Run Django database migrations
      shell: >
        docker run --rm
        --network app_main
        --env-file /etc/wheel-analyzer/.env.docker
        ghcr.io/sirvig/wheel-analyzer:latest
        uv run manage.py migrate --noinput
      register: migrate_result

    - name: Display migration output
      debug:
        var: migrate_result.stdout_lines

    # Cron job
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

**Key specifications:**
- Use `docker_swarm_service` module (NOT `docker_container`)
- Network: `app_main` with overlay driver and swarm scope
- Service names: `wheel_analyzer_db`, `wheel_analyzer_redis`
- Cron: `*/15 10-16 * * 1-5` (every 15 min, weekdays, 10 AM-4 PM)
- Template path: `../templates/wheel_analyzer/.env.docker.j2`
- Health checks and resource limits as specified
- Wait tasks to ensure services are ready before migrations

**Files to modify:**
- `playbooks/deploy_wheel_analyzer.yml`

**Acceptance:**
- Playbook completely rewritten
- Uses Docker Swarm service deployment
- Includes PostgreSQL, Redis, migrations, and cron
- All paths and names match specifications
- Health checks and resource limits configured
- Idempotent (safe to run multiple times)

### Step 5: Test Playbook Syntax and Validate Configuration

Validate the playbook before committing:

```bash
cd /Users/danvigliotti/Development/Webvig/webvig-ansible
ansible-playbook playbooks/deploy_wheel_analyzer.yml --syntax-check
```

**Note:** This may fail without vault password, but check for syntax errors.

**Files affected:**
- None (validation only)

**Acceptance:**
- Syntax check passes or only fails on vault password
- No YAML syntax errors
- No undefined variable references (if vault available)

### Step 6: Commit Changes to Feature Branch

Commit all changes to the feature branch:

```bash
git add templates/wheel_analyzer/.env.docker.j2
git add playbooks/deploy_wheel_analyzer.yml
git add inventory/webvig.yml
git commit -m "Migrate wheel-analyzer deployment to Docker Swarm

- Create dedicated template directory for wheel-analyzer environment config
- Completely rewrite deployment playbook for Docker Swarm services
- Deploy PostgreSQL 14.1 service with volumes and health checks
- Deploy Redis 6.2-alpine service with AOF+RDB persistence
- Add Django migration execution after database readiness
- Configure cron job for automated options scanning (weekdays 10AM-4PM)
- Use overlay network (app_main) for service communication
- Update inventory with service names for internal networking"
```

**Files affected:**
- Feature branch in webvig-ansible repository

**Acceptance:**
- All changes committed to feature branch
- Commit message describes Docker Swarm migration
- Clean working directory

### Step 7: Document Deployment Process

Update documentation to reference webvig-ansible repository:

**In wheel-analyzer repository:**
- Task files 003, 004, 005 should reference webvig-ansible playbook
- ROADMAP.md should note that deployment is in separate repo

**Documentation notes:**
- Deployment happens in webvig-ansible repository
- Playbook path: `/Users/danvigliotti/Development/Webvig/webvig-ansible/playbooks/deploy_wheel_analyzer.yml`
- Requires vault password file in webvig-ansible repository
- Run from webvig-ansible directory

**Files to update (later step):**
- Task 003, 004, 005 in wheel-analyzer (Part 3)

**Acceptance:**
- Clear documentation of separate repository approach
- Path references are correct
- Prerequisites are listed

## Acceptance Criteria

### Functional Requirements

- [ ] Feature branch created in webvig-ansible repository
- [ ] Template directory created: `templates/wheel_analyzer/`
- [ ] Environment template created with all required variables
- [ ] Inventory updated with all necessary variables
- [ ] Playbook completely rewritten for Docker Swarm
- [ ] Playbook includes PostgreSQL deployment
- [ ] Playbook includes Redis deployment
- [ ] Playbook includes migration execution
- [ ] Playbook includes cron job creation
- [ ] Syntax check passes

### Configuration Requirements

- [ ] Paths use `/etc/wheel-analyzer/` on server
- [ ] Network uses overlay driver with swarm scope
- [ ] Service names are `wheel_analyzer_db` and `wheel_analyzer_redis`
- [ ] Template path is `../templates/wheel_analyzer/.env.docker.j2`
- [ ] Vault-encrypted values are preserved
- [ ] Environment file permissions set to 0600

### Deployment Requirements

- [ ] Playbook uses `docker_swarm_service` module
- [ ] Health checks configured for PostgreSQL and Redis
- [ ] Resource limits configured for Redis
- [ ] Wait tasks ensure services are ready
- [ ] Migrations run after database readiness
- [ ] Cron schedule: `*/15 10-16 * * 1-5`

### Documentation Requirements

- [ ] Commit message describes changes clearly
- [ ] Task 002 updated in wheel-analyzer repo
- [ ] References to webvig-ansible are correct
- [ ] Working directory clearly documented

## Files Involved

### New Files (in webvig-ansible repo)

- `templates/wheel_analyzer/.env.docker.j2`

### Modified Files (in webvig-ansible repo)

- `playbooks/deploy_wheel_analyzer.yml` - Complete rewrite
- `inventory/webvig.yml` - Update variables as needed

### Modified Files (in wheel-analyzer repo)

- `tasks/002-ansible-consolidation.md` - This file, rewritten

### Source Files (for reference)

- `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/tasks/003-postgres-deployment.md`
- `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/tasks/004-redis-deployment.md`
- `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/tasks/005-automated-scanner-cron.md`

## Notes

### Repository Separation

- Ansible code stays in webvig-ansible repository
- Application code stays in wheel-analyzer repository
- This maintains separation of concerns
- Infrastructure-as-code is reusable across projects

### Docker Swarm vs docker-compose

**Local development (docker-compose):**
- Uses docker-compose.yml in wheel-analyzer repo
- Container names: `app_db`, `app_redis`
- Network: `app_main` (bridge)

**Production (Docker Swarm):**
- Uses Ansible playbook in webvig-ansible repo
- Service names: `wheel_analyzer_db`, `wheel_analyzer_redis`
- Network: `app_main` (overlay, swarm scope)
- High availability through Swarm

### Service Name Resolution

Docker Swarm provides DNS resolution for service names:
- `wheel_analyzer_db` resolves to PostgreSQL service
- `wheel_analyzer_redis` resolves to Redis service
- Works across swarm nodes via overlay network
- No need to know which node runs which service

### Vault Password

- Vault password file must exist in webvig-ansible repo
- Not committed to git (in .gitignore)
- Required to decrypt inventory variables
- Must be present for playbook execution

## Dependencies

- Access to webvig-ansible repository
- Vault password from webvig-ansible project
- SSH access to uss-web1.webviglabs.com
- Docker Swarm initialized on uss-web1
- Task specifications in wheel-analyzer repo (Tasks 003, 004, 005)
