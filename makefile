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
