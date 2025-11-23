from contextlib import contextmanager
from logging import WARNING

from openapi_pydantic import Operation
from pytest import LogCaptureFixture, mark

from aiohttp_openapi import get_operation, operation


def handler_no_doc(request): ...


def handler_with_doc(request):
    "do something"
    ...


@contextmanager
def no_warnings_or_errors(caplog: LogCaptureFixture):
    with caplog.at_level(WARNING, "aiohttp_openapi"):
        try:
            yield caplog
        finally:
            assert caplog.record_tuples == []


def test_operation(caplog):
    with no_warnings_or_errors(caplog):
        operation = Operation(summary="test")
        # Check that it gets passed through no changes.
        assert get_operation(handler_no_doc, operation=operation) == operation


def test_decorated(caplog):
    with no_warnings_or_errors(caplog):
        org_operation = Operation(summary="test")

        @operation(operation=org_operation)
        def handler_decorated(request): ...

        # Check that it gets passed through no changes.
        assert get_operation(handler_decorated) == org_operation


def test_decorated_and_operation_warning(caplog):
    with caplog.at_level(WARNING, "aiohttp_openapi"):

        @operation(operation=Operation(summary="summary from decorator"))
        def handler_decorated(request): ...

        ret_opperation = get_operation(handler_decorated, operation=Operation(summary="expected summary"))
        assert ret_opperation.summary == "expected summary"
        print(caplog.record_tuples)
        assert caplog.record_tuples == [
            (
                "aiohttp_openapi",
                WARNING,
                "Both operation argument provided and decorated with @operation. Ignoring decoration with @operation.",
            )
        ]


def test_summary_docstring(caplog):
    with no_warnings_or_errors(caplog):
        assert get_operation(handler_with_doc).summary == "do something"


def test_operation_summary_docstring(caplog):
    with no_warnings_or_errors(caplog):
        operation = Operation(tags=["foo"])
        ret_operation = get_operation(handler_with_doc, operation=operation)
        assert ret_operation.summary == "do something"
        assert ret_operation.tags == ["foo"]

        # make sure operation was copied, and not modified
        assert operation is not ret_operation


def test_operation_args(caplog):
    with no_warnings_or_errors(caplog):
        assert get_operation(handler_no_doc, summary="test") == Operation(summary="test")


def test_operation_args_overwrite_warning(caplog):
    with caplog.at_level(WARNING, "aiohttp_openapi"):
        assert get_operation(
            handler_no_doc,
            operation=Operation(summary="test"),
            summary="Expected summary",
        ) == Operation(summary="Expected summary")
        print(caplog.record_tuples)


def test_json(caplog):
    with no_warnings_or_errors(caplog):
        assert get_operation(handler_no_doc, json='{"summary": "do something"}').summary == "do something"


def test_json_invalid_schema(caplog):
    with caplog.at_level(WARNING, "aiohttp_openapi"):
        assert get_operation(handler_with_doc, json='{"tags": "bar"}').summary == "do something"
        print(caplog.record_tuples)
        assert caplog.record_tuples == [
            (
                "aiohttp_openapi",
                WARNING,
                "1 validation error for Operation\ntags\n  Input should be a valid array [type=list_type, "
                "input_value='bar', input_type=str]\n    "
                "For further information visit https://errors.pydantic.dev/2.12/v/list_type",
            )
        ]


def test_json_invalid_json(caplog):
    with caplog.at_level(WARNING, "aiohttp_openapi"):
        assert get_operation(handler_with_doc, json="{").summary == "do something"
        print(caplog.record_tuples)
        assert caplog.record_tuples == [
            (
                "aiohttp_openapi",
                WARNING,
                "1 validation error for Operation\n  Invalid JSON: EOF while parsing an object at line 1 column 1 "
                "[type=json_invalid, input_value='{', input_type=str]\n    "
                "For further information visit https://errors.pydantic.dev/2.12/v/json_invalid",
            )
        ]


def test_operation_and_json_warn(caplog):
    with caplog.at_level(WARNING, "aiohttp_openapi"):
        get_operation(
            handler_no_doc,
            operation=Operation(summary="do something"),
            json='{"summary": "do something"}',
        )
        print(caplog.record_tuples)
        assert caplog.record_tuples == [
            ("aiohttp_openapi", WARNING, "Both operation argument and json argument provided. Ignoring json argument.")
        ]


try:
    import yaml  # NOQA F401

    have_yaml = True
except ImportError:
    have_yaml = False


needs_yaml = mark.skipif(not have_yaml, reason="Needs pyyaml to be installed.")
needs_no_yaml = mark.skipif(have_yaml, reason="Needs pyyaml to not be installed.")


@needs_yaml
def test_yaml(caplog: LogCaptureFixture):
    with no_warnings_or_errors(caplog):
        assert get_operation(handler_no_doc, yaml="summary: do something").summary == "do something"


def test_operation_and_yaml_error(caplog):
    with caplog.at_level(WARNING, "aiohttp_openapi"):
        get_operation(
            handler_no_doc,
            operation=Operation(summary="do something"),
            yaml="summary: do something",
        )
        assert caplog.record_tuples == [
            ("aiohttp_openapi", WARNING, "Both operation argument and yaml argument provided. Ignoring yaml argument.")
        ]


def test_yaml_invalid_yaml(caplog):
    with caplog.at_level(WARNING, "aiohttp_openapi"):
        assert get_operation(handler_with_doc, yaml='"x').summary == "do something"
        print(caplog.record_tuples)
        assert caplog.record_tuples == [
            (
                "aiohttp_openapi",
                WARNING,
                'while scanning a quoted scalar\n  in "<unicode string>", line 1, column 1:\n    "x\n    ^\n'
                'found unexpected end of stream\n  in "<unicode string>", line 1, column 3:\n    "x\n      ^',
            )
        ]


def handler_with_yaml_doc(request):
    """
    some docs
    ---
    summary: do something
    """
    ...


def handler_with_yaml_doc2(request):
    """
    summary: do something
    """
    ...


@needs_yaml
def test_yaml_docstring(caplog):
    with no_warnings_or_errors(caplog):
        assert get_operation(handler_with_yaml_doc, yaml_docstring=True).summary == "do something"


@needs_yaml
def test_yaml_docstring2(caplog):
    with no_warnings_or_errors(caplog):
        assert get_operation(handler_with_yaml_doc2, yaml_docstring=True).summary == "do something"


@mark.no_yaml
@needs_no_yaml
def test_no_yaml_error(caplog):
    with caplog.at_level(WARNING, "aiohttp_openapi"):
        get_operation(handler_with_yaml_doc, yaml_docstring=True)
        assert caplog.record_tuples == [
            ("aiohttp_openapi", 40, "Could not import yaml. Please install aiohttp_openapi[yaml]")
        ]
