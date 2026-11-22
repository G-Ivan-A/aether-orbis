"""Bounded public-page acquisition for a single AM-1 run."""

from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from http.client import HTTPException, HTTPSConnection
from ipaddress import ip_address
import re
import socket
import ssl
from time import monotonic, sleep
from typing import Callable, Iterable, Iterator, Mapping
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring
from protego import Protego

from aether_orbis.clock import Clock, SystemClock, to_rfc3339
from aether_orbis.ingestion import canonicalize_url
from aether_orbis.model import FrontierItem, RawMaterial, SourceAccessFailure

USER_AGENT = "AetherOrbis"
HABR_ARTICLE = re.compile(r"/(?:ru|en)/(?:companies/[a-zA-Z0-9_-]+/)?articles/[0-9]+/?")
REDIRECT = {301, 302, 303, 307, 308}
RSS_TYPES = {"application/rss+xml", "application/xml", "text/xml"}
HTML_TYPES = {"text/html", "application/xhtml+xml"}


class FetchError(Exception):
    """An expected transport or source-policy failure."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes = b""

    @property
    def media_type(self) -> str:
        return self.headers.get("content-type", "").split(";", 1)[0].strip().lower()


class _PublicHTTPSConnection(HTTPSConnection):
    """Bind the HTTPS connection to an address we checked, retaining TLS hostname checks."""

    def connect(self) -> None:
        addresses = socket.getaddrinfo(self.host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(
            not ip_address(address[4][0]).is_global or ip_address(address[4][0]).is_multicast
            for address in addresses
        ):
            raise FetchError("source_address_denied")
        family, socktype, protocol, _, sockaddr = addresses[0]
        raw = socket.socket(family, socktype, protocol)
        try:
            raw.settimeout(self.timeout)
            raw.connect(sockaddr)
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def https_get(url: str, timeout: float, max_bytes: int) -> HttpResponse:
    parts = urlsplit(url)
    path = urlunsplit(("", "", parts.path, parts.query, ""))
    deadline = monotonic() + timeout
    connection = _PublicHTTPSConnection(parts.hostname, timeout=timeout, context=ssl.create_default_context())
    try:
        connection.request("GET", path, headers={
            "User-Agent": USER_AGENT, "Accept-Encoding": "identity", "Connection": "close",
        })
        with connection.getresponse() as response:
            headers = {name.lower(): value for name, value in response.getheaders()}
            if response.status != 200:
                return HttpResponse(response.status, headers)
            if headers.get("content-encoding", "identity").lower() != "identity":
                raise FetchError("source_encoding_unsupported")
            if response.length is not None and response.length > max_bytes:
                raise FetchError("source_body_limit")
            body = bytearray()
            while len(body) <= max_bytes:
                if monotonic() >= deadline:
                    raise FetchError("source_timeout")
                chunk = response.read1(min(64 * 1024, max_bytes + 1 - len(body)))
                if not chunk:
                    if response.length:
                        raise FetchError("source_response_incomplete")
                    return HttpResponse(response.status, headers, bytes(body))
                body.extend(chunk)
            raise FetchError("source_body_limit")
    except TimeoutError:
        raise FetchError("source_timeout") from None
    except (OSError, HTTPException):
        raise FetchError("source_network_error") from None
    finally:
        connection.close()


def _https_url(value: str) -> str:
    if (
        not isinstance(value, str) or len(value) > 2048 or not value.isascii()
        or re.search(r"[\x00-\x20\x7f\\]", value)
    ):
        raise FetchError("source_url_denied")
    try:
        url = urlsplit(value)
        if (
            url.scheme != "https" or not url.hostname or url.port not in (None, 443)
            or not re.fullmatch(r"(?:[a-z0-9-]+\.)+[a-z][a-z0-9-]*", url.hostname)
            or url.username is not None
        ):
            raise FetchError("source_url_denied")
    except ValueError:
        raise FetchError("source_url_denied") from None
    return urlunsplit(("https", url.hostname, url.path or "/", url.query, ""))


def _habr_article(url: str) -> bool:
    parts = urlsplit(url)
    return parts.hostname == "habr.com" and not parts.query and bool(HABR_ARTICLE.fullmatch(parts.path))


@dataclass(frozen=True)
class HttpLimits:
    max_urls: int = 10
    max_bytes: int = 1_000_000
    delay_seconds: float = 2.0
    timeout_seconds: float = 10.0
    run_seconds: float = 120.0
    max_redirects: int = 2

    def __post_init__(self) -> None:
        if not (
            type(self.max_urls) is int and 1 <= self.max_urls <= 50
            and type(self.max_bytes) is int and 1 <= self.max_bytes <= 2_000_000
            and 1 <= self.delay_seconds <= 60
            and 0 < self.timeout_seconds <= 30 and 0 < self.run_seconds <= 300
            and type(self.max_redirects) is int and 0 <= self.max_redirects <= 5
        ):
            raise ValueError("HTTP source limits are outside supported bounds")


@dataclass(frozen=True)
class SourceSelection:
    urls: tuple[str, ...] = ()
    habr_rss: str | None = None

    def __post_init__(self) -> None:
        if not self.urls and self.habr_rss is None:
            raise FetchError("source_selection_empty")
        if self.habr_rss is not None:
            parts = urlsplit(_https_url(self.habr_rss))
            if parts.hostname != "habr.com" or not re.fullmatch(r"/(?:ru|en)/rss/.*", parts.path):
                raise FetchError("rss_source_denied")


Transport = Callable[[str, float, int], HttpResponse]


@dataclass
class HttpRssFetcher:
    """Fetch approved URLs and articles in one approved Habr RSS scope."""

    selections: Mapping[str, SourceSelection]
    approval_reference: str
    limits: HttpLimits = field(default_factory=HttpLimits)
    transport: Transport = https_get
    clock: Clock = field(default_factory=SystemClock)
    timer: Callable[[], float] = monotonic
    pause: Callable[[float], None] = sleep

    def __post_init__(self) -> None:
        feeds = {selection.habr_rss for selection in self.selections.values()} - {None}
        if not self.approval_reference.strip() or len(feeds) > 1:
            raise ValueError("HTTP acquisition requires one recorded approval and at most one RSS feed")

    def fetch(self, item: FrontierItem) -> Iterable[RawMaterial | SourceAccessFailure]:
        for _, result in self.fetch_batch((item,)):
            yield result

    def fetch_batch(
        self, items: Iterable[FrontierItem],
    ) -> Iterable[tuple[FrontierItem, RawMaterial | SourceAccessFailure]]:
        session = _FetchSession(self, self.timer() + self.limits.run_seconds)
        for item in items:
            selection = self.selections.get(item.value)
            if item.strategy != "enumerate" or selection is None:
                yield item, SourceAccessFailure(item.value, "source_scope_denied")
                continue
            for result in session.fetch_selection(selection):
                yield item, result
            if session.exhausted:
                return


@dataclass
class _FetchSession:
    fetcher: HttpRssFetcher
    deadline: float
    robots: dict[str, Protego | None] = field(default_factory=dict)
    last_request: dict[str, float] = field(default_factory=dict)
    blocked_origins: set[str] = field(default_factory=set)
    attempted: set[str] = field(default_factory=set)
    feeds: set[str] = field(default_factory=set)
    requested_articles: set[str] = field(default_factory=set)
    exhausted: bool = False

    def fetch_selection(self, selection: SourceSelection) -> Iterable[RawMaterial | SourceAccessFailure]:
        approved = set()
        for original in selection.urls:
            try:
                approved.add(_https_url(original))
            except FetchError:
                continue
        candidates = ((url, None, False) for url in selection.urls)
        yield from self._fetch_candidates(candidates, approved)
        if selection.habr_rss is not None and not self.exhausted:
            feed = _https_url(selection.habr_rss)
            if feed in self.feeds:
                return
            self.feeds.add(feed)
            try:
                _, response = self._request(feed, lambda url: url == feed)
                entries = self._rss(response)
                yield from self._fetch_candidates(entries, approved)
            except FetchError as error:
                yield SourceAccessFailure(feed, str(error))

    def _rss(self, response: HttpResponse) -> Iterable[tuple[str, str | None, bool]]:
        if response.media_type not in RSS_TYPES:
            raise FetchError("rss_content_type_denied")
        try:
            root = fromstring(response.body, forbid_dtd=True)
        except (ParseError, DefusedXmlException, LookupError, ValueError):
            raise FetchError("rss_invalid") from None
        channel = root.find("channel") if root.tag == "rss" else None
        if channel is None:
            raise FetchError("rss_invalid")
        for entry in channel.iterfind("item"):
            try:
                date = parsedate_to_datetime(entry.findtext("pubDate", ""))
                published_at = to_rfc3339(date) if date.tzinfo is not None else None
            except (ValueError, TypeError, OverflowError):
                published_at = None
            yield entry.findtext("link", "").strip(), published_at, True

    def _fetch_candidates(
        self,
        candidates: Iterable[tuple[str, str | None, bool]],
        approved: set[str],
    ) -> Iterator[RawMaterial | SourceAccessFailure]:
        for original, published_at, from_feed in candidates:
            try:
                try:
                    url = _https_url(original)
                except FetchError:
                    url = None
                identity = canonicalize_url(url) if url is not None else original
                if identity in self.attempted:
                    continue
                self._count_article(identity)
                if url is None:
                    raise FetchError("source_url_denied")
                if from_feed and not _habr_article(url):
                    raise FetchError("rss_article_scope_denied")

                def allows(target: str) -> bool:
                    return target in approved or (from_feed and _habr_article(target))

                final_url, response = self._request(url, allows, deduplicate=True)
                if response is None:
                    continue
                if response.media_type not in HTML_TYPES:
                    raise FetchError("source_content_type_denied")
                yield RawMaterial(
                    url=canonicalize_url(final_url), payload=response.body, media_type=response.media_type,
                    retrieved_at=to_rfc3339(self.fetcher.clock.now()), published_at=published_at,
                    metadata={"access_status": "allowed"},
                )
            except FetchError as error:
                yield SourceAccessFailure(original, str(error))
                if self.exhausted:
                    return

    def _count_article(self, identity: str) -> None:
        if identity not in self.attempted:
            if len(self.attempted) >= self.fetcher.limits.max_urls:
                self.exhausted = True
                raise FetchError("source_url_limit")
            self.attempted.add(identity)

    def _request(
        self, url: str, allowed: Callable[[str], bool], *, deduplicate: bool = False,
    ) -> tuple[str, HttpResponse | None]:
        origin = urlsplit(url).hostname
        for _ in range(self.fetcher.limits.max_redirects + 1):
            if urlsplit(url).hostname != origin or not allowed(url):
                raise FetchError("source_scope_denied")
            if deduplicate:
                identity = canonicalize_url(url)
                if identity in self.requested_articles:
                    return url, None
                self._count_article(identity)
            if origin in self.blocked_origins:
                raise FetchError("source_origin_blocked")
            policy = self._robots(origin)
            if not policy.can_fetch(url, USER_AGENT):
                raise FetchError("source_robots_denied")
            delay = policy.crawl_delay(USER_AGENT) or 0
            rate = policy.request_rate(USER_AGENT)
            if rate is not None and rate.requests > 0:
                delay = max(delay, rate.seconds / rate.requests)
            if deduplicate:
                self.requested_articles.add(identity)
            response = self._get(url, origin, delay)
            if response.status == 200:
                return url, response
            if response.status in REDIRECT and response.headers.get("location"):
                url = _https_url(urljoin(url, response.headers["location"]))
                continue
            raise FetchError("source_http_error")
        raise FetchError("source_redirect_limit")

    def _robots(self, origin: str) -> Protego:
        if origin not in self.robots:
            self.robots[origin] = None
            response = self._get(f"https://{origin}/robots.txt", origin)
            if response.status == 200 and response.media_type == "text/plain":
                try:
                    body = response.body.decode("utf-8-sig")
                except UnicodeError:
                    raise FetchError("source_robots_unavailable") from None
                lines = (line.split("#", 1)[0].strip() for line in body.splitlines())
                if not any(line and ":" not in line for line in lines):
                    self.robots[origin] = Protego.parse(body)
        policy = self.robots[origin]
        if policy is None:
            raise FetchError("source_robots_unavailable")
        return policy

    def _get(self, url: str, origin: str, robots_delay: float = 0) -> HttpResponse:
        limits = self.fetcher.limits
        now = self.fetcher.timer()
        delay = max(limits.delay_seconds, robots_delay)
        wait = max(0, self.last_request.get(origin, now - delay) + delay - now)
        if now + wait >= self.deadline:
            self.exhausted = True
            raise FetchError("source_run_time_limit")
        if wait:
            self.fetcher.pause(wait)
        remaining = self.deadline - self.fetcher.timer()
        if remaining <= 0:
            self.exhausted = True
            raise FetchError("source_run_time_limit")
        try:
            response = self.fetcher.transport(url, min(limits.timeout_seconds, remaining), limits.max_bytes)
        except TimeoutError:
            raise FetchError("source_timeout") from None
        except OSError:
            raise FetchError("source_network_error") from None
        finally:
            self.last_request[origin] = self.fetcher.timer()
        if self.fetcher.timer() >= self.deadline:
            self.exhausted = True
            raise FetchError("source_run_time_limit")
        if response.status in (403, 429):
            self.blocked_origins.add(origin)
            raise FetchError(f"source_http_{response.status}")
        if len(response.body) > limits.max_bytes:
            raise FetchError("source_body_limit")
        return response
