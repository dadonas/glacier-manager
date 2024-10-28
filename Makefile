start:
	eval "$(pyenv init -)"
	poetry shell
	fastapi dev app.py