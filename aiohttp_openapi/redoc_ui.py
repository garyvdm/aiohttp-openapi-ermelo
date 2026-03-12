import importlib.resources
from functools import partial
from string import Template
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field
from yarl import URL

from aiohttp_openapi._web_util import add_fixed_response_resource, add_importlib_resource

if TYPE_CHECKING:
    from aiohttp_openapi import OpenAPIApp


class RedocUI(BaseModel):
    """Setup `Redoc UI <https://redocly.com/docs/redoc>`

    For details on settings, see: `configuration <https://redocly.com/docs/redoc/config>`"""

    model_config = ConfigDict(use_attribute_docstrings=True)

    ui_path: str = Field(exclude=True, default="redoc-ui/")
    """URL path to host the ui at."""

    def setup(self, openapi_app: "OpenAPIApp") -> URL:
        ui_path = openapi_app.url_base_.join(URL(self.ui_path)).path
        add_static_resource = partial(
            add_importlib_resource,
            openapi_app.app.router,
            ui_path,
            importlib.resources.files("aiohttp_openapi").joinpath("contrib-ui/redoc-ui/"),
            append_version=True,
        )
        js_url = add_static_resource("redoc.standalone.js", content_type="text/javascript").url_for()
        add_static_resource("redoc.standalone.js.map", content_type="application/json")
        # settings_json = self.model_dump_json(exclude_unset=True)
        return add_fixed_response_resource(
            openapi_app.app.router,
            ui_path,
            name=f"{openapi_app.name}-redoc-ui" if openapi_app.name else None,
            get_response_args=lambda: dict(
                text=html_template.substitute(
                    title=openapi_app.schema.info.title,
                    url=openapi_app.schema_url,
                    # settings=settings_json,
                    js_url=js_url,
                ),
                content_type="text/html",
            ),
        ).url_for()


html_template = Template("""<!DOCTYPE html>
<html>
  <head>
    <title>Redoc - ${title}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet"/>
    <style> body { margin: 0; padding: 0; } </style>
  </head>
  <body>
    <redoc spec-url="${url}"></redoc>
    <script src="${js_url}"></script>
  </body>
</html>
""")
