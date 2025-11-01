# Project Overview

This project is a Django-based web application called "Wheel Analyzer". It appears to be designed for tracking and analyzing stock options, possibly related to the "wheel" strategy.

The application is divided into two main Django apps:

*   **`tracker`**: This app seems to be responsible for tracking options trading campaigns and individual transactions. It includes models for `Campaign` and `Transaction`, and views for listing and creating these items.
*   **`scanner`**: This app appears to provide tools for scanning and analyzing options. It includes views for listing options for a given stock ticker.

The project uses the following key technologies:

*   **Backend**: Django, Python
*   **Frontend**: HTML, CSS, JavaScript, with [HTMX](https://htmx.org/) for dynamic updates.
*   **Database**: PostgreSQL
*   **Authentication**: `django-allauth`
*   **Development Environment**: Docker, with `docker-compose` for orchestration.
*   **Task Runner**: `just`

# Building and Running

The project uses Docker for its development environment and `just` as a task runner to simplify common commands.

## Initial Setup

1.  Copy the example environment file: `cp .env.example .env`
2.  Create the Docker network: `docker network create app_main`
3.  Build and start the services: `docker-compose up -d --build`

## Common Commands

The `justfile` provides several shortcuts for common development tasks:

*   **List all commands**: `just --list`
*   **Run the development server**: `just run`
*   **Run tests**: `just test`
*   **Run tests on file changes**: `just test-watch`
*   **Lint the code**: `just lint`
*   **Create database migrations**: `just exec python manage.py makemigrations`
*   **Run database migrations**: `just exec python manage.py migrate`
*   **Backup the database**: `just backup`
*   **Restore the database**: `just restore <backup-file>`

# Development Conventions

*   **Code Formatting**: The project uses `ruff` for code formatting and linting. You can run `just lint` to format the code.
*   **Testing**: Tests are located in the `tests` directory within each app. The project uses `pytest-django` for testing. Tests are integrational and require a database connection.
*   **Database Migrations**: Django's built-in migration system is used to manage database schema changes.
*   **Static Files**: Static files (CSS, JavaScript, images) are managed by `whitenoise`.
