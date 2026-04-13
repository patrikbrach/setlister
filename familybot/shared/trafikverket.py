"""Trafikverket API client for train disruption messages."""

import requests

TRAFIKVERKET_API_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

ROUTE_MALMÖ_CPH = ["Malmö C", "Triangeln", "Hyllie", "Kastrup", "København H", "Kobenhavn H"]
ROUTE_MALMÖ_LUND = ["Malmö C", "Triangeln", "Lund C"]

ALL_RELEVANT = set(ROUTE_MALMÖ_CPH + ROUTE_MALMÖ_LUND)


def fetch_train_messages(api_key: str) -> list[dict]:
    """Fetch all active TrainMessage objects from Trafikverket API."""
    # Query for trains with deviations on relevant stations
    stations = ["Malmö C", "Lund C", "Hyllie", "Triangeln"]
    station_filter = "".join(
        f'<EQ name="LocationSignature" value="{s}" />' for s in ["M", "Lu", "Hi", "Tr"]
    )
    query = f"""<REQUEST>
  <LOGIN authenticationkey="{api_key}" />
  <QUERY objecttype="TrainAnnouncement" schemaversion="1.8" limit="100">
    <FILTER>
      <AND>
        <IN name="LocationSignature" value="M,Lu,Hi,Tr" />
        <EXISTS name="Deviation" value="true" />
      </AND>
    </FILTER>
    <INCLUDE>AdvertisedTrainIdent</INCLUDE>
    <INCLUDE>LocationSignature</INCLUDE>
    <INCLUDE>Deviation</INCLUDE>
    <INCLUDE>AdvertisedTimeAtLocation</INCLUDE>
  </QUERY>
</REQUEST>"""

    try:
        response = requests.post(
            TRAFIKVERKET_API_URL,
            data=query.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8"},
            timeout=10,
        )
        if not response.ok:
            print(f"Trafikverket API error {response.status_code}: {response.text[:300]}")
            return []
        data = response.json()
        results = data.get("RESPONSE", {}).get("RESULT", [])
        if results:
            r = results[0]
            # Print keys for debugging
            keys = list(r.keys())
            print(f"Trafikverket result keys: {keys}")
            return r.get("TrainAnnouncement") or []
        return []
    except Exception as e:
        print(f"Trafikverket API exception: {e}")
        return []


def _affected_locations(message: dict) -> list[str]:
    """Extract location names from a message."""
    affected = message.get("AffectedLocation", [])
    if not isinstance(affected, list):
        affected = [affected]
    return [loc.get("LocationName", "") for loc in affected if isinstance(loc, dict)]


def _affects_route(message: dict, route: list[str]) -> bool:
    names = _affected_locations(message)
    # Check exact match or partial match (e.g. "Malmö C" in "Malmö Centralstation")
    for name in names:
        for station in route:
            if station.lower() in name.lower() or name.lower() in station.lower():
                return True
    return False


def _is_relevant(message: dict) -> bool:
    """Return True if the message affects any of our monitored routes."""
    names = _affected_locations(message)
    for name in names:
        for station in ALL_RELEVANT:
            if station.lower() in name.lower() or name.lower() in station.lower():
                return True
    return False


def get_disruptions(api_key: str) -> dict:
    """
    Returns a dict with keys 'malmö_cph' and 'malmö_lund'.
    Each value is a list of disruption message strings.
    """
    all_messages = fetch_train_messages(api_key)
    result = {"malmö_cph": [], "malmö_lund": []}

    for msg in all_messages:
        deviations = msg.get("Deviation", [])
        if not isinstance(deviations, list):
            deviations = [deviations]
        deviation_texts = [d.get("Description", "") for d in deviations if isinstance(d, dict)]
        text = "; ".join(t for t in deviation_texts if t) or "Avvikelse"
        loc = msg.get("LocationSignature", "")

        # M=Malmö C, Hi=Hyllie, Tr=Triangeln, Lu=Lund C
        if loc in ("M", "Hi", "Tr"):
            result["malmö_cph"].append(text)
            result["malmö_lund"].append(text)
        elif loc == "Lu":
            result["malmö_lund"].append(text)

    return result


def format_disruptions_telegram(disruptions: dict) -> str:
    """Format disruptions for Telegram message."""
    lines = ["🚂 *TÅGSTÖRNINGAR*"]

    cph = disruptions.get("malmö_cph", [])
    lund = disruptions.get("malmö_lund", [])

    if cph:
        lines.append("Malmö → Köpenhamn: ⚠️ " + "; ".join(cph))
    else:
        lines.append("Malmö → Köpenhamn: ✅ Inga störningar")

    if lund:
        lines.append("Malmö → Lund: ⚠️ " + "; ".join(lund))
    else:
        lines.append("Malmö → Lund: ✅ Inga störningar")

    return "\n".join(lines)
