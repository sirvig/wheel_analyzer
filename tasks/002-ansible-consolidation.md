# Task 002: Consolidate Ansible Deployment into Wheel-Analyzer

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Create Ansible directory structure
- [ ] Step 2: Set up Ansible configuration and vault
- [ ] Step 3: Create deployment playbook
- [ ] Step 4: Create and adapt inventory configuration
- [ ] Step 5: Create environment template
- [ ] Step 6: Create Docker deployment role
- [ ] Step 7: Test deployment configuration
- [ ] Step 8: Document deployment process

## Overview

Consolidate the Ansible deployment configuration from the separate `webvig-ansible` repository into the `wheel-analyzer` project. This makes the project self-contained and simplifies deployment by keeping infrastructure code alongside application code. The consolidation includes:

- Creating `ansible/` directory structure in wheel-analyzer
- Copying and adapting relevant deployment files from webvig-ansible
- Setting up Ansible configuration and vault
- Fixing path inconsistencies (use `/etc/wheel-analyzer/` per roadmap)
- Cleaning up deployment tasks to focus only on wheel-analyzer

## Current State Analysis

### Existing Ansible Configuration (webvig-ansible repo)

Located at: `/Users/danvigliotti/Development/Webvig/webvig-ansible/`

**Key files:**
- `playbooks/deploy_wheel_analyzer.yml` - Main deployment playbook (partially complete)
- `playbooks/roles/docker/tasks/wheel-analyzer.yml` - Docker tasks (contains mixed configuration)
- `templates/.env.docker.j2` - Environment template (exists and mostly complete)
- `inventory/webvig.yml` - Inventory with wheel-analyzer variables

**Issues identified:**
1. Path inconsistency: Ansible uses `/opt/wheel-analyzer/` but roadmap specifies `/etc/wheel-analyzer/`
2. Mixed configuration: `wheel-analyzer.yml` contains unrelated `investment_targets` configuration
3. Incorrect cron jobs: Point to `investment_targets` instead of `wheel-analyzer`
4. Network mismatch: Uses `back-tier`/`front-tier` instead of `app_main` per roadmap

### Wheel-Analyzer Project Structure

Currently has:
- No `ansible/` directory
- No deployment configuration
- Docker image build capability (Dockerfile, docker-compose.yml for dev)

## Target State

### New Directory Structure

```
wheel-analyzer/
├── ansible/
│   ├── ansible.cfg                    # Ansible configuration
│   ├── vault-password.txt             # Vault password file (gitignored)
│   ├── playbooks/
│   │   └── deploy.yml                 # Main deployment playbook
│   ├── inventory/
│   │   └── production.yml             # Production inventory
│   └── templates/
│       └── .env.docker.j2             # Environment template
├── .gitignore                         # Updated to ignore vault password
└── README.md                          # Updated with deployment docs
```

### Corrected Configuration

- Environment file location: `/etc/wheel-analyzer/.env.docker` (per roadmap)
- File permissions: `0600` for security
- Docker network: `app_main` for swarm integration
- Clean, focused configuration without unrelated services

## Implementation Steps

### Step 1: Create Ansible Directory Structure

Create the directory structure for Ansible deployment:

```bash
cd /Users/danvigliotti/Development/Sirvig/wheel-analyzer
mkdir -p ansible/{playbooks,inventory,templates}
```

**Files to create:**
- `ansible/` directory
- `ansible/playbooks/` directory
- `ansible/inventory/` directory
- `ansible/templates/` directory

**Acceptance:**
- All directories exist
- Structure follows Ansible best practices

### Step 2: Set up Ansible Configuration and Vault

Create Ansible configuration file and set up vault:

**Create `ansible/ansible.cfg`:**
```ini
[defaults]
inventory = inventory/production.yml
vault_password_file = vault-password.txt
host_key_checking = False
retry_files_enabled = False

[privilege_escalation]
become = True
become_method = sudo
become_user = root
become_ask_pass = False
```

**Create `ansible/vault-password.txt`:**
- Copy vault password from webvig-ansible project
- Add to `.gitignore`

**Update `.gitignore`:**
```
ansible/vault-password.txt
```

**Files to create:**
- `ansible/ansible.cfg`
- `ansible/vault-password.txt` (gitignored)

**Files to modify:**
- `.gitignore` - Add vault password file

**Acceptance:**
- Ansible configuration is valid
- Vault password file exists but is gitignored
- Configuration points to correct inventory file

### Step 3: Create Deployment Playbook

Create the main deployment playbook at `ansible/playbooks/deploy.yml`:

**Key tasks:**
1. Log into GitHub Container Registry (ghcr.io)
2. Pull latest wheel-analyzer Docker image
3. Deploy `.env.docker` file to `/etc/wheel-analyzer/.env.docker` with 0600 permissions
4. Create `app_main` Docker network (if not exists)
5. Deploy Redis service to Docker Swarm
6. Set up cron job for automated scanning

**Files to create:**
- `ansible/playbooks/deploy.yml`

**Source reference:**
- Adapt from `/Users/danvigliotti/Development/Webvig/webvig-ansible/playbooks/deploy_wheel_analyzer.yml`
- Fix paths: Use `/etc/wheel-analyzer/` not `/opt/wheel-analyzer/`
- Add proper network creation: `app_main`

**Acceptance:**
- Playbook is valid YAML
- Uses correct paths per roadmap
- Includes all necessary deployment steps
- No references to unrelated services

### Step 4: Create and Adapt Inventory Configuration

Create production inventory at `ansible/inventory/production.yml`:

**Content structure:**
```yaml
all:
  children:
    swarm_managers:
      hosts:
        uss-web1.webviglabs.com:
    swarm_workers:
      hosts:
        uss-web1.webviglabs.com:

  vars:
    wheel_analyzer:
      database_url: !vault |
        <encrypted connection string>
      redis_url: !vault |
        <encrypted redis url>
      django_secret_key: !vault |
        <encrypted secret>
      # ... other variables
```

**Files to create:**
- `ansible/inventory/production.yml`

**Source reference:**
- Copy wheel-analyzer variables from `/Users/danvigliotti/Development/Webvig/webvig-ansible/inventory/webvig.yml`
- Keep vault-encrypted values intact
- Remove unrelated service configurations

**Acceptance:**
- Inventory is valid YAML
- Contains all necessary wheel-analyzer variables
- Vault-encrypted values are preserved
- Targets correct hosts (uss-web1.webviglabs.com)

### Step 5: Create Environment Template

Create environment template at `ansible/templates/.env.docker.j2`:

**Template variables:**
- `{{ wheel_analyzer.database_url }}`
- `{{ wheel_analyzer.redis_url }}`
- `{{ wheel_analyzer.django_secret_key }}`
- `{{ wheel_analyzer.django_allowed_hosts }}`
- `{{ wheel_analyzer.marketdata_api_key }}`
- `{{ wheel_analyzer.alphavantage_api_key }}`
- Other Django settings

**Files to create:**
- `ansible/templates/.env.docker.j2`

**Source reference:**
- Copy from `/Users/danvigliotti/Development/Webvig/webvig-ansible/templates/.env.docker.j2`
- Verify all necessary environment variables are included

**Acceptance:**
- Template uses correct Jinja2 variable references
- All required environment variables are included
- Template renders correctly with inventory variables

### Step 6: Create Docker Deployment Role

Create deployment tasks that handle:
1. Creating `/etc/wheel-analyzer/` directory with proper permissions
2. Rendering `.env.docker.j2` to `/etc/wheel-analyzer/.env.docker`
3. Setting file permissions to `0600`
4. Creating `app_main` Docker network
5. Deploying Redis service
6. Setting up GHCR authentication

These tasks can be inline in the playbook or in a separate role structure.

**Files to create:**
- Deployment tasks (inline in playbook or separate role)

**Source reference:**
- Adapt from `/Users/danvigliotti/Development/Webvig/webvig-ansible/playbooks/roles/docker/tasks/wheel-analyzer.yml`
- Remove investment_targets references
- Fix paths to use `/etc/wheel-analyzer/`
- Ensure proper permissions (0600)

**Acceptance:**
- Tasks create correct directory structure
- Environment file is deployed to correct path with correct permissions
- Docker network `app_main` is created
- Redis service is deployed correctly
- No references to unrelated services

### Step 7: Test Deployment Configuration

Test the deployment configuration:

1. Validate playbook syntax:
```bash
cd ansible
ansible-playbook playbooks/deploy.yml --syntax-check
```

2. Run in check mode (dry run):
```bash
ansible-playbook playbooks/deploy.yml --check
```

3. Verify inventory:
```bash
ansible-inventory --list
```

**Acceptance:**
- Playbook syntax is valid
- Check mode runs without errors
- Inventory is properly structured
- All vault variables are accessible

### Step 8: Document Deployment Process

Update README.md with deployment documentation:

**Add section:**
- "Deployment" section explaining:
  - Ansible directory structure
  - How to set up vault password
  - How to run deployment playbook
  - Prerequisites (Ansible installed, SSH access)
  - Example commands

**Files to modify:**
- `README.md` - Add deployment documentation

**Acceptance:**
- Deployment process is clearly documented
- Commands are accurate and complete
- Prerequisites are listed
- Vault setup is explained

## Acceptance Criteria

### Functional Requirements

- [ ] Ansible directory structure is created
- [ ] Deployment playbook deploys to `/etc/wheel-analyzer/` (not `/opt/`)
- [ ] Environment file has correct permissions (0600)
- [ ] Docker network `app_main` is created
- [ ] Inventory contains all necessary variables
- [ ] Vault configuration works correctly
- [ ] Playbook syntax is valid

### Configuration Requirements

- [ ] Paths match roadmap specification (`/etc/wheel-analyzer/`)
- [ ] No references to unrelated services (investment_targets)
- [ ] Vault-encrypted values are preserved
- [ ] GHCR authentication is configured
- [ ] Redis deployment is included

### Documentation Requirements

- [ ] README.md contains deployment instructions
- [ ] Vault setup is documented
- [ ] Directory structure is explained
- [ ] Example commands are provided

### Technical Requirements

- [ ] `.gitignore` excludes vault password file
- [ ] Ansible configuration is valid
- [ ] Playbook can run in check mode without errors
- [ ] All Jinja2 templates render correctly

## Files Involved

### New Files

- `ansible/ansible.cfg`
- `ansible/vault-password.txt` (gitignored)
- `ansible/playbooks/deploy.yml`
- `ansible/inventory/production.yml`
- `ansible/templates/.env.docker.j2`

### Modified Files

- `.gitignore` - Add vault password exclusion
- `README.md` - Add deployment documentation

### Source Files (webvig-ansible repo)

- `/Users/danvigliotti/Development/Webvig/webvig-ansible/playbooks/deploy_wheel_analyzer.yml`
- `/Users/danvigliotti/Development/Webvig/webvig-ansible/playbooks/roles/docker/tasks/wheel-analyzer.yml`
- `/Users/danvigliotti/Development/Webvig/webvig-ansible/templates/.env.docker.j2`
- `/Users/danvigliotti/Development/Webvig/webvig-ansible/inventory/webvig.yml`

### Potentially Affected Files

None - this is new infrastructure within the project.

## Notes

- Vault password must be copied securely from webvig-ansible project
- SSH access to uss-web1.webviglabs.com is required for deployment
- The deployment should be tested in check mode first before actual deployment
- Path correction (`/etc/` not `/opt/`) is critical for Phase 1 compliance
- Consider whether to keep webvig-ansible deployment after consolidation

## Dependencies

- Access to webvig-ansible repository for copying configurations
- Vault password from webvig-ansible project
- SSH access to uss-web1.webviglabs.com
- Ansible installed locally (for testing)
- Task 001 completed (task tracking system established)
