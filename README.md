# Wheel Analyzer

## Local Development
The local development environment runs in a docker container with the source mounted directly.
The Django development runserver is loaded in the container and will reload on any change.

### First Build Only
1. `cp .env.example .env`
2. `docker network create app_main`
3. `docker-compose up -d --build`

### Justfile
The template is using [Just](https://github.com/casey/just). 

It's a Makefile alternative written in Rust with a nice syntax.

You can find all the shortcuts in `justfile` or run the following command to list them all:
```shell
just --list
```
Info about installation can be found [here](https://github.com/casey/just#packages).

### Linters
Format the code with `ruff --fix` and `ruff format`
```shell
just lint
```

### Migrations
- Create an automatic migration from changes in `tracker/models.py`
```shell
just exec python manage.py makemigrations
```
- Run migrations
```shell
just exec python manage.py migrate
```
- Downgrade migrations
```shell
just exec python manage.py showmigrations
just exec python manage.py migrate tracker 00XX (migration number)
```
### Tests
All tests are integrational and require DB connection. 

Tests will run in a postgres test database

Run tests
```shell
just test
```

You can have tests running automatically with any change
```shell
just test-watch
```

### Backup and Restore database
We are using `pg_dump` and `pg_restore` to backup and restore the database.
- Backup
```shell
just backup
# output example
Backup process started.
Backup has been created and saved to /backups/backup-year-month-date-HHMMSS.dump.gz
```

- Copy the backup file or a directory with all backups to your local machine
```shell
just mount-docker-backup  # get all backups
just mount-docker-backup backup-year-month-date-HHMMSS.dump.gz  # get a specific backup
```
- Restore
```shell
just restore backup-year-month-date-HHMMSS.dump.gz
# output example
Dropping the database...
Creating a new database...
Applying the backup to the new database...
Backup applied successfully.
```
