# Wheel-Analyzer Development Roadmap

Wheel Analyzer is a Django-based web application for tracking and analyzing stock options trading, specifically focused on the "wheel strategy" (selling puts, taking assignment, selling calls). The application helps track options campaigns, individual transactions, and scan for new trading opportunities.

## Overview

Wheel Analyzer looks through a curated list of stocks, finds their options for a given time period and analyzes them, looking for options that provide a 30% or greater annualized return with a delta of less than .20 or -.20

## Development Workflow

1. **Task Planning**

- Study the existing codebase and understand the current state
- Update `ROADMAP.md` to include the new task
- Priority tasks should be inserted after the last completed task

2. **Task Creation**

- Study the existing codebase and understand the current state
- Create a new task file in the `/tasks` directory
- Name format: `XXX-description.md` (e.g., `001-db.md`)
- Include high-level specifications, relevant files, acceptance criteria, and implementation steps
- Refer to last completed task in the `/tasks` directory for examples. For example, if the current task is `012`, refer to `011` and `010` for examples.
- Note that these examples are completed tasks, so the content reflects the final state of completed tasks (checked boxes and summary of changes). For the new task, the document should contain empty boxes and no summary of changes. Refer to `000-sample.md` as the sample for initial state.

3. **Task Implementation**

- Follow the specifications in the task file
- Implement features and functionality
- Update step progress within the task file after each step
- Stop after completing each step and wait for further instructions

4. **Roadmap Updates**

- Mark completed tasks with ✅ in the roadmap
- Add reference to the task file (e.g., `See: /tasks/001-db.md`)

## Task Files

Detailed implementation tasks are tracked in the `/tasks` directory:

- **Task 001**: Establish Task Tracking System - See: `/tasks/001-task-tracking.md`
- **Task 002**: Consolidate Ansible Deployment into Wheel-Analyzer - See: `/tasks/002-ansible-consolidation.md`
- **Task 003**: Deploy PostgreSQL Database and Run Django Migrations - See: `/tasks/003-postgres-deployment.md`
- **Task 004**: Deploy Redis Cache Using Docker Swarm - See: `/tasks/004-redis-deployment.md`
- **Task 005**: Implement Automated Scanner Cron Job Deployment - See: `/tasks/005-automated-scanner-cron.md`

## Development Phases

### Phase 1: Option scanner MVP

**Status**: In Progress

**Related Tasks**: Task 002, Task 003, Task 004, Task 005

#### Automated Scanning Deployment

Deploy automated options scanning via cron job on uss-web1 server:

1. **Deploy `.env.docker` file**:
   - Ansible task uses template module to render `templates/.env.docker.j2`
   - Rendered file placed at `/etc/wheel-analyzer/.env.docker` on uss-web1
   - File permissions set to `0600` to protect sensitive environment variables

2. **Create Cron Job**:
   - Ansible task uses cron module to add cron entry on uss-web1
   - Schedule: `*/15 10-16 * * *` (every 15 minutes between 10 AM and 4 PM)
   - Command:
     ```bash
     docker run --rm --network app_main --env-file /etc/wheel-analyzer/.env.docker ghcr.io/sirvig/wheel-analyzer:latest uv run manage.py cron_scanner
     ```
   - `--rm`: Automatically remove container after exit
   - `--network app_main`: Connect to existing Docker network for Redis/PostgreSQL access
   - `--env-file`: Load environment variables from deployed file
   - `ghcr.io/sirvig/wheel-analyzer:latest`: Use pre-pulled Docker image
   - `uv run manage.py cron_scanner`: Execute scanner management command

### Phase 2: Fair value calculation automation

**Status**: Not Started

**Related Tasks**: To be defined