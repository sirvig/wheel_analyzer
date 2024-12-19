_default: list

set dotenv-load := true

alias l := list
alias t := test

list:
    @just -l

@test *options:
    uv run pytest {{options}}

ruff *args:
  docker compose exec app ruff check {{args}} .
  docker compose exec app ruff format .

@lint:
  just ruff

runserver:
  uv run manage.py runserver

@run:
  just runserver

up:
  docker-compose up -d

kill:
  docker-compose kill

stop:
  docker-compose rm -f

ps:
  docker-compose ps

exec *args:
  docker-compose exec app {{args}}

logs *args:
    docker-compose logs {{args}} -f

dbconsole:
  docker-compose exec app_db psql -U app app

backup:
  docker compose exec app_db scripts/backup

# examples:
# "just get-backup dump_name_2021-01-01..backup.gz" to copy particular backup
# "just get-backup" to copy directory (backups) with all dumps
mount-docker-backup *args:
  docker cp postgres:/backups/{{args}} ./{{args}}

restore *args:
    docker compose exec app_db scripts/restore {{args}}

options *args:
    uv run manage.py find_options {{args}}

rolls *args:
    uv run manage.py find_rolls {{args}}

scan *args:
    uv run manage.py cron_scanner {{args}}

sma *args:
    uv run manage.py cron_sma {{args}}

redis-cli *args:
    redis-cli -p 36379 -a "myStrongPassword" {{args}}