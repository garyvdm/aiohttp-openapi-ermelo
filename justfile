default: ruff-fix testall
check: ruff-check testall
test: (_test "3.14" "")
[parallel]
testall:  (_test "3.14" "") (_test "3.13" "-m 'not playwright'") (_test "3.12" "-m 'not playwright'") (_test "3.11" "-m 'not playwright'") (_test "3.10" "-m 'not playwright'")

_test version args:
    uv run --quiet --isolated --python python{{version}} --extra test -- pytest --color yes {{args}} | tac | tac

ruff-fix:
    ruff format .
    ruff check --fix .

ruff-check:
    ruff format --check .
    ruff check .

update-ui:
    aiohttp_openapi/contrib-ui/dw-latest-swagger