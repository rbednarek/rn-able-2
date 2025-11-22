setup-all: setup-system-dependencies setup-db

setup-system-dependencies:
	bash setup/setup_system_dependencies.sh

setup-db:
	bash setup/setup_db.sh

run:
	poetry install && poetry run python rnable_2/manage.py runserver

db-make-migrations:
	poetry install && poetry run python rnable_2/manage.py makemigrations

db-migrate:
	poetry install && poetry run python rnable_2/manage.py migrate

db-flush:
	poetry install && poetry run python rnable_2/manage.py flush --no-input

db-connect:
	psql -h localhost -p 5432 -U rnable_user -d rnable_db


tests_all:
	poetry run python rnable_2/manage.py test --verbosity=2

tests_de_analysis:
	poetry run python rnable_2/manage.py test de_analysis --verbosity=2

tests_core:
	poetry run python rnable_2/manage.py test core --verbosity=2

tests_home:
	poetry run python rnable_2/manage.py test home --verbosity=2

tests_enrichment:
	poetry run python rnable_2/manage.py test enrichment --verbosity=2
