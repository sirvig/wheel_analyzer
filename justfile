_default: list

set dotenv-load := true
set shell := ["bash", "-c"]

registry := "ghcr.io"
namespace := "sirvig"

alias l := list
alias t := test

list:
    @just -l --color always | less --quit-if-one-screen --RAW-CONTROL-CHARS --no-init

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

roll *args:
    uv run manage.py find_rolls {{args}}

scan *args:
    uv run manage.py cron_scanner {{args}}

sma *args:
    uv run manage.py cron_sma {{args}}
    
fair_value *args:
    uv run manage.py calculate_intrinsic_value {{args}}

premium *args:
    uv run manage.py calculate_minimum_premium {{args}}

redis-cli *args:
    redis-cli -p 36379 -a "myStrongPassword" {{args}}

build:
  #!/usr/bin/env bash
  image="wheel-analyzer"
  version="latest"
  image_full_name="{{registry}}/{{namespace}}/${image}"
  tagged_name="${image_full_name}:${version}"
  docker build --platform linux/amd64 -t $tagged_name .
  docker images $tagged_name
  docker history $tagged_name
  [[ "${PUSH:-}" != "true" ]] || just push "${image_full_name}" "${version}"

[private]
push image tag:
  docker push "{{image}}:{{tag}}"


docker-run:
  docker run --rm --network app_main --env-file=./.env.docker --publish 8080:8000 --name wheel-analyzer --detach wheel-analyzer:latest

@docker-start:
  just docker-run

docker-stop:
  docker stop wheel-analyzer

ngrok:
  ngrok http 8000

ccusage *args:
  npx ccusage@latest {{args}}