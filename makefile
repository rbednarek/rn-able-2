setup-all: setup-system-dependencies

setup-system-dependencies:
	bash setup/setup_system_dependencies.sh

run:
	python rnable_2/manage.py runserver

