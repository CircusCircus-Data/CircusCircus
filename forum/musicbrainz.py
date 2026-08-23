"""Small, rate-conscious client for public MusicBrainz release searches."""

import json
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ROOT = "https://musicbrainz.org/ws/2"
USER_AGENT = "SoundLabForum/1.0 (https://github.com/CircusCircus-Data/CircusCircus)"
REQUEST_INTERVAL_SECONDS = 1.05
_request_lock = threading.Lock()
_last_request_at = 0.0


class MusicBrainzUnavailable(Exception):
    """Raised when MusicBrainz cannot provide a usable response."""


def _get_json(path, params):
    global _last_request_at
    url = f"{API_ROOT}/{path}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})

    with _request_lock:
        delay = REQUEST_INTERVAL_SECONDS - (time.monotonic() - _last_request_at)
        if delay > 0:
            time.sleep(delay)
        try:
            with urlopen(request, timeout=8) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise MusicBrainzUnavailable("MusicBrainz search is temporarily unavailable.") from exc
        finally:
            _last_request_at = time.monotonic()
    return payload


def _lucene_phrase(value):
    """Escape a user value before placing it inside a Lucene phrase."""

    return value.replace("\\", "\\\\").replace('"', '\\"')


def _artist_credit(credits):
    return "".join(
        credit.get("name", "") + credit.get("joinphrase", "")
        for credit in (credits or [])
        if isinstance(credit, dict)
    ) or "Unknown artist"


def _exact_artist(query):
    """Resolve an exact artist name so common names search the right catalog."""

    phrase = _lucene_phrase(query)
    payload = _get_json(
        "artist/",
        {"query": f'artist:"{phrase}"', "fmt": "json", "limit": 8},
    )
    query_key = query.casefold()
    exact = [
        artist for artist in payload.get("artists", [])
        if artist.get("name", "").casefold() == query_key
    ]
    if not exact:
        return None
    return max(exact, key=lambda artist: int(artist.get("score", 0)))


def _artist_release_groups(artist, limit, offset):
    """Browse canonical albums/EPs for a resolved MusicBrainz artist."""

    payload = _get_json(
        "release-group/",
        {
            "artist": artist["id"],
            "fmt": "json",
            "limit": 100,
            "offset": 0,
            "type": "album|ep",
            "release-group-status": "website-default",
        },
    )
    results = []
    for group in payload.get("release-groups", []):
        group_id = group.get("id", "")
        if not group_id or not group.get("title"):
            continue
        artist_name = _artist_credit(group.get("artist-credit"))
        if artist_name == "Unknown artist":
            artist_name = artist.get("name", "Unknown artist")
        primary_type = group.get("primary-type", "")
        secondary_types = group.get("secondary-types") or []
        format_name = " / ".join([primary_type, *secondary_types]).strip(" / ")
        results.append({
            "id": group_id,
            "title": group["title"],
            "artist": artist_name,
            "date": group.get("first-release-date", ""),
            "format": format_name,
            "country": "",
            "cover_url": f"https://coverartarchive.org/release-group/{group_id}/front-500",
            "musicbrainz_url": f"https://musicbrainz.org/release-group/{group_id}",
            "score": 100,
            "release_group_id": group_id,
        })
    results.sort(key=lambda result: (result["date"] or "9999", result["title"].casefold()))
    return results[offset:offset + limit]


def search_releases(query, limit=24, offset=0):
    """Return artist-aware, de-duplicated releases for a search query."""

    cleaned = (query or "").strip()
    if len(cleaned) < 2:
        return []
    exact_artist = _exact_artist(cleaned)
    if exact_artist:
        return _artist_release_groups(exact_artist, limit, offset)

    phrase = _lucene_phrase(cleaned)
    # An unqualified MusicBrainz release query searches release titles only.
    # Search both fields explicitly so an artist name such as "Prince" finds
    # that artist's catalog, while album-title searches still work.
    search_query = f'artistname:"{phrase}" OR release:"{phrase}"'
    fetch_limit = 100
    payload = _get_json(
        "release/",
        {"query": search_query, "fmt": "json", "limit": fetch_limit, "offset": 0},
    )
    results = []
    for release in payload.get("releases", []):
        release_id = release.get("id", "")
        artist_name = _artist_credit(release.get("artist-credit"))
        formats = release.get("media") or []
        format_name = next(
            (medium.get("format") for medium in formats if medium.get("format")),
            "",
        )
        release_group_id = (release.get("release-group") or {}).get("id", "")
        if release_id and release_group_id and release.get("title"):
            results.append({
                "id": release_group_id,
                "title": release["title"],
                "artist": artist_name,
                "date": release.get("date", ""),
                "format": format_name,
                "country": release.get("country", ""),
                "cover_url": f"https://coverartarchive.org/release-group/{release_group_id}/front-500",
                "musicbrainz_url": f"https://musicbrainz.org/release-group/{release_group_id}",
                "score": int(release.get("score", 0)),
                "release_group_id": release_group_id,
            })

    query_key = cleaned.casefold()
    results.sort(
        key=lambda result: (
            result["artist"].casefold() == query_key,
            result["artist"].casefold().startswith(query_key),
            result["score"],
        ),
        reverse=True,
    )

    # MusicBrainz contains many country/format editions of the same album.
    # Show one representative release per release group in search results;
    # users still see its format and can refine their query for another issue.
    unique_results = []
    seen_groups = set()
    for result in results:
        group_key = result["release_group_id"] or (
            result["artist"].casefold(),
            result["title"].casefold(),
        )
        if group_key in seen_groups:
            continue
        seen_groups.add(group_key)
        unique_results.append(result)
    return unique_results[offset:offset + limit]
