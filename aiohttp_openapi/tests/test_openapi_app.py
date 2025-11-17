from aiohttp import ClientResponse
from aiohttp.web import Application, Request, Response
from openapi_pydantic import Info, OpenAPI, Operation

from aiohttp_openapi import OpenAPIApp


async def hello(request: Request):
    return Response(text="Hello, world")


async def test_schema_handler(aiohttp_client):
    def create_app():
        app = Application()
        openapi_app = OpenAPIApp(app, OpenAPI(info=Info(title="test-api", version="v0.0.1")))
        openapi_app.add_route("GET", "/", hello, Operation(tags=["foo"], description="home"))
        return app

    client = await aiohttp_client(create_app())
    resp: ClientResponse = await client.get("/schema.json")
    assert resp.status == 200
    assert resp.content_type == "application/json"
    OpenAPI.model_validate_json(await resp.text())


async def test_add_route():
    app = Application()
    openapi_app = OpenAPIApp(app, OpenAPI(info=Info(title="test-api", version="v0.0.1")))
    openapi_app.add_route("GET", "/", hello, Operation(tags=["foo"], description="home"))

    assert openapi_app.schema.paths
    assert (operation := openapi_app.schema.paths["/"].get)
    assert operation.description == "home"
