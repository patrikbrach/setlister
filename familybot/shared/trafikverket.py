"""Trafikverket API client for train disruption messages via TrainAnnouncement."""

import requests

TRAFIKVERKET_API_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

# Station signatures: M=Malmö C, Tr=Triangeln, Hi=Hyllie, Lu=Lund C
CPH_STATIONS = {"M", "Tr", "Hi"}
LUND_STATIONS = {"M", "Tr", "Lu"}

# Deviation descriptions considered serious enough to surface
SERIOUS_DEVIATIONS = {
    "Inställt", "Växelfel", "Signalfel", "Spårfel", "Fordonsfel",
    "Banarbete", "Polisinsats", "Djur i spår", "Obeh. i spår",
    "Tågkö", "Banhinder", "Brist på fordon",
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
    Each value is a dict: {'count': int, 'reasons': list[str]}
    """
    announcements = fetch_train_messages(api_key)
    cph = {"count": 0, "reasons": set()}
    lund = {"count": 0, "reasons": set()}

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
            cph["count"] += 1
            cph["reasons"] |= serious
        if loc in LUND_STATIONS:
            lund["count"] += 1
            lund["reasons"] |= serious

    return {
        "malmö_cph": {"count": cph["count"], "reasons": sorted(cph["reasons"])},
        "malmö_lund": {"count": lund["count"], "reasons": sorted(lund["reasons"])},
    }


def _format_route(data: dict) -> str:
    count = data.get("count", 0)
    reasons = data.get("reasons", [])
    if count == 0:
        return "✅ Inga störningar"
    reason_str = f" ({', '.join(reasons)})" if reasons else ""
    return f"⚠️ {count} tåg påverkade{reason_str}"


def format_disruptions_telegram(disruptions: dict) -> str:
    """Format disruptions for Telegram message."""
    lines = ["🚂 *TÅGSTÖRNINGAR*"]
    lines.append("Malmö → Köpenhamn: " + _format_route(disruptions.get("malmö_cph", {})))
    lines.append("Malmö → Lund: " + _format_route(disruptions.get("malmö_lund", {})))
    return "\n".join(lines)
