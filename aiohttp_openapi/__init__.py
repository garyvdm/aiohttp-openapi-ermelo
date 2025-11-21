from collections.abc import Sequence
from dataclasses import InitVar, dataclass, field
from typing import Any, Protocol

from aiohttp import hdrs
from aiohttp.abc import AbstractView
from aiohttp.typedefs import Handler
from aiohttp.web import Application
from aiohttp.web_urldispatcher import AbstractRoute, Resource, ResourceRoute, _ExpectHandler
from openapi_pydantic import OpenAPI, Operation, PathItem
from yarl import URL

from aiohttp_openapi._web_util import add_fixed_response_resource
from aiohttp_openapi.swagger_ui import SwaggerUI

__all__ = [
    "OpenAPIApp",
    "OpenAPIResource",
    "SwaggerUI",
    "APIDocUI",
]


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
                text=self.schema.model_dump_json(indent=2, exclude_none=True),
                content_type="application/json",
            ),
        ).url_for()
        self.api_doc_ui_urls = [schema_doc_ui.setup(self.app, schema_url) for schema_doc_ui in schema_doc_uis]

    def add_route(
        self,
        method: str,
        path: str,
        handler: Handler | type[AbstractView],
        operation: Operation | None = None,
        *,
        name: str | None = None,
        expect_handler: _ExpectHandler | None = None,
    ) -> AbstractRoute:
        setattr(self._get_or_create_path_item(path), check_valid_method(method), operation)
        return self.app.router.add_route(method, path, handler, name=name, expect_handler=expect_handler)

    def add_resource(self, path: str, *, name: str | None = None) -> "OpenAPIResource":
        return OpenAPIResource(self._get_or_create_path_item(path), self.app.router.add_resource(path, name=name))

    def add_head(self, path: str, handler: Handler, operation: Operation | None = None, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method HEAD."""
        return self.add_route(hdrs.METH_HEAD, path, handler, operation=operation, **kwargs)

    def add_options(
        self, path: str, handler: Handler, operation: Operation | None = None, **kwargs: Any
    ) -> AbstractRoute:
        """Shortcut for add_route with method OPTIONS."""
        return self.add_route(hdrs.METH_OPTIONS, path, handler, operation=operation, **kwargs)

    def add_get(
        self,
        path: str,
        handler: Handler,
        operation: Operation | None = None,
        *,
        name: str | None = None,
        allow_head: bool = True,
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with method GET.

        If allow_head is true, another
        route is added allowing head requests to the same endpoint.
        """
        resource = self.add_resource(path, name=name)
        if allow_head:
            resource.add_route(hdrs.METH_HEAD, handler, operation=operation, **kwargs)
        return resource.add_route(hdrs.METH_GET, handler, operation=operation, **kwargs)

    def add_post(self, path: str, handler: Handler, operation: Operation | None = None, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method POST."""
        return self.add_route(hdrs.METH_POST, path, handler, operation=operation, **kwargs)

    def add_put(self, path: str, handler: Handler, operation: Operation | None = None, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method PUT."""
        return self.add_route(hdrs.METH_PUT, path, handler, operation=operation, **kwargs)

    def add_patch(
        self, path: str, handler: Handler, operation: Operation | None = None, **kwargs: Any
    ) -> AbstractRoute:
        """Shortcut for add_route with method PATCH."""
        return self.add_route(hdrs.METH_PATCH, path, handler, operation=operation, **kwargs)

    def add_delete(
        self, path: str, handler: Handler, operation: Operation | None = None, **kwargs: Any
    ) -> AbstractRoute:
        """Shortcut for add_route with method DELETE."""
        return self.add_route(hdrs.METH_DELETE, path, handler, operation=operation, **kwargs)

    def _get_or_create_path_item(self, path: str) -> PathItem:
        if self.schema.paths is None:
            self.schema.paths = {}
        path_item = self.schema.paths.get(path)
        if path_item is None:
            self.schema.paths[path] = path_item = PathItem()
        return path_item


@dataclass
class OpenAPIResource:
    path_item: PathItem
    resource: Resource

    def add_route(
        self,
        method: str,
        handler: type[AbstractView] | Handler,
        operation: Operation | None = None,
        *,
        expect_handler: _ExpectHandler | None = None,
    ) -> ResourceRoute:
        setattr(self.path_item, check_valid_method(method), operation)
        return self.resource.add_route(method, handler, expect_handler=expect_handler)

    def add_head(self, handler: Handler, operation: Operation | None = None, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method HEAD."""
        return self.add_route(hdrs.METH_HEAD, handler, operation=operation, **kwargs)

    def add_options(self, handler: Handler, operation: Operation | None = None, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method OPTIONS."""
        return self.add_route(hdrs.METH_OPTIONS, handler, operation=operation, **kwargs)

    def add_get(
        self,
        handler: Handler,
        operation: Operation | None = None,
        *,
        allow_head: bool = True,
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with method GET.

        If allow_head is true, another
        route is added allowing head requests to the same endpoint.
        """
        if allow_head:
            self.add_route(hdrs.METH_HEAD, handler, operation=operation, **kwargs)
        return self.add_route(hdrs.METH_GET, handler, operation=operation, **kwargs)

    def add_post(self, handler: Handler, operation: Operation | None = None, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method POST."""
        return self.add_route(hdrs.METH_POST, handler, operation=operation, **kwargs)

    def add_put(self, handler: Handler, operation: Operation | None = None, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method PUT."""
        return self.add_route(hdrs.METH_PUT, handler, operation=operation, **kwargs)

    def add_patch(self, handler: Handler, operation: Operation | None = None, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method PATCH."""
        return self.add_route(hdrs.METH_PATCH, handler, operation=operation, **kwargs)

    def add_delete(self, handler: Handler, operation: Operation | None = None, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method DELETE."""
        return self.add_route(hdrs.METH_DELETE, handler, operation=operation, **kwargs)


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
