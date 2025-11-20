from aiohttp import ClientResponse
from aiohttp.web import Application, Request, Response
from openapi_pydantic import Info, OpenAPI, Operation

from aiohttp_openapi import OpenAPIApp
from aiohttp_openapi.tests.util import setup_test_client


async def hello(request: Request):
    return Response(text="Hello, world")


async def test_schema_handler():
    app = Application()
    openapi_app = OpenAPIApp(app, OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_route("GET", "/", hello, Operation(tags=["foo"], description="home"))
    async with setup_test_client(app) as client:
        resp: ClientResponse = await client.get("/schema.json")
        assert resp.status == 200
        assert resp.content_type == "application/json"
        OpenAPI.model_validate_json(await resp.text())


async def test_add_route():
    app = Application()
    openapi_app = OpenAPIApp(app, OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_route("GET", "/", hello, Operation(tags=["foo"], description="home"))

    print(openapi_app.schema.model_dump_json(indent=2, exclude_none=True))
    assert openapi_app.schema.paths
    assert (operation := openapi_app.schema.paths["/"].get)
    assert operation.description == "home"
