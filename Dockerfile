from    python:3.11
run     python3 -m pip install --upgrade pip
run     python3 -m pip install poetry
workdir /app
add     pyproject.toml .
add     poetry.lock .
run     poetry export --with dev > req.txt
run     python3 -m pip install -r req.txt
