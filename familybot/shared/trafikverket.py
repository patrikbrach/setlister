"""Trafikverket API client for train disruption messages."""

import requests

TRAFIKVERKET_API_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

ROUTE_MALMÖ_CPH = ["Malmö C", "Triangeln", "Hyllie", "Kastrup", "København H", "Kobenhavn H"]
ROUTE_MALMÖ_LUND = ["Malmö C", "Triangeln", "Lund C"]

ALL_RELEVANT = set(ROUTE_MALMÖ_CPH + ROUTE_MALMÖ_LUND)


def fetch_train_messages(api_key: str) -> list[dict]:
    """Fetch all active TrainMessage objects from Trafikverket API."""
    query = f"""<REQUEST>
  <LOGIN authenticationkey="{api_key}" />
  <QUERY objecttype="Situation" schemaversion="1.5">
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
            # Try both known object type names
            r = results[0]
            return r.get("TrainMessage") or r.get("Situation") or r.get("Message") or []
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

    # Debug: print first message keys so we can identify correct field names
    if all_messages:
        print(f"TrainMessage keys: {list(all_messages[0].keys())}")

    for msg in all_messages:
        if not _is_relevant(msg):
            continue
        # Try common field name variants
        header = (
            msg.get("Header")
            or msg.get("ExternalDescription")
            or msg.get("Description")
            or "Störning"
        )
        reason = msg.get("ReasonCodeText") or msg.get("ReasonCode") or ""
        text = header if not reason else f"{header} ({reason})"

        if _affects_route(msg, ROUTE_MALMÖ_CPH):
            result["malmö_cph"].append(text)
        if _affects_route(msg, ROUTE_MALMÖ_LUND):
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
