import base64
import time
import requests
from typing import Optional

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"


class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self._token: Optional[str] = None
        self._token_expires: float = 0
        self._cache: dict[tuple, Optional[str]] = {}  # (artist, track) -> isrc

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        resp = requests.post(
            TOKEN_URL,
            headers={"Authorization": f"Basic {credentials}"},
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
        if resp.status_code == 401:
            raise ValueError("Ogiltiga Spotify-credentials (401) – kontrollera Client ID och Secret.")
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + data["expires_in"]
        return self._token

    def validate(self):
        """Validate credentials by fetching a token. Raises ValueError on failure."""
        self._get_token()

    def get_isrc(self, artist: str, track: str) -> Optional[str]:
        """Return ISRC for (artist, track), or None if not found. Results cached."""
        key = (artist.lower(), track.lower())
        if key in self._cache:
            return self._cache[key]

        # Attempt 1: specific structured query
        isrc = self._search(f'artist:"{artist}" track:"{track}"')
        # Attempt 2: free text fallback
        if isrc is None:
            isrc = self._search(f"{artist} {track}")

        self._cache[key] = isrc
        return isrc

    def _search(self, query: str, max_retries: int = 3) -> Optional[str]:
        for attempt in range(max_retries):
            try:
                token = self._get_token()
                resp = requests.get(
                    SEARCH_URL,
                    params={"q": query, "type": "track", "limit": 1},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                if resp.status_code == 429:
                    delay = int(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                    time.sleep(delay)
                    continue
                if resp.status_code == 401:
                    self._token = None  # force refresh
                    continue
                if resp.status_code != 200:
                    return None
                items = resp.json().get("tracks", {}).get("items", [])
                if not items:
                    return None
                return items[0].get("external_ids", {}).get("isrc")
            except requests.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        return None
