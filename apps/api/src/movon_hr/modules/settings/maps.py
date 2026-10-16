"""Coordinates from Google Maps links or raw "lat, lng" text."""

import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

COORDINATES = r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)"
SHORT_LINK_HOSTS = ("goo.gl", "app.goo.gl")


def with_scheme(value: str) -> str:
    return value if "://" in value else f"https://{value}"


def is_short_link(value: str) -> bool:
    return (urlparse(with_scheme(value)).hostname or "").endswith(SHORT_LINK_HOSTS)


def _valid(latitude: float, longitude: float) -> tuple[float, float] | None:
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return round(latitude, 6), round(longitude, 6)


def _match(match: re.Match[str] | None) -> tuple[float, float] | None:
    return _valid(float(match.group(1)), float(match.group(2))) if match else None


def parse_location(text: str) -> tuple[float, float] | None:
    """Raw coordinates, a pin (!3d..!4d..), an @lat,lng view, or a q/ll/... query value."""
    value = text.strip()
    if not value:
        return None
    raw = re.fullmatch(COORDINATES, value)
    if raw:
        return _match(raw)
    pin = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", value)
    if pin:
        return _match(pin)
    at = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", value)
    if at:
        return _match(at)
    try:
        query = parse_qs(urlparse(with_scheme(value)).query)
    except ValueError:
        query = {}
    for key in ("q", "query", "ll", "center", "destination", "daddr"):
        if key in query:
            found = re.search(COORDINATES, unquote(query[key][0]))
            if found:
                return _match(found)
    return _match(re.search(COORDINATES, value))


async def resolve_short_link(url: str) -> str:
    """Follow a short Google Maps link to the final URL; raises httpx.HTTPError on failure."""
    async with (
        httpx.AsyncClient(timeout=8, follow_redirects=True) as client,
        client.stream("GET", url, headers={"User-Agent": "TeamkuOfficeSettings/1.0"}) as response,
    ):
        response.raise_for_status()
        return str(response.url)
