from aiohttp import ClientResponse
from aiohttp.web import Application, Request, Response
from openapi_pydantic import Info, OpenAPI, Operation, PathItem

from aiohttp_openapi import OpenAPIApp, operation
from aiohttp_openapi.tests.util import setup_test_client


async def hello(request: Request):
    "home"
    return Response(text="Hello, world")


async def test_schema_handler():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_route("GET", "/", hello)
    async with setup_test_client(openapi_app.app) as client:
        resp: ClientResponse = await client.get("/schema.json")
        assert resp.status == 200
        assert resp.content_type == "application/json"
        print(repr(await resp.text()))
        assert (
            await resp.text()
            == '{"openapi":"3.1.1","info":{"title":"test-api","summary":null,"description":null,"termsOfService":null,"contact":null,"license":null,"version":"v0.0.1"},"jsonSchemaDialect":null,"servers":[{"url":"/","description":null,"variables":null}],"paths":{"/":{"ref":null,"summary":null,"description":null,"get":{"tags":null,"summary":"home","description":null,"externalDocs":null,"operationId":null,"parameters":null,"requestBody":null,"responses":null,"callbacks":null,"deprecated":false,"security":null,"servers":null},"put":null,"post":null,"delete":null,"options":null,"head":null,"patch":null,"trace":null,"servers":null,"parameters":null}},"webhooks":null,"components":null,"security":null,"tags":null,"externalDocs":null}'
        )


def test_add_route():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_route("GET", "/", hello)

    assert openapi_app.schema == OpenAPI(
        info=Info(title="test-api", version="v0.0.1"),
        paths={"/": PathItem(get=Operation(summary="home"))},
    )


def test_add_resource_route():
    openapi_app = OpenAPIApp(Application(), OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    home_resource = openapi_app.add_resource("/")
    home_resource.add_route("GET", hello)

    assert openapi_app.schema == OpenAPI(
        info=Info(title="test-api", version="v0.0.1"),
        paths={"/": PathItem(get=Operation(summary="home"))},
    )


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

    assert openapi_app.schema == OpenAPI(
        info=Info(title="test-api", version="v0.0.1"),
        paths={
            "/": PathItem(
                get=Operation(summary="home"),
                head=Operation(summary="home"),
                put=Operation(summary="home"),
                post=Operation(summary="home"),
                patch=Operation(summary="home"),
                delete=Operation(summary="home"),
                options=Operation(summary="home"),
            ),
            "/no-head": PathItem(get=Operation(summary="home")),
            "/only-head": PathItem(head=Operation(summary="home")),
        },
    )


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

    assert openapi_app.schema == OpenAPI(
        info=Info(title="test-api", version="v0.0.1"),
        paths={
            "/": PathItem(
                get=Operation(summary="home"),
                head=Operation(summary="home"),
                put=Operation(summary="home"),
                post=Operation(summary="home"),
                patch=Operation(summary="home"),
                delete=Operation(summary="home"),
                options=Operation(summary="home"),
            ),
            "/no-head": PathItem(get=Operation(summary="home")),
            "/only-head": PathItem(head=Operation(summary="home")),
        },
    )


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
