from openapi_pydantic import Operation
from pytest import mark, raises, warns

from aiohttp_openapi import OpenAPIWarning, get_operation, operation


def handler_no_doc(request): ...


def handler_with_doc(request):
    "do something"
    ...


def test_operation(recwarn):
    operation = Operation(summary="test")
    # Check that it gets passed through no changes.
    assert get_operation(handler_no_doc, operation=operation) == operation
    assert len(recwarn) == 0


def test_decorated(recwarn):
    org_operation = Operation(summary="test")

    @operation(operation=org_operation)
    def handler_decorated(request): ...

    # Check that it gets passed through no changes.
    assert get_operation(handler_decorated) == org_operation
    assert len(recwarn) == 0


def test_decorated_and_operation_warning(recwarn):
    @operation(operation=Operation(summary="summary from decorator"))
    def handler_decorated(request): ...

    assert len(recwarn) == 0

    with warns(
        match="Both operation argument provided and decorated with @operation. Ignoring decoration with @operation.",
        expected_warning=OpenAPIWarning,
    ):
        ret_opperation = get_operation(handler_decorated, operation=Operation(summary="expected summary"))
        assert ret_opperation.summary == "expected summary"


def test_summary_docstring(recwarn):
    assert get_operation(handler_with_doc).summary == "do something"
    assert len(recwarn) == 0


def test_operation_summary_docstring(recwarn):
    operation = Operation(tags=["foo"])
    ret_operation = get_operation(handler_with_doc, operation=operation)
    assert ret_operation.summary == "do something"
    assert ret_operation.tags == ["foo"]

    # make sure operation was copied, and not modified
    assert operation is not ret_operation
    assert len(recwarn) == 0


def test_operation_args(recwarn):
    assert get_operation(handler_no_doc, summary="test") == Operation(summary="test")
    assert len(recwarn) == 0


def test_operation_args_overwrite_warning():
    with warns(
        match="summary argument provided, and already provided by operation argument. Overwriting with summary argument.",
        expected_warning=OpenAPIWarning,
    ):
        assert get_operation(
            handler_no_doc,
            operation=Operation(summary="test"),
            summary="Expected summary",
        ) == Operation(summary="Expected summary")


def test_json(recwarn):
    assert get_operation(handler_no_doc, json='{"summary": "do something"}').summary == "do something"
    assert len(recwarn) == 0


def test_json_invalid_schema():
    with warns(match="1 validation error for Operation", expected_warning=OpenAPIWarning):
        assert get_operation(handler_with_doc, json='{"tags": "bar"}').summary == "do something"


def test_json_invalid_json():
    with warns(match="1 validation error for Operation", expected_warning=OpenAPIWarning):
        assert get_operation(handler_with_doc, json="{").summary == "do something"


def test_operation_and_json_warn():
    with warns(
        match="Both operation argument and json argument provided. Ignoring json argument.",
        expected_warning=OpenAPIWarning,
    ):
        get_operation(
            handler_no_doc,
            operation=Operation(summary="do something"),
            json='{"summary": "do something"}',
        )


try:
    import yaml  # NOQA F401

    have_yaml = True
except ImportError:
    have_yaml = False


needs_yaml = mark.skipif(not have_yaml, reason="Needs pyyaml to be installed.")
needs_no_yaml = mark.skipif(have_yaml, reason="Needs pyyaml to not be installed.")


@needs_yaml
def test_yaml(recwarn):
    assert get_operation(handler_no_doc, yaml="summary: do something").summary == "do something"
    assert len(recwarn) == 0


def test_operation_and_yaml_error():
    with warns(
        match="Both operation argument and yaml argument provided. Ignoring yaml argument.",
        expected_warning=OpenAPIWarning,
    ):
        get_operation(
            handler_no_doc,
            operation=Operation(summary="do something"),
            yaml="summary: do something",
        )


def test_yaml_invalid_yaml(recwarn):
    with warns(match="found unexpected end of stream", expected_warning=OpenAPIWarning):
        assert get_operation(handler_with_doc, yaml='"x').summary == "do something"


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
def test_yaml_docstring(recwarn):
    assert get_operation(handler_with_yaml_doc, yaml_docstring=True).summary == "do something"
    assert len(recwarn) == 0


@needs_yaml
def test_yaml_docstring2(recwarn):
    assert get_operation(handler_with_yaml_doc2, yaml_docstring=True).summary == "do something"
    assert len(recwarn) == 0


@mark.no_yaml
@needs_no_yaml
def test_no_yaml_error(recwarn):
    with raises(ImportError, match=r"Could not import yaml. Please install aiohttp-openapi-ermelo\[yaml\]"):
        get_operation(handler_with_yaml_doc, yaml_docstring=True)
