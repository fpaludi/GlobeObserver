
start_project:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python3 -
	poetry install
	poetry update
