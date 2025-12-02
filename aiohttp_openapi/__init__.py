from collections.abc import Callable, Sequence
from dataclasses import InitVar, dataclass, field
from functools import partial
from logging import getLogger
from typing import NotRequired, Protocol, TypedDict, Unpack, cast
from warnings import warn

from aiohttp import hdrs
from aiohttp.abc import AbstractView
from aiohttp.typedefs import Handler
from aiohttp.web import Application
from aiohttp.web_urldispatcher import AbstractRoute, Resource, ResourceRoute, _ExpectHandler
from openapi_pydantic import (
    Callback,
    ExternalDocumentation,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Reference,
    RequestBody,
    Responses,
    SecurityRequirement,
    Server,
)
from pydantic import ValidationError
from yarl import URL

from aiohttp_openapi._web_util import add_fixed_response_resource
from aiohttp_openapi.swagger_ui import SwaggerUI

__all__ = [
    "OpenAPIApp",
    "OpenAPIResource",
    "SwaggerUI",
    "APIDocUI",
    "operation",
    "OpenAPIWarning",
]

logger = getLogger("aiohttp_openapi")


@dataclass
class OpenAPIApp:
    "Adds corresponding routes to an Application and path/operations to an OpenAPI. Setup API documentation UIs."

    app: Application
    schema: OpenAPI
    url_base: InitVar[URL | str] = "/"
    schema_path: InitVar[str | URL] = "schema.json"
    name: str | None = None
    doc_uis: InitVar[Sequence["APIDocUI"]] = field(default=())

    url_base_: URL = field(init=False)
    schema_url: URL = field(init=False)
    doc_ui_urls: Sequence[URL] = field(init=False)

    def __post_init__(self, url_base: URL | str, schema_path: str | URL, doc_uis: Sequence["APIDocUI"]):
        self.url_base_ = URL(url_base)
        self.schema.openapi = self.schema.openapi  # So that pydantic includes it in the dump. (bit of a hack 😭)
        self.schema_url = add_fixed_response_resource(
            self.app.router,
            self.url_base_.join(URL(schema_path)).path,
            name=self.name,
            get_response_args=lambda: dict(
                text=self.schema_dump_json(),
                content_type="application/json",
            ),
        ).url_for()
        self.doc_ui_urls = [doc_ui.setup(self) for doc_ui in doc_uis]

    def schema_dump_json(self):
        return self.schema.model_dump_json(exclude_unset=True, indent=1, by_alias=True)

    def schema_dump(self):
        return self.schema.model_dump(mode="json", exclude_unset=True, by_alias=True)

    def add_route(
        self,
        method: str,
        path: str,
        handler: Handler | type[AbstractView],
        *,
        name: str | None = None,
        expect_handler: _ExpectHandler | None = None,
        **operation_args: Unpack["GetOperationArgs"],
    ) -> AbstractRoute:
        path = self.url_base_.join(URL(path)).path
        operation = get_operation(handler, **operation_args)
        setattr(self._get_or_create_path_item(path), check_valid_method(method), operation)
        return self.app.router.add_route(method, path, handler, name=name, expect_handler=expect_handler)

    def add_resource(self, path: str, *, name: str | None = None, rel_to_base: bool | None = None) -> "OpenAPIResource":
        path = self.url_base_.join(URL(path)).path
        return OpenAPIResource(self._get_or_create_path_item(path), self.app.router.add_resource(path, name=name))

    def add_get(
        self,
        path: str,
        handler: Handler,
        *,
        allow_head: bool = True,
        **kwargs: Unpack["AddRouteArgs"],
    ) -> AbstractRoute:
        """Shortcut for add_route with method GET.

        If allow_head is true, another
        route is added allowing head requests to the same endpoint.
        """
        resource = self.add_resource(path, name=cast(str | None, kwargs.pop("name", None)))
        if allow_head:
            resource.add_route(hdrs.METH_HEAD, handler, **kwargs)  # type: ignore[misc]
        return resource.add_route(hdrs.METH_GET, handler, **kwargs)  # type: ignore[misc]

    def add_head(self, path: str, handler: Handler, **kwargs: Unpack["AddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method HEAD."""
        return self.add_route(hdrs.METH_HEAD, path, handler, **kwargs)

    def add_options(self, path: str, handler: Handler, **kwargs: Unpack["AddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method OPTIONS."""
        return self.add_route(hdrs.METH_OPTIONS, path, handler, **kwargs)

    def add_post(self, path: str, handler: Handler, **kwargs: Unpack["AddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method POST."""
        return self.add_route(hdrs.METH_POST, path, handler, **kwargs)

    def add_put(self, path: str, handler: Handler, **kwargs: Unpack["AddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method PUT."""
        return self.add_route(hdrs.METH_PUT, path, handler, **kwargs)

    def add_patch(self, path: str, handler: Handler, **kwargs: Unpack["AddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method PATCH."""
        return self.add_route(hdrs.METH_PATCH, path, handler, **kwargs)

    def add_delete(self, path: str, handler: Handler, **kwargs: Unpack["AddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method DELETE."""
        return self.add_route(hdrs.METH_DELETE, path, handler, **kwargs)

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
        *,
        expect_handler: _ExpectHandler | None = None,
        **operation_args: Unpack["GetOperationArgs"],
    ) -> ResourceRoute:
        setattr(self.path_item, check_valid_method(method), get_operation(handler, **operation_args))
        return self.resource.add_route(method, handler, expect_handler=expect_handler)

    def add_get(
        self,
        handler: Handler,
        *,
        allow_head: bool = True,
        **kwargs: Unpack["ResourceAddRouteArgs"],
    ) -> AbstractRoute:
        """Shortcut for add_route with method GET.

        If allow_head is true, another
        route is added allowing head requests to the same endpoint.
        """
        if allow_head:
            self.add_route(hdrs.METH_HEAD, handler, **kwargs)
        return self.add_route(hdrs.METH_GET, handler, **kwargs)

    def add_head(self, handler: Handler, **kwargs: Unpack["ResourceAddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method HEAD."""
        return self.add_route(hdrs.METH_HEAD, handler, **kwargs)

    def add_options(self, handler: Handler, **kwargs: Unpack["ResourceAddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method OPTIONS."""
        return self.add_route(hdrs.METH_OPTIONS, handler, **kwargs)

    def add_post(self, handler: Handler, **kwargs: Unpack["ResourceAddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method POST."""
        return self.add_route(hdrs.METH_POST, handler, **kwargs)

    def add_put(self, handler: Handler, **kwargs: Unpack["ResourceAddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method PUT."""
        return self.add_route(hdrs.METH_PUT, handler, **kwargs)

    def add_patch(self, handler: Handler, **kwargs: Unpack["ResourceAddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method PATCH."""
        return self.add_route(hdrs.METH_PATCH, handler, **kwargs)

    def add_delete(self, handler: Handler, **kwargs: Unpack["ResourceAddRouteArgs"]) -> AbstractRoute:
        """Shortcut for add_route with method DELETE."""
        return self.add_route(hdrs.METH_DELETE, handler, **kwargs)


def operation(**kwargs: Unpack["GetOperationArgs"]):
    """Decorate a handler with it's operation information."""

    def decorate(handler):
        handler.open_api_operation = get_operation(handler, **kwargs)
        return handler

    return decorate


class APIDocUI(Protocol):
    def setup(self, openapi_app: OpenAPIApp) -> URL: ...


class GetOperationArgs(TypedDict):
    operation: NotRequired[Operation]
    "Operation to add to schema for this handler. If omitted, one will be created."
    json: NotRequired[str | bytes | bytearray]
    "Operation in json format. Ignored if operation provided"
    yaml: NotRequired[str | None]
    "Operation in yaml format. Ignored if operation provided"
    yaml_docstring: NotRequired[bool]
    "Should yaml be loaded form the docstring of the handler?"
    summary_docstring: NotRequired[bool]
    "Should docstring of the handler be used as the summary?"

    # All args for Operation

    tags: NotRequired[list[str]]
    """
    A list of tags for API documentation control.
    Tags can be used for logical grouping of operations by resources or any other 
    qualifier.
    """

    summary: NotRequired[str]
    """
    A short summary of what the operation does.
    """

    description: NotRequired[str]
    """
    A verbose explanation of the operation behavior.
    [CommonMark syntax](https://spec.commonmark.org/) MAY be used for rich text 
    representation.
    """

    externalDocs: NotRequired[ExternalDocumentation]
    """
    Additional external documentation for this operation.
    """

    operationId: NotRequired[str]
    """
    Unique string used to identify the operation.
    The id MUST be unique among all operations described in the API.
    The operationId value is **case-sensitive**.
    Tools and libraries MAY use the operationId to uniquely identify an operation,
    therefore, it is RECOMMENDED to follow common programming naming conventions.
    """

    parameters: NotRequired[list[Parameter | Reference]]
    """
    A list of parameters that are applicable for this operation.
    If a parameter is already defined at the [Path Item](#pathItemParameters),
    the new definition will override it but can never remove it.
    The list MUST NOT include duplicated parameters.
    A unique parameter is defined by a combination of a [name](#parameterName) and 
    [location](#parameterIn). The list can use the [Reference Object](#referenceObject) 
    to link to parameters that are defined at the 
    [OpenAPI Object's components/parameters](#componentsParameters).
    """

    requestBody: NotRequired[RequestBody | Reference]
    """
    The request body applicable for this operation.  
    
    The `requestBody` is fully supported in HTTP methods where the HTTP 1.1 
    specification [RFC7231](https://tools.ietf.org/html/rfc7231#section-4.3.1) has 
    explicitly defined semantics for request bodies.
    In other cases where the HTTP spec is vague (such as [GET](https://tools.ietf.org/html/rfc7231#section-4.3.1),
    [HEAD](https://tools.ietf.org/html/rfc7231#section-4.3.2)
    and [DELETE](https://tools.ietf.org/html/rfc7231#section-4.3.5)),
    `requestBody` is permitted but does not have well-defined semantics and SHOULD be 
    avoided if possible.
    """

    responses: NotRequired[Responses]
    """
    The list of possible responses as they are returned from executing this operation.
    """

    callbacks: NotRequired[dict[str, Callback | Reference]]
    """
    A map of possible out-of band callbacks related to the parent operation.
    The key is a unique identifier for the Callback Object.
    Each value in the map is a [Callback Object](#callbackObject) 
    that describes a request that may be initiated by the API provider and the expected 
    responses.
    """

    deprecated: NotRequired[bool]
    """
    Declares this operation to be deprecated.
    Consumers SHOULD refrain from usage of the declared operation.
    Default value is `false`.
    """

    security: NotRequired[list[SecurityRequirement]]
    """
    A declaration of which security mechanisms can be used for this operation.
    The list of values includes alternative security requirement objects that can be 
    used. Only one of the security requirement objects need to be satisfied to 
    authorize a request. To make security optional, an empty security requirement 
    (`{}`) can be included in the array. This definition overrides any declared 
    top-level [`security`](#oasSecurity). To remove a top-level security declaration, 
    an empty array can be used.
    """

    servers: NotRequired[list[Server]]
    """
    An alternative `server` array to service this operation.
    If an alternative `server` object is specified at the Path Item Object or Root 
    level, it will be overridden by this value.
    """


class AddRouteArgs(GetOperationArgs):
    name: NotRequired[str]
    expect_handler: NotRequired[_ExpectHandler]


class ResourceAddRouteArgs(GetOperationArgs):
    expect_handler: NotRequired[_ExpectHandler]


class OpenAPIWarning(Warning): ...


openapi_warn = partial(warn, category=OpenAPIWarning, stacklevel=3)


def get_operation(
    handler: Callable,
    operation: Operation | None = None,
    json: str | bytes | bytearray | None = None,
    yaml: str | None = None,
    yaml_docstring: bool = False,
    summary_docstring: bool = True,
    **operation_args,
) -> Operation:
    LOG_STACK_LEVEL = 3
    source = ""
    try:
        if operation:
            source = "operation argument"
        decorated_operation = getattr(handler, "open_api_operation", None)
        if decorated_operation:
            if operation:
                openapi_warn(
                    f"Both {source} provided and decorated with @operation. Ignoring decoration with @operation."
                )
            else:
                source = "decorated with @operation"
                operation = decorated_operation
        if json:
            if operation:
                openapi_warn(f"Both {source} and json argument provided. Ignoring json argument.")
            else:
                source = "json argument"
                operation = Operation.model_validate_json(json)
        yaml_source = ""
        if yaml:
            yaml_source = "yaml argument"
        if yaml_docstring and handler.__doc__:
            if yaml:
                openapi_warn(
                    "Both yaml argument and yaml docstring provided. Ignoring yaml docstring.",
                    stacklevel=LOG_STACK_LEVEL,
                )
            else:
                yaml_source = "yaml docstring"
                before, _, after = handler.__doc__.partition("---")
                yaml = after if after else before
        if yaml:
            if operation:
                openapi_warn(f"Both {source} and {yaml_source} provided. Ignoring {yaml_source}.")
            else:
                try:
                    from yaml import safe_load
                    from yaml.error import YAMLError
                except ImportError as e:
                    raise ImportError("Could not import yaml. Please install aiohttp-openapi-ermelo[yaml]") from e
                else:
                    try:
                        operation = Operation.model_validate(safe_load(yaml))
                    except YAMLError as e:
                        openapi_warn(str(e))
    except ValidationError as e:
        openapi_warn(str(e))
    if operation is None:
        operation = Operation()
    if summary_docstring and not yaml_docstring and not operation.summary and handler.__doc__:
        operation = operation.model_copy(update=dict(summary=handler.__doc__))

    for key in operation_args:
        if key in operation.model_fields_set:
            openapi_warn(
                f"{key} argument provided, and already provided by {source}. Overwriting with {key} argument.",
                stacklevel=LOG_STACK_LEVEL,
            )
    operation = operation.model_copy(update=operation_args)

    return operation


def check_valid_method(method: str):
    if not isinstance(method, str):
        raise TypeError("method must be a str")
    method_lower = method.lower()
    if method_lower not in allowed_methods_lower:
        raise ValueError(f"method.lower() must be one of {allowed_methods_lower}")
    return method_lower


allowed_methods_lower = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
