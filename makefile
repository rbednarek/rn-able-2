setup-all: setup-system-dependencies setup-db

setup-system-dependencies:
	bash setup/setup_system_dependencies.sh

setup-db:
	bash setup/setup_db.sh

run:
	python rnable_2/manage.py runserver

db-make-migrations:
	python rnable_2/manage.py makemigrations

db-migrate:
	python rnable_2/manage.py migrate

db-flush:
	python rnable_2/manage.py flush --no-input


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
