import importlib.resources
from functools import partial
from string import Template
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field
from yarl import URL

from aiohttp_openapi._web_util import add_fixed_response_resource, add_importlib_resource

if TYPE_CHECKING:
    from aiohttp_openapi import OpenAPIApp


class SwaggerUI(BaseModel):
    """Setup `Swagger UI <https://swagger.io/tools/swagger-ui/>`

    For details on settings, see: `configuration <https://github.com/swagger-api/swagger-ui/blob/master/docs/usage/configuration.md>`"""

    model_config = ConfigDict(use_attribute_docstrings=True)

    ui_path: str = Field(exclude=True, default="swagger-ui/")
    """URL path to host the ui at."""

    # Plugin
    layout: Literal["BaseLayout", "StandaloneLayout"] = "StandaloneLayout"
    "The name of a component available via the plugin system to use as the top-level layout for Swagger UI."

    # Display
    deepLinking: bool = True
    """If set to ``True``, enables deep linking for tags and operations. See the
    `Deep Linking documentation <https://github.com/swagger-api/swagger-ui/blob/master/docs/usage/deep-linking.md>`_
    for more information. """
    displayOperationId: bool = False
    "Controls the display of operationId in operations list. Default ``False``."
    defaultModelsExpandDepth: int = 1
    " The default expansion depth for models (set to ``-1`` completely hide the models)."
    defaultModelExpandDepth: int = 1
    "The default expansion depth for the model on the model-example section."
    defaultModelRendering: Literal["example", "model"] = "example"
    "Controls how the model is shown when the API is first rendered."
    displayRequestDuration: bool = False
    """Controls the display of the request duration (in milliseconds) for "Try it out" requests."""
    docExpansion: Literal["list", "full", "none"] = "list"
    """Controls the default expansion setting for the operations and tags.
    It can be ``list`` (expands only the tags), ``full`` (expands the tags and operations) or ``none`` 
    (expands nothing)."""
    filter: bool = False
    """If set, enables filtering. The top bar will show an edit box that you can use to filter the tagged operations 
    that are shown."""
    showExtensions: bool = False
    "Controls the display of vendor extension (x-) fields and values for Operations, Parameters, and Schema."
    showCommonExtensions: bool = False
    """Controls the display of extensions (pattern, maxLength, minLength, maximum, minimum) fields and values for 
    Parameters."""

    # Network
    supportedSubmitMethods: list[Literal["get", "put", "post", "delete", "options", "head", "patch", "trace"]] = [
        "get",
        "put",
        "post",
        "delete",
        "options",
        "head",
        "patch",
        "trace",
    ]
    """List of HTTP methods that have the "Try it out" feature enabled.
    
    An empty array disables "Try it out" for all operations. This does not filter the operations from the display."""
    validatorUrl: str | None = "https://validator.swagger.io/validator"
    """By default, Swagger UI attempts to validate specs against swagger.io's online validator.
    You can use this parameter to set a different validator URL, for example for locally deployed
    validators (Validator Badge). Setting it to ``None`` will disable validation."""

    withCredentials: bool = False
    """If set to ``True``, enables passing credentials,`as defined in the Fetch standard <https://fetch.spec.whatwg.org/#credentials>`_,
    in CORS requests that are sent by the browser. Note that Swagger UI cannot currently set cookies cross-domain (see 
    `swagger-js#1163 <https://github.com/swagger-api/swagger-js/issues/1163>`_) - as a result, you will have to rely 
    on browser-supplied cookies (which this setting enables sending) that Swagger UI cannot control. """

    def setup(self, openapi_app: "OpenAPIApp") -> URL:
        static_resource = partial(
            add_importlib_resource,
            openapi_app.app.router,
            openapi_app.url_base_.joinpath(self.ui_path),
            importlib.resources.files("aiohttp_openapi").joinpath("contrib-ui/swagger-ui/"),
            append_version=True,
        )
        html_text = html_template.substitute(
            url=openapi_app.schema_url,
            settings=self.model_dump_json(exclude_unset=True),
            css=static_resource("swagger-ui.css", content_type="text/css").url_for(),
            favicon_32=static_resource("favicon-32x32.png", content_type="image/png").url_for(),
            favicon_16=static_resource("favicon-16x16.png", content_type="image/png").url_for(),
            bundle_js=static_resource("swagger-ui-bundle.js", content_type="text/javascript").url_for(),
            standalone_preset_js=static_resource(
                "swagger-ui-standalone-preset.js", content_type="text/javascript"
            ).url_for(),
        )
        return add_fixed_response_resource(
            openapi_app.app.router,
            openapi_app.url_base_.joinpath(self.ui_path).path,
            name=f"{openapi_app.name}-swagger-ui" if openapi_app.name else None,
            text=html_text,
            content_type="text/html",
        ).url_for()


html_template = Template("""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <title>Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="${css}" >
    <link rel="icon" type="image/png" href="${favicon_32}" sizes="32x32" />
    <link rel="icon" type="image/png" href="${favicon_16}" sizes="16x16" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }

        *,
        *:before,
        *:after {
            box-sizing: inherit;
        }

        body {
            margin: 0;
            background: #fafafa;
        }
    </style>
  </head>

  <body>
    <div id="swagger-ui"></div>

    <script src="${bundle_js}"> </script>
    <script src="${standalone_preset_js}"> </script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({...{
                url: "${url}",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }, ...${settings}});
            window.ui = ui
        }
    </script>
  </body>
</html>
""")
