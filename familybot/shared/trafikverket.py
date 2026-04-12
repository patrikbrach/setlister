"""Trafikverket API client for train disruption messages."""

import os
import requests
from typing import Optional

TRAFIKVERKET_API_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

RELEVANT_STATIONS = [
    "Malmö C",
    "Triangeln",
    "Hyllie",
    "Lund C",
    "Kastrup",
    "København H",
]

ROUTE_MALMÖ_CPH = ["Malmö C", "Triangeln", "Hyllie", "Kastrup", "København H"]
ROUTE_MALMÖ_LUND = ["Malmö C", "Triangeln", "Lund C"]


def fetch_train_messages(api_key: str) -> list[dict]:
    """Fetch active TrainMessage objects from Trafikverket API."""
    query = f"""<REQUEST>
  <LOGIN authenticationkey="{api_key}" />
  <QUERY objecttype="TrainMessage" schemaversion="1.6">
    <FILTER>
      <OR>
        {''.join(f'<LIKE name="AffectedLocation.LocationName" value="%{s}%" />' for s in RELEVANT_STATIONS)}
      </OR>
    </FILTER>
    <INCLUDE>Header</INCLUDE>
    <INCLUDE>ReasonCodeText</INCLUDE>
    <INCLUDE>StartDateTime</INCLUDE>
    <INCLUDE>PrognosticatedEndDateTimeTrafficImpact</INCLUDE>
    <INCLUDE>AffectedLocation</INCLUDE>
    <INCLUDE>TrafficImpact</INCLUDE>
  </QUERY>
</REQUEST>"""

    try:
        response = requests.post(
            TRAFIKVERKET_API_URL,
            data=query,
            headers={"Content-Type": "text/xml"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("RESPONSE", {}).get("RESULT", [])
        if results:
            return results[0].get("TrainMessage", [])
        return []
    except Exception as e:
        print(f"Trafikverket API error: {e}")
        return []


def _affects_route(message: dict, route_stations: list[str]) -> bool:
    """Check if a message affects any station on a given route."""
    affected = message.get("AffectedLocation", [])
    if not isinstance(affected, list):
        affected = [affected]
    affected_names = [loc.get("LocationName", "") for loc in affected]
    return any(station in affected_names for station in route_stations)


def get_disruptions(api_key: str) -> dict:
    """
    Returns a dict with keys 'malmö_cph' and 'malmö_lund'.
    Each value is a list of disruption message strings.
    """
    messages = fetch_train_messages(api_key)
    result = {"malmö_cph": [], "malmö_lund": []}

    for msg in messages:
        header = msg.get("Header", "Störning utan rubrik")
        reason = msg.get("ReasonCodeText", "")
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
