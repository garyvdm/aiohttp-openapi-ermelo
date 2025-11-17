from dataclasses import dataclass, field

from aiohttp.abc import AbstractView
from aiohttp.typedefs import Handler
from aiohttp.web import Application, Request, Response
from aiohttp.web_urldispatcher import AbstractRoute, _ExpectHandler
from openapi_pydantic import OpenAPI, Operation, PathItem

__all__ = [
    "OpenAPIApp",
]


_allowed_methods_lower = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


@dataclass
class OpenAPIApp:
    "Adds corresponding routes to an Application and path/operations to an OpenAPI. Setup API documentation UIs."

    app: Application
    schema: OpenAPI
    schema_path: str = "/schema.json"

    def __post_init__(self):
        self.app.router.add_route("GET", self.schema_path, self._schema_handler)

    _schema_json: str | None = field(init=False, repr=False, default=None)

    async def _schema_handler(self, request: Request):
        if self._schema_json is None:
            self._schema_json = self.schema.model_dump_json(indent=2)
        return Response(text=self._schema_json, content_type="application/json")

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
