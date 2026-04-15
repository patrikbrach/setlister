"""Trafikverket API client for train disruption messages via TrainAnnouncement."""

import requests

TRAFIKVERKET_API_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

# Station signatures: M=Malmö C, Tr=Triangeln, Hi=Hyllie, Lu=Lund C
CPH_STATIONS = {"M", "Tr", "Hi"}
LUND_STATIONS = {"M", "Tr", "Lu"}

# Only truly critical infrastructure/operational issues
SERIOUS_DEVIATIONS = {
    "Inställt", "Växelfel", "Signalfel", "Spårfel", "Fordonsfel",
    "Banhinder", "Brist på fordon", "Polisinsats",
}


def fetch_train_messages(api_key: str) -> list[dict]:
    """Fetch TrainAnnouncements with active deviations at relevant stations."""
    query = f"""<REQUEST>
  <LOGIN authenticationkey="{api_key}" />
  <QUERY objecttype="TrainAnnouncement" schemaversion="1.8" limit="100">
    <FILTER>
      <AND>
        <IN name="LocationSignature" value="M,Lu,Hi,Tr" />
        <EXISTS name="Deviation" value="true" />
      </AND>
    </FILTER>
    <INCLUDE>LocationSignature</INCLUDE>
    <INCLUDE>Deviation</INCLUDE>
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
        return results[0].get("TrainAnnouncement", []) if results else []
    except Exception as e:
        print(f"Trafikverket API exception: {e}")
        return []


def get_disruptions(api_key: str) -> dict:
    """
    Returns a dict with keys 'malmö_cph' and 'malmö_lund'.
    Each value is a sorted list of unique serious disruption reasons.
    """
    announcements = fetch_train_messages(api_key)
    cph_reasons: set[str] = set()
    lund_reasons: set[str] = set()

    for ann in announcements:
        loc = ann.get("LocationSignature", "")
        deviations = ann.get("Deviation", [])
        if not isinstance(deviations, list):
            deviations = [deviations]

        serious = {
            dev.get("Description", "").strip()
            for dev in deviations
            if isinstance(dev, dict) and dev.get("Description", "").strip() in SERIOUS_DEVIATIONS
        }

        if loc in CPH_STATIONS:
            cph_reasons |= serious
        if loc in LUND_STATIONS:
            lund_reasons |= serious

    return {
        "malmö_cph": sorted(cph_reasons),
        "malmö_lund": sorted(lund_reasons),
    }


def _format_route(reasons: list) -> str:
    if not reasons:
        return "✅ Inga störningar"
    return "⚠️ " + ", ".join(reasons)


def format_disruptions_telegram(disruptions: dict) -> str:
    """Format disruptions for Telegram message."""
    lines = ["🚂 *TÅGSTÖRNINGAR*"]
    lines.append("Malmö → Köpenhamn: " + _format_route(disruptions.get("malmö_cph", [])))
    lines.append("Malmö → Lund: " + _format_route(disruptions.get("malmö_lund", [])))
    return "\n".join(lines)
