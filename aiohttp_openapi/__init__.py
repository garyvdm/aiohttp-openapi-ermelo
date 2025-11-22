from collections.abc import Sequence
from dataclasses import InitVar, dataclass, field
from logging import getLogger
from typing import Protocol, TypedDict, Unpack

from aiohttp import hdrs
from aiohttp.abc import AbstractView
from aiohttp.typedefs import Handler
from aiohttp.web import Application
from aiohttp.web_urldispatcher import AbstractRoute, Resource, ResourceRoute, _ExpectHandler
from openapi_pydantic import OpenAPI, Operation, PathItem
from pydantic import ValidationError
from yarl import URL

from aiohttp_openapi._web_util import add_fixed_response_resource
from aiohttp_openapi.swagger_ui import SwaggerUI

__all__ = [
    "OpenAPIApp",
    "OpenAPIResource",
    "SwaggerUI",
    "APIDocUI",
]

logger = getLogger("aiohttp_openapi")


class OperationArgs(TypedDict):
    operation: Operation | None
    "Operation to add to schema for this handler. If omitted, one will be created."
    json: str | bytes | bytearray | None
    "Operation in json format. Ignored if operation provided"
    yaml: str | None
    "Operation in yaml format. Ignored if operation provided"
    yaml_docstring: bool
    "Should yaml be loaded form the docstring of the handler?"
    summary_docstring: bool
    "Should docstring of the handler be used as the summary?"


class AddRouteArgs(OperationArgs):
    name: str | None
    expect_handler: _ExpectHandler | None


@dataclass
class OpenAPIApp:
    "Adds corresponding routes to an Application and path/operations to an OpenAPI. Setup API documentation UIs."

    app: Application
    schema: OpenAPI
    schema_path: str = "/schema.json"
    api_doc_uis: InitVar[Sequence["APIDocUI"]] = field(default=())
    api_doc_ui_urls: Sequence[URL] = field(init=False)

    def __post_init__(self, schema_doc_uis: Sequence["APIDocUI"]):
        schema_url = add_fixed_response_resource(
            self.app.router,
            self.schema_path,
            get_response_args=lambda: dict(
                text=self.schema.model_dump_json(),
                content_type="application/json",
            ),
        ).url_for()
        self.api_doc_ui_urls = [schema_doc_ui.setup(self.app, schema_url) for schema_doc_ui in schema_doc_uis]

    def add_route(
        self,
        method: str,
        path: str,
        handler: Handler | type[AbstractView],
        *,
        name: str | None = None,
        expect_handler: _ExpectHandler | None = None,
        **operation_args: Unpack[OperationArgs],
    ) -> AbstractRoute:
        operation = get_operation(handler, **operation_args)
        setattr(self._get_or_create_path_item(path), check_valid_method(method), operation)
        return self.app.router.add_route(method, path, handler, name=name, expect_handler=expect_handler)

    def add_resource(self, path: str, *, name: str | None = None) -> "OpenAPIResource":
        return OpenAPIResource(self._get_or_create_path_item(path), self.app.router.add_resource(path, name=name))

    def add_get(
        self,
        path: str,
        handler: Handler,
        *,
        name: str | None = None,
        allow_head: bool = True,
        **kwargs: Unpack[AddRouteArgs],
    ) -> AbstractRoute:
        """Shortcut for add_route with method GET.

        If allow_head is true, another
        route is added allowing head requests to the same endpoint.
        """
        resource = self.add_resource(path, name=name)
        if allow_head:
            resource.add_route(hdrs.METH_HEAD, handler, **kwargs)
        return resource.add_route(hdrs.METH_GET, handler, **kwargs)

    def add_head(self, path: str, handler: Handler, **kwargs: Unpack[AddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method HEAD."""
        return self.add_route(hdrs.METH_HEAD, path, handler, **kwargs)

    def add_options(self, path: str, handler: Handler, **kwargs: Unpack[AddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method OPTIONS."""
        return self.add_route(hdrs.METH_OPTIONS, path, handler, **kwargs)

    def add_post(self, path: str, handler: Handler, **kwargs: Unpack[AddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method POST."""
        return self.add_route(hdrs.METH_POST, path, handler, **kwargs)

    def add_put(self, path: str, handler: Handler, **kwargs: Unpack[AddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method PUT."""
        return self.add_route(hdrs.METH_PUT, path, handler, **kwargs)

    def add_patch(self, path: str, handler: Handler, **kwargs: Unpack[AddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method PATCH."""
        return self.add_route(hdrs.METH_PATCH, path, handler, **kwargs)

    def add_delete(self, path: str, handler: Handler, **kwargs: Unpack[AddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method DELETE."""
        return self.add_route(hdrs.METH_DELETE, path, handler, **kwargs)

    def _get_or_create_path_item(self, path: str) -> PathItem:
        if self.schema.paths is None:
            self.schema.paths = {}
        path_item = self.schema.paths.get(path)
        if path_item is None:
            self.schema.paths[path] = path_item = PathItem()
        return path_item


class ResourceAddRouteArgs(OperationArgs):
    expect_handler: _ExpectHandler | None


@dataclass
class OpenAPIResource:
    path_item: PathItem
    resource: Resource

    def add_route(
        self,
        method: str,
        handler: type[AbstractView] | Handler,
        *,
        expect_handler: _ExpectHandler | None = None,
        **operation_args: Unpack[OperationArgs],
    ) -> ResourceRoute:
        setattr(self.path_item, check_valid_method(method), get_operation(handler, **operation_args))
        return self.resource.add_route(method, handler, expect_handler=expect_handler)

    def add_get(
        self,
        handler: Handler,
        *,
        allow_head: bool = True,
        **kwargs: Unpack[ResourceAddRouteArgs],
    ) -> AbstractRoute:
        """Shortcut for add_route with method GET.

        If allow_head is true, another
        route is added allowing head requests to the same endpoint.
        """
        if allow_head:
            self.add_route(hdrs.METH_HEAD, handler, **kwargs)
        return self.add_route(hdrs.METH_GET, handler, **kwargs)

    def add_head(self, handler: Handler, **kwargs: Unpack[ResourceAddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method HEAD."""
        return self.add_route(hdrs.METH_HEAD, handler, **kwargs)

    def add_options(self, handler: Handler, **kwargs: Unpack[ResourceAddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method OPTIONS."""
        return self.add_route(hdrs.METH_OPTIONS, handler, **kwargs)

    def add_post(self, handler: Handler, **kwargs: Unpack[ResourceAddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method POST."""
        return self.add_route(hdrs.METH_POST, handler, **kwargs)

    def add_put(self, handler: Handler, **kwargs: Unpack[ResourceAddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method PUT."""
        return self.add_route(hdrs.METH_PUT, handler, **kwargs)

    def add_patch(self, handler: Handler, **kwargs: Unpack[ResourceAddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method PATCH."""
        return self.add_route(hdrs.METH_PATCH, handler, **kwargs)

    def add_delete(self, handler: Handler, **kwargs: Unpack[ResourceAddRouteArgs]) -> AbstractRoute:
        """Shortcut for add_route with method DELETE."""
        return self.add_route(hdrs.METH_DELETE, handler, **kwargs)


def check_valid_method(method: str):
    if not isinstance(method, str):
        raise TypeError("method must be a str")
    method_lower = method.lower()
    if method_lower not in _allowed_methods_lower:
        raise ValueError(f"method.lower() must be one of {_allowed_methods_lower}")
    return method_lower


_allowed_methods_lower = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


class APIDocUI(Protocol):
    def setup(self, app: Application, schema_url: URL) -> URL: ...


def get_operation(
    handler: Handler,
    operation: Operation | None = None,
    json: str | bytes | bytearray | None = None,
    yaml: str | None = None,
    yaml_docstring: bool = False,
    summary_docstring: bool = True,
) -> Operation:
    LOG_STACK_LEVEL = 3

    try:
        decorated_operation = getattr(handler, "open_api_operation", None)
        if decorated_operation:
            if operation:
                logger.warning(
                    "operation provided, but handler already decorated with operation. Ignoring operation.",
                    stacklevel=3,
                )
            operation = decorated_operation
        if json:
            if operation:
                logger.warning("Both operation and json provided. Ignoring json.", stacklevel=LOG_STACK_LEVEL)
            else:
                operation = Operation.model_validate_json(json)
        if yaml_docstring:
            yaml = handler.__doc__
            _, _, after = yaml.partition("---")
            if after:
                yaml = after
        if yaml:
            if operation:
                logger.warning("Both operation and yaml provided. Ignoring yaml.", stacklevel=LOG_STACK_LEVEL)
            else:
                try:
                    from yaml import safe_load
                    from yaml.error import YAMLError
                except ImportError:
                    logger.exception(
                        "Could not import yaml. Please install aiohttp_openapi[yaml]", stacklevel=LOG_STACK_LEVEL
                    )
                else:
                    try:
                        operation = Operation.model_validate(safe_load(yaml))
                    except YAMLError as e:
                        logger.warning(e, stacklevel=LOG_STACK_LEVEL)
    except ValidationError as e:
        logger.warning(e, stacklevel=LOG_STACK_LEVEL)
    except Exception:
        logger.warning("Error loading operation:", stacklevel=LOG_STACK_LEVEL, exc_info=True)
    if operation is None:
        operation = Operation()
    if summary_docstring and not yaml_docstring and operation.summary is None and handler.__doc__:
        operation = operation.model_copy(update=dict(summary=handler.__doc__))
    return operation


def operation(**kwargs: Unpack[OperationArgs]):
    """Decorate a handler with it's operation information."""

    def decorate(handler):
        handler.open_api_operation = get_operation(handler, **kwargs)
        return handler

    return decorate
