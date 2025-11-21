from pprint import pprint

from aiohttp import ClientResponse
from aiohttp.web import Application, Request, Response
from openapi_pydantic import Info, OpenAPI, Operation

from aiohttp_openapi import OpenAPIApp
from aiohttp_openapi.tests.util import setup_test_client


async def hello(request: Request):
    return Response(text="Hello, world")


async def test_schema_handler():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_route("GET", "/", hello, Operation(description="home"))
    async with setup_test_client(openapi_app.app) as client:
        resp: ClientResponse = await client.get("/schema.json")
        assert resp.status == 200
        assert resp.content_type == "application/json"
        OpenAPI.model_validate_json(await resp.text())


def test_add_route():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_route("GET", "/", hello, Operation(description="home"))

    pprint(openapi_app.schema.model_dump(exclude_unset=True))
    assert openapi_app.schema == OpenAPI.model_validate(
        {
            "info": {"title": "test-api", "version": "v0.0.1"},
            "paths": {"/": {"get": {"description": "home"}}},
        }
    )


def test_add_resource_route():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    home_resource = openapi_app.add_resource("/")
    home_resource.add_route("GET", hello, Operation(description="home"))

    pprint(openapi_app.schema.model_dump(exclude_unset=True))
    assert openapi_app.schema == OpenAPI.model_validate(
        {
            "info": {"title": "test-api", "version": "v0.0.1"},
            "paths": {"/": {"get": {"description": "home"}}},
        }
    )


def test_add_route_helpers():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_get("/", hello, Operation(description="home"))
    openapi_app.add_post("/", hello, Operation(description="home"))

    pprint(openapi_app.schema.model_dump(exclude_unset=True))
    assert openapi_app.schema == OpenAPI.model_validate(
        {
            "info": {"title": "test-api", "version": "v0.0.1"},
            "paths": {
                "/": {
                    "get": {"description": "home"},
                    "post": {"description": "home"},
                    "head": {"description": "home"},
                }
            },
        }
    )


def test_resource_add_route_helpers():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    home_resource = openapi_app.add_resource("/")
    home_resource.add_get(hello, Operation(description="home"))
    home_resource.add_post(hello, Operation(description="home"))

    pprint(openapi_app.schema.model_dump(exclude_unset=True))
    assert openapi_app.schema == OpenAPI.model_validate(
        {
            "info": {"title": "test-api", "version": "v0.0.1"},
            "paths": {
                "/": {
                    "get": {"description": "home"},
                    "post": {"description": "home"},
                    "head": {"description": "home"},
                }
            },
        }
    )
