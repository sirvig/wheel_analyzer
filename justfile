_default: list

set dotenv-load := true

alias l := list
alias t := test

list:
    @just -l

@test *options:
    docker-compose exec app pytest {{options}}

@test-watch *options:
    docker-compose exec app pytest-watch {{options}}

ruff *args:
  docker compose exec app ruff check {{args}} .
  docker compose exec app ruff format .

@lint:
  just ruff

up:
  docker-compose up -d

up-prod:
  docker-compose -f docker-compose.prod.yml up -d

kill:
  docker-compose kill

kill-prod:
  docker-compose -f docker-compose.prod.yml kill

build:
  docker-compose build

build-prod:
  docker-compose -f docker-compose.prod.yml build

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
