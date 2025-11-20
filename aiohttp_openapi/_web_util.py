from base64 import urlsafe_b64encode
from collections.abc import Callable, Mapping
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from aiohttp.web import HTTPMovedPermanently, Request, Response
from aiohttp.web_urldispatcher import (
    PlainResource,
    Resource,
    UrlDispatcher,
)
from yarl import URL

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable


def hash_body(body: bytes) -> str:
    m = sha256()
    m.update(body)
    return urlsafe_b64encode(m.digest()).decode("ascii")


def add_fixed_response_resource(
    routes: UrlDispatcher,
    path: str,
    *,
    get_response_args: Callable[[], Mapping[str, Any]] | None = None,
    name: str | None = None,
    append_version: bool = False,
    **response_args,
) -> Resource:
    resource = FixedResponseResource(
        path,
        get_response_args=get_response_args,
        name=name,
        append_version=append_version,
        **response_args,
    )
    routes.register_resource(resource)
    return resource


def add_importlib_resource(
    routes: UrlDispatcher,
    url_prefix: URL | str,
    files: "Traversable",
    path: str,
    *,
    name: str | None = None,
    append_version: bool = False,
    **response_args,
) -> Resource:
    body = files.joinpath(path).read_bytes()
    return add_fixed_response_resource(
        routes,
        str(URL(url_prefix) / path),
        name=name,
        append_version=append_version,
        body=body,
        **response_args,
    )


class FixedResponseResource(PlainResource):
    VERSION_KEY = "v"

    def __init__(
        self,
        path: str,
        *,
        get_response_args: Callable[[], Mapping[str, Any]] | None = None,
        name: str | None = None,
        append_version: bool = False,
        **response_args,
    ) -> None:
        super().__init__(path, name=name)
        self._append_version = append_version
        if get_response_args and response_args:
            raise ValueError("Cannot provide both get_response_args and response_args")
        if response_args:
            self._response_args = response_args
        if get_response_args:
            self._get_response_args = get_response_args
            self._response_args = None
        self._hash = None
        self.add_route("GET", self._handle)
        self.add_route("HEAD", self._handle)

    def _get_hash(self):
        if self._response_args is None:
            self._response_args = self._get_response_args()
        if self._hash is None:
            mock_response = Response(**self._response_args)
            assert isinstance(mock_response.body, bytes)
            self._hash = hash_body(mock_response.body)
        return self._hash

    async def _handle(self, request: Request) -> Response:
        request_version = request.query.get(self.VERSION_KEY, "")
        hash = self._get_hash()
        if request_version and request_version != hash:
            raise HTTPMovedPermanently(self.url_for())
        hash_match: str = request.headers.get("If-None-Match", "")
        if hash_match.startswith("W/"):
            hash_match = hash_match[2:]
        if hash_match == hash:
            response = Response(status=304, reason="Not Modified")
        else:
            assert self._response_args is not None
            response = Response(**self._response_args)
        response.headers["ETag"] = hash
        response.headers["Cache-Control"] = "public, max-age=31536000" if request_version else "public"
        return response

    def url_for(self) -> URL:  # type: ignore[override]
        url = super().url_for()
        if self._append_version:
            url = url.with_query({self.VERSION_KEY: self._get_hash()})
        return url
