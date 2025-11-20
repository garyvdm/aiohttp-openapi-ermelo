from collections.abc import Sequence
from dataclasses import InitVar, dataclass, field
from typing import Protocol

from aiohttp.abc import AbstractView
from aiohttp.typedefs import Handler
from aiohttp.web import Application
from aiohttp.web_urldispatcher import AbstractRoute, _ExpectHandler
from openapi_pydantic import OpenAPI, Operation, PathItem
from yarl import URL

from aiohttp_openapi._web_util import add_fixed_response_resource
from aiohttp_openapi.swagger_ui import SwaggerUI

__all__ = [
    "OpenAPIApp",
    "SwaggerUI",
    "APIDocUI",
]


_allowed_methods_lower = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


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
        if self.schema.paths is None:
            self.schema.paths = {}
        path_item = self.schema.paths.get(path)
        if path_item is None:
            self.schema.paths[path] = path_item = PathItem()

        if not isinstance(method, str):
            raise TypeError("method must be a str")
        method_lower = method.lower()
        if method_lower not in _allowed_methods_lower:
            raise ValueError(f"method.lower() must be one of {_allowed_methods_lower}")
        setattr(path_item, method_lower, operation)
        return self.app.router.add_route(method, path, handler, name=name, expect_handler=expect_handler)


class APIDocUI(Protocol):
    def setup(self, app: Application, schema_url: URL) -> URL: ...
