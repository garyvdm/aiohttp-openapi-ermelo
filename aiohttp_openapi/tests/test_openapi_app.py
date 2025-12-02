from textwrap import dedent

from aiohttp import ClientResponse
from aiohttp.web import Application, Request, Response
from openapi_pydantic import Info, OpenAPI, Operation, PathItem
from yarl import URL

from aiohttp_openapi import OpenAPIApp, operation
from aiohttp_openapi.tests.util import setup_test_client


async def hello(request: Request):
    "Says Hello"
    return Response(text="Hello, world")


async def test_schema_handler():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")), url_base="/api/")
    openapi_app.add_route("GET", "hello", hello)
    assert openapi_app.schema_url == URL("/api/schema.json")

    async with setup_test_client(openapi_app.app) as client:
        resp: ClientResponse = await client.get(openapi_app.schema_url)
        assert resp.status == 200
        assert resp.content_type == "application/json"
        print(await resp.text())
        expected_text = dedent(
            """
            {
             "openapi": "3.1.1",
             "info": {
              "title": "test-api",
              "version": "v0.0.1"
             },
             "paths": {
              "/api/hello": {
               "get": {
                "summary": "Says Hello"
               }
              }
             }
            }
            """
        ).strip()

        assert await resp.text() == expected_text


async def test_schema_handler_multiple_api():
    app = Application()
    openapi_app1 = OpenAPIApp(app, OpenAPI(info=Info(title="api 1", version="v0.0.1")), name="api1", url_base="/api1/")
    openapi_app1.add_route("GET", "hello", hello)

    openapi_app2 = OpenAPIApp(app, OpenAPI(info=Info(title="api 2", version="v0.0.2")), name="api2", url_base="/api2/")
    openapi_app2.add_route("GET", "hello", hello)

    async with setup_test_client(app) as client:
        for openapi_app in (openapi_app1, openapi_app2):
            resp: ClientResponse = await client.get(openapi_app.schema_url)
            assert resp.status == 200


def test_add_route_rel():
    openapi_app = OpenAPIApp(
        Application(),
        OpenAPI(info=Info(title="test-api", version="v0.0.1")),
        url_base="/api/",
    )
    route = openapi_app.add_route("GET", "hello", hello)
    assert route.url_for().path == "/api/hello"
    assert openapi_app.schema.paths == {"/api/hello": PathItem(get=Operation(summary="Says Hello"))}


def test_add_route_abs():
    openapi_app = OpenAPIApp(
        Application(),
        OpenAPI(info=Info(title="test-api", version="v0.0.1")),
        url_base="/api/",
    )
    route = openapi_app.add_route("GET", "/hello", hello)
    assert route.url_for().path == "/hello"
    assert openapi_app.schema.paths == {"/hello": PathItem(get=Operation(summary="Says Hello"))}


def test_add_resource_route():
    openapi_app = OpenAPIApp(
        Application(),
        OpenAPI(info=Info(title="test-api", version="v0.0.1")),
        url_base="/api/",
    )
    home_resource = openapi_app.add_resource("hello")
    home_resource.add_route("GET", hello)

    assert openapi_app.schema.paths == {"/api/hello": PathItem(get=Operation(summary="Says Hello"))}


def test_add_route_helpers():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_get("/", hello)
    openapi_app.add_post("/", hello)
    openapi_app.add_delete("/", hello)
    openapi_app.add_put("/", hello)
    openapi_app.add_patch("/", hello)
    openapi_app.add_options("/", hello)

    openapi_app.add_get("/no-head", hello, allow_head=False)
    openapi_app.add_head("/only-head", hello)

    assert openapi_app.schema.paths == {
        "/": PathItem(
            get=Operation(summary="Says Hello"),
            head=Operation(summary="Says Hello"),
            put=Operation(summary="Says Hello"),
            post=Operation(summary="Says Hello"),
            patch=Operation(summary="Says Hello"),
            delete=Operation(summary="Says Hello"),
            options=Operation(summary="Says Hello"),
        ),
        "/no-head": PathItem(get=Operation(summary="Says Hello")),
        "/only-head": PathItem(head=Operation(summary="Says Hello")),
    }


def test_resource_add_route_helpers():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))

    home_resource = openapi_app.add_resource("/")
    home_resource.add_get(hello)
    home_resource.add_post(hello)
    home_resource.add_delete(hello)
    home_resource.add_put(hello)
    home_resource.add_patch(hello)
    home_resource.add_options(hello)

    openapi_app.add_resource("/no-head").add_get(hello, allow_head=False)
    openapi_app.add_resource("/only-head").add_head(hello)

    assert openapi_app.schema.paths == {
        "/": PathItem(
            get=Operation(summary="Says Hello"),
            head=Operation(summary="Says Hello"),
            put=Operation(summary="Says Hello"),
            post=Operation(summary="Says Hello"),
            patch=Operation(summary="Says Hello"),
            delete=Operation(summary="Says Hello"),
            options=Operation(summary="Says Hello"),
        ),
        "/no-head": PathItem(get=Operation(summary="Says Hello")),
        "/only-head": PathItem(head=Operation(summary="Says Hello")),
    }


def test_add_route_decorated():
    @operation(operation=Operation(summary="decorated"))
    async def hello(request: Request):
        return Response(text="Hello, world")

    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_route("GET", "/", hello)

    assert openapi_app.schema == OpenAPI(
        info=Info(title="test-api", version="v0.0.1"),
        paths={"/": PathItem(get=Operation(summary="decorated"))},
    )
