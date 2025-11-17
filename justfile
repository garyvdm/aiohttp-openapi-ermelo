default: ruff-fix testall
check: ruff-check testall
test: (_test "3.14")
[parallel]
testall:  (_test "3.14") (_test "3.13") (_test "3.12") (_test "3.11") (_test "3.10")

_test version:
    uv run --quiet --isolated --python python{{version}} --extra test -- pytest --color yes | tac | tac

ruff-fix:
    ruff format .
    ruff check --fix .

ruff-check:
    ruff format --check .
    ruff check .
