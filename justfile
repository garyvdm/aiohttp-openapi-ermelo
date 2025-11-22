default: ruff-fix testall
check: ruff-check testall
test: (_test "3.14" "")

# Run tests across all versions.
# We only run the playwright tests on the latest python version as they are slow.
# When running the main tests, deselect no_yaml so we can clearly see other skips.
# We only run the no_yaml on the latest python version to save on venv setups.
[parallel]
testall:  (_test "3.14" "-m 'not no_yaml'") (_test "3.13" "-m 'not playwright and not no_yaml'") (_test "3.12" "-m 'not playwright and not no_yaml'") (_test "3.11" "-m 'not playwright and not no_yaml'") test_no_yaml

_test version args:
    uv run --quiet --isolated --python python{{version}} --extra test --extra yaml -- pytest --color yes {{args}} | tac | tac

test_no_yaml:
    uv run --quiet --isolated --python python3.14 --extra test -- pytest --color yes -m no_yaml | tac | tac


ruff-fix:
    ruff format .
    ruff check --fix .

ruff-check:
    ruff format --check .
    ruff check .

update-ui:
    aiohttp_openapi/contrib-ui/dw-latest-swagger