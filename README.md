# aiohttp-openapi-ermelo

This library helps you to build openapi schemas for your aiohttp app, and serve documentation uis (Swagger) for the schema.

## Installation

Add `"aiohttp-openapi-ermelo"` to your project dependencies. If you wish to use yaml functionality, then please add `"aiohttp-openapi-ermelo[yaml]"`.

## How to use

Once you have created an aiohttp Application, create an OpenAPIApp, and specify the global parameters for your schema using classes from [openapi-pydantic](https://pypi.org/project/openapi-pydantic/):

```python
from aiohttp.web import Application, Request, Response
from aiohttp_openapi import OpenAPIApp, SwaggerUI, operation
from openapi_pydantic import Info, OpenAPI, Operation

app = Application()
api = OpenAPIApp(
    app,
    OpenAPI(info=Info(version="1.0.0", title="Petstore")),
    url_base="/api/",
    doc_uis=(SwaggerUI(),),
)
```

Then routes to handlers can be added while specifying the parameters for the operation.

```python
async def get_pets(request: Request):
    return json_response([{"id": 10, "name": "doggie"}])

api.add_route("GET", "pets", get_pets, summary="List all pets", operationId="listPets", tags=["pets"])
```

`api.add_route`, and it's related helper functions works much like `app.router.add_route`. It also allows you to specify parameters for the operation. This operation gets set for the relevant path on the schema.

Note that the path is relative the the `url_base`, so for the example above, the path for this example will be `"/api/pets"`. If you want to specify an absolute path, start the path with a `/`.

One can specify the operation parameters using the `@operation` decorator:

```python
@operation(summary="List all pets", operationId="listPets", tags=["pets"])
async def get_pets(request: Request):
    return json_response([{"id": 10, "name": "doggie"}])

api.add_route("GET", "pets", get_pets)
```

### Specifying operation parameters

When specifying operation parameters on either `add_route` or `@operation`, there are a few options on how to provide parameters:

- Specify an Operation object:

```python
@operation(operation=Operation(summary="List all pets", operationId="listPets", tags=["pets"]))
async def get_pets(request: Request): ...
```

- Specify Operation arguments directly:

```python
@operation(summary="List all pets", operationId="listPets", tags=["pets"])
async def get_pets(request: Request): ...
```

- If no summary is provided, and the handler has a doc string, then the doc string is used as the summary. Hence the bellow example is the same as above:

```python
@operation(operationId="listPets", tags=["pets"])
async def get_pets(request: Request):
    "List all pets"
    ...
```

- Specify json text:

```python
@operation(json='{"summary":"List all pets","operationId":"listPets","tags":["pets"]}')
async def get_pets(request: Request): ...
```

- Specify yaml text:

```python
@operation(yaml="""
    summary: List all pets
    operationId: listPets
    tags:
    - pets
""")
async def get_pets(request: Request): ...
```

- Specify yaml text as a docstring:

```python
@operation(yaml_docstring=True)
async def get_pets(request: Request):
    """
    summary: List all pets
    operationId: listPets
    tags:
    - pets
    """
    ...
```
