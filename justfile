# Fix, check and test all
default: ruff-fix mypy test-all

# Check and test all
[parallel]
check: ruff-check mypy test-all

# We only run the playwright tests on the latest python version as they are slow.
# When running the main tests, deselect no_yaml so we can clearly see other skips.
# We only run the no_yaml on the latest python version to save on venv setups.
# Run tests across all configurations.
[parallel]
test-all:  (_test "3.14" "-m 'not no_yaml'") (_test "3.13" "-m 'not playwright and not no_yaml'") (_test "3.12" "-m 'not playwright and not no_yaml'") (_test "3.11" "-m 'not playwright and not no_yaml'") test-no-yaml

test: (_test "3.14" "")

_test version args:
    uv run --isolated --python python{{version}} --extra test --extra yaml -- pytest --color yes {{args}} | tac | tac

test-no-yaml:
    uv run --isolated --python python3.14 --extra test -- pytest --color yes -m no_yaml | tac | tac

mypy: 
    uv run --python python3.14 --extra test mypy -p aiohttp_openapi --check-untyped-defs

ruff-fix:
    ruff format .
    ruff check --fix .

ruff-check:
    ruff format --check .
    ruff check .

update-ui:
    aiohttp_openapi/contrib-ui/dw-latest-swagger