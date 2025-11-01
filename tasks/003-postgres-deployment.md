# Task 003: Deploy PostgreSQL Database and Run Django Migrations

**Implementation Location**: `/Users/danvigliotti/Development/Webvig/webvig-ansible/playbooks/deploy_wheel_analyzer.yml`

This task is implemented in the separate webvig-ansible repository. The deployment playbook includes PostgreSQL deployment as part of the comprehensive Wheel Analyzer deployment to Docker Swarm.

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Add PostgreSQL service deployment to Ansible playbook
- [ ] Step 2: Configure PostgreSQL Docker volume and network
- [ ] Step 3: Create database initialization tasks
- [ ] Step 4: Add Django migration execution task
- [ ] Step 5: Test database deployment and connectivity
- [ ] Step 6: Verify migrations and schema
- [ ] Step 7: Update documentation

## Overview

Deploy PostgreSQL database service on uss-web1 server using Docker Swarm and set up the Django database schema through migrations. This task establishes the persistent data layer required for the Wheel Analyzer application and all subsequent features.

The deployment will:
- Deploy PostgreSQL 14.1 service via Docker Swarm
- Configure persistent storage with Docker volumes
- Use overlay networking for service-to-service communication
- Set up database credentials securely via Ansible vault
- Create the Django database and user
- Run Django migrations to establish schema
- Verify database connectivity and schema integrity
- Enable high availability through Swarm service management

This task is a prerequisite for Task 004 (automated scanner cron job) as the scanner requires database access to store and retrieve options data.

## Current State Analysis

### Existing Infrastructure

**Local Development Setup:**
- PostgreSQL runs via docker-compose on port 65432
- Uses `app_main` Docker network
- Database configuration in `.env` file (not committed)
- Volumes: `app_pg_data` and `app_pg_data_backups`

**Docker Configuration:**
- `docker-compose.yml` defines local PostgreSQL service as `app_db`
- Image: `library/postgres:14.1`
- Container name: `app_db`, hostname: `postgres`
- Environment loaded from `.env` file
- Backup directory: `/backups` mounted in container

**Django Configuration:**
- Custom user model: `tracker.User`
- Database URL parsed via `dj-database-url` and `django-environ`
- Migrations exist for `tracker` and `scanner` apps
- `docker-entrypoint.sh` includes migration automation when `DJANGO_MANAGEPY_MIGRATE=on`

**Deployment Configuration (from Task 002):**
- Ansible playbook at `ansible/playbooks/deploy.yml` (to be created)
- Environment template at `ansible/templates/.env.docker.j2` (to be created)
- Vault-encrypted credentials in `ansible/inventory/production.yml` (to be created)

### Missing Components

- PostgreSQL deployment in Ansible playbook
- Production database initialization tasks
- Migration execution strategy for production
- Database backup strategy for production
- Health check and validation tasks

## Target State

### PostgreSQL Container Configuration

**Service Name:** `wheel_analyzer_db`
**Image:** `postgres:14.1`
**Network:** `app_main` (shared with application containers)
**Port:** 5432 (internal to Docker network, not exposed externally)

**Environment Variables:**
- `POSTGRES_DB`: Database name (e.g., `wheel_analyzer`)
- `POSTGRES_USER`: Database user (from vault)
- `POSTGRES_PASSWORD`: Database password (from vault)
- `POSTGRES_HOST_AUTH_METHOD`: `md5` (password authentication)

**Volumes:**
- `wheel_analyzer_pg_data`: PostgreSQL data directory (`/var/lib/postgresql/data`)
- `wheel_analyzer_pg_backups`: Backup directory (`/backups`)

**Deployment Method:**
- Docker Swarm service deployment
- Persistent storage via named volumes
- Restart policy: Restart on any failure

### Database Schema

Django migrations will create:
- `tracker` app tables: User, Account, Campaign, Transaction
- `scanner` app tables: OptionsWatch
- Django system tables: migrations, sessions, admin, etc.
- Database indexes and constraints per model definitions

### Security Configuration

- Database credentials stored in Ansible vault
- Password authentication required
- Database not exposed to external network (internal Docker network only)
- Application connects via `DATABASE_URL` environment variable

## Implementation Steps

### Step 1: Add PostgreSQL Service Deployment to Ansible Playbook

Add tasks to deploy PostgreSQL container in `ansible/playbooks/deploy.yml`:

**Add tasks:**
```yaml
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
      POSTGRES_DB: "{{ wheel_analyzer.postgres_db }}"
      POSTGRES_USER: "{{ wheel_analyzer.postgres_user }}"
      POSTGRES_PASSWORD: "{{ wheel_analyzer.postgres_password }}"
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
      test: ["CMD-SHELL", "pg_isready -U {{ wheel_analyzer.postgres_user }}"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Notes:**
- Volume names use `wheel_analyzer_` prefix for clarity
- Service name: `wheel_analyzer_db` (distinguishes from dev `app_db`)
- Health check ensures database is ready before proceeding
- Restart policy ensures database survives node failures
- Placement on worker nodes for resource isolation

**Files to modify:**
- `ansible/playbooks/deploy.yml` (to be created in Task 002)

**Acceptance:**
- PostgreSQL service deployment tasks are added to playbook
- Volumes are created before service deployment
- Network connection is configured (overlay network)
- Environment variables are templated from inventory
- Health check is configured
- Restart policy and placement constraints are set

### Step 2: Configure PostgreSQL Docker Volume and Network

Ensure Docker network and volumes are properly configured:

**Network configuration (verify from Task 002):**
```yaml
- name: Create Docker overlay network for wheel-analyzer
  docker_network:
    name: app_main
    state: present
    driver: overlay
    scope: swarm
```

**Volume configuration:**
- Volumes use local driver (default)
- Data persists across container recreations
- Backups directory accessible for manual backups

**Verification tasks:**
```yaml
- name: Verify PostgreSQL volumes exist
  docker_volume_info:
    name: "{{ item }}"
  loop:
    - wheel_analyzer_pg_data
    - wheel_analyzer_pg_backups
  register: volume_info

- name: Verify app_main network exists
  docker_network_info:
    name: app_main
  register: network_info
```

**Files to modify:**
- `ansible/playbooks/deploy.yml`

**Acceptance:**
- Overlay network creation happens before PostgreSQL deployment
- Network is configured with `driver: overlay` and `scope: swarm`
- Volumes are created with correct names
- Verification tasks confirm infrastructure is ready

### Step 3: Create Database Initialization Tasks

Add tasks to initialize the PostgreSQL database:

**Wait for database readiness:**
```yaml
- name: Wait for PostgreSQL service to be ready
  shell: |
    docker exec $(docker ps -q -f name=wheel_analyzer_db) pg_isready -U {{ wheel_analyzer.postgres_user }}
  register: result
  until: result.rc == 0
  retries: 10
  delay: 3
```

**Create database and user (if needed):**
```yaml
- name: Ensure database exists
  shell: |
    docker exec $(docker ps -q -f name=wheel_analyzer_db) psql -U {{ wheel_analyzer.postgres_user }} -lqt
  register: db_check

- name: Create database if it doesn't exist
  shell: |
    docker exec $(docker ps -q -f name=wheel_analyzer_db) createdb -U {{ wheel_analyzer.postgres_user }} {{ wheel_analyzer.postgres_db }}
  when: "wheel_analyzer.postgres_db not in db_check.stdout"
  ignore_errors: yes
```

**Notes:**
- Uses `shell` module to find container ID dynamically (Swarm services may have dynamic container names)
- Database and user are typically created by PostgreSQL on first run via environment variables
- These tasks ensure database exists even if service is recreated
- Error handling for cases where database already exists

**Files to modify:**
- `ansible/playbooks/deploy.yml`

**Acceptance:**
- Database initialization waits for PostgreSQL readiness
- Database and user are created if they don't exist
- Tasks are idempotent (safe to run multiple times)

### Step 4: Add Django Migration Execution Task

Add task to run Django migrations:

**Migration task:**
```yaml
- name: Run Django database migrations
  docker_container:
    name: wheel_analyzer_migrate
    image: ghcr.io/sirvig/wheel-analyzer:latest
    state: started
    detach: no
    cleanup: yes
    networks:
      - name: app_main
    env_file: /etc/wheel-analyzer/.env.docker
    command: uv run manage.py migrate --noinput
  register: migrate_result

- name: Display migration output
  debug:
    var: migrate_result.container.Output
```

**Alternative approach using docker run:**
```yaml
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
    var: migrate_result.stdout
```

**Notes:**
- Container is removed after migrations complete (`--rm` or `cleanup: yes`)
- Uses `.env.docker` file deployed in Task 002
- Connects via `app_main` network to reach database
- `--noinput` flag prevents interactive prompts
- Migration output is captured and displayed for verification

**Files to modify:**
- `ansible/playbooks/deploy.yml`

**Acceptance:**
- Migration task runs after database is ready
- Task uses deployed environment configuration
- Migration output is visible in Ansible logs
- Task succeeds without errors
- Container is cleaned up after completion

### Step 5: Test Database Deployment and Connectivity

Test the database deployment locally using Ansible:

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

# Check PostgreSQL service is running
docker service ls | grep wheel_analyzer_db

# Check service details and status
docker service ps wheel_analyzer_db

# Check service logs
docker service logs wheel_analyzer_db

# Verify volumes exist
docker volume ls | grep wheel_analyzer

# Test database connectivity (find container ID first)
CONTAINER_ID=$(docker ps -q -f name=wheel_analyzer_db)
docker exec $CONTAINER_ID psql -U <username> -d wheel_analyzer -c '\l'

# Check network connectivity (overlay network)
docker network inspect app_main
```

**Files affected:**
- PostgreSQL service on uss-web1.webviglabs.com (Docker Swarm)
- Docker volumes on uss-web1.webviglabs.com

**Acceptance:**
- Playbook deploys without errors
- PostgreSQL service is running
- Service is connected to `app_main` overlay network
- Database is accessible from within Docker network
- Volumes are mounted correctly
- Logs show no errors

### Step 6: Verify Migrations and Schema

Verify that Django migrations completed successfully:

**Check migrations:**
```bash
# SSH to server
ssh uss-web1.webviglabs.com

# List applied migrations
docker run --rm \
  --network app_main \
  --env-file /etc/wheel-analyzer/.env.docker \
  ghcr.io/sirvig/wheel-analyzer:latest \
  uv run manage.py showmigrations

# Check specific app migrations
docker run --rm \
  --network app_main \
  --env-file /etc/wheel-analyzer/.env.docker \
  ghcr.io/sirvig/wheel-analyzer:latest \
  uv run manage.py showmigrations tracker scanner
```

**Verify database schema:**
```bash
# Connect to database (find container ID for the service first)
CONTAINER_ID=$(docker ps -q -f name=wheel_analyzer_db)
docker exec -it $CONTAINER_ID psql -U <username> -d wheel_analyzer

# List tables
\dt

# Check specific tables
\d tracker_user
\d tracker_campaign
\d scanner_optionswatch

# Verify indexes
\di

# Exit
\q
```

**Expected tables:**
- Django system tables: `django_migrations`, `django_session`, `auth_*`, etc.
- Tracker tables: `tracker_user`, `tracker_account`, `tracker_campaign`, `tracker_transaction`
- Scanner tables: `scanner_optionswatch`

**Files affected:**
None - this is verification only

**Acceptance:**
- All migrations are applied (marked with [X] in showmigrations output)
- All expected tables exist in database
- Schema matches model definitions
- No migration errors in logs
- Database is ready for application use

### Step 7: Update Documentation

Update project documentation with database deployment information:

**Update README.md:**
Add "Database Deployment" section:
- Explain PostgreSQL deployment via Ansible
- Document connection details (internal to Docker network)
- Explain volume configuration and persistence
- Document how to run migrations manually
- Document backup strategy (if applicable)

**Update ansible/playbooks/deploy.yml comments:**
- Add comments explaining PostgreSQL deployment tasks
- Document environment variables needed
- Explain migration process

**Update reference/ROADMAP.md:**
- Add Task 003 to task list
- Update Phase 1 dependencies
- Reference this task file

**Files to modify:**
- `README.md` - Add database deployment documentation
- `ansible/playbooks/deploy.yml` - Add explanatory comments
- `reference/ROADMAP.md` - Add task reference

**Acceptance:**
- README.md contains clear database deployment documentation
- Deployment process is explained step-by-step
- Troubleshooting tips are included
- ROADMAP.md references this task
- Comments in playbook explain each step

## Acceptance Criteria

### Functional Requirements

- [ ] PostgreSQL 14.1 service is deployed on uss-web1 via Docker Swarm
- [ ] Database is accessible via `app_main` overlay network
- [ ] Database credentials are configured via Ansible vault
- [ ] Django migrations run successfully
- [ ] All expected tables exist in database schema
- [ ] Database persists across service restarts and node failures

### Infrastructure Requirements

- [ ] Docker volumes are created for data and backups
- [ ] PostgreSQL service is connected to `app_main` overlay network
- [ ] Service has health check configured
- [ ] Restart policy is configured with condition and retry limits
- [ ] Placement constraints are set (worker nodes)
- [ ] Database is not exposed to external network
- [ ] Volumes use persistent storage

### Deployment Requirements

- [ ] Ansible playbook includes PostgreSQL deployment
- [ ] Ansible playbook includes migration execution
- [ ] Playbook deploys without errors
- [ ] Playbook is idempotent (can run multiple times safely)
- [ ] Environment variables are templated from inventory
- [ ] Vault-encrypted credentials are used

### Security Requirements

- [ ] Database credentials stored in Ansible vault
- [ ] `.env.docker` file has 0600 permissions (from Task 002)
- [ ] Database requires password authentication
- [ ] Database not exposed to external network
- [ ] Only application containers can access database

### Schema Requirements

- [ ] All Django migrations are applied
- [ ] `tracker` app tables exist: User, Account, Campaign, Transaction
- [ ] `scanner` app tables exist: OptionsWatch
- [ ] Django system tables exist
- [ ] Database indexes are created
- [ ] Foreign key constraints are in place

### Documentation Requirements

- [ ] README.md explains database deployment
- [ ] Connection configuration is documented
- [ ] Migration process is documented
- [ ] Troubleshooting steps are included
- [ ] Playbook has explanatory comments
- [ ] ROADMAP.md references this task

## Files Involved

### Modified Files

- `ansible/playbooks/deploy.yml` - Add PostgreSQL deployment and migration tasks
- `ansible/inventory/production.yml` - Add PostgreSQL credentials (vault-encrypted)
- `ansible/templates/.env.docker.j2` - Ensure DATABASE_URL is templated
- `README.md` - Add database deployment documentation
- `reference/ROADMAP.md` - Add task reference

### Server Files (uss-web1.webviglabs.com)

- PostgreSQL service: `wheel_analyzer_db` (Docker Swarm)
- Docker volumes: `wheel_analyzer_pg_data`, `wheel_analyzer_pg_backups`
- Docker network: `app_main` (overlay network, shared with other services)
- Environment file: `/etc/wheel-analyzer/.env.docker` (from Task 002)

### Potentially Affected Files

- Django migration files (no changes, just execution)
- `.gitignore` - Ensure local `.env` files are excluded
- `docker-compose.yml` - Local dev setup (no changes needed)

## Notes

### Database Connectivity

**Connection String Format:**
```
DATABASE_URL=postgresql://username:password@wheel_analyzer_db:5432/wheel_analyzer
```

**Key points:**
- Hostname: `wheel_analyzer_db` (service name, resolvable within Docker overlay network)
- Port: `5432` (internal PostgreSQL port)
- Network: `app_main` (overlay network, services must be on this network)

### Migration Strategy

**Initial deployment:**
- Run all migrations to establish schema
- Creates empty database structure
- No data seeding (handled separately if needed)

**Future deployments:**
- Migrations run automatically if `DJANGO_MANAGEPY_MIGRATE=on` in entrypoint
- Ansible playbook can also run migrations explicitly
- Zero-downtime migrations may require additional strategy

### Backup Strategy

**Manual backups:**
```bash
docker exec wheel_analyzer_db pg_dump -U <username> wheel_analyzer > backup.sql
```

**Backup directory:**
- Mounted at `/backups` in container
- Mapped to `wheel_analyzer_pg_backups` volume
- Accessible for manual backup operations

**Future considerations:**
- Automated backup cron job (separate task)
- Backup retention policy
- Backup restore procedures
- Point-in-time recovery setup

### Health Check

PostgreSQL health check ensures:
- Database process is running
- Database is accepting connections
- Database is ready for queries

Health check command: `pg_isready -U <username>`

### Volume Management

**Data persistence:**
- All data stored in `wheel_analyzer_pg_data` volume
- Volume persists even if service is removed or fails
- Volume can be backed up separately
- Data survives across node failures (Swarm will reschedule service)

**Backup volume:**
- Provides dedicated space for backup files
- Can be used for manual or automated backups
- Accessible from host system for offloading backups

### Comparison with Local Development

**Local (docker-compose):**
- Container: `app_db`, hostname: `postgres`
- Port: 65432 (exposed to host)
- Environment: `.env` file

**Production (uss-web1):**
- Service: `wheel_analyzer_db` (Docker Swarm), hostname: same
- Port: 5432 (internal only)
- Network: `app_main` (overlay network)
- Environment: `/etc/wheel-analyzer/.env.docker` (deployed via Ansible)
- High availability: Swarm handles service failures and rescheduling

## Dependencies

- Task 002 completed (Ansible consolidation)
  - `ansible/` directory structure exists
  - `ansible.cfg` configured
  - `vault-password.txt` set up
  - Inventory file created with vault-encrypted credentials
  - `.env.docker.j2` template created
- Docker Swarm initialized on uss-web1.webviglabs.com
  - Swarm mode must be active: `docker swarm init`
  - Server should be manager or worker node
- Docker installed on uss-web1.webviglabs.com
- SSH access to uss-web1.webviglabs.com
- Docker image published to ghcr.io (for running migrations)
- Django migrations exist in codebase (already present)
- `app_main` overlay network creation (added in Task 002)
