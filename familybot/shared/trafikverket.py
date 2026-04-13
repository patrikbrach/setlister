"""Trafikverket API client for train disruption messages via TrainAnnouncement."""

import requests

TRAFIKVERKET_API_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"

# Station signatures: M=Malmö C, Tr=Triangeln, Hi=Hyllie, Lu=Lund C
CPH_STATIONS = {"M", "Tr", "Hi"}
LUND_STATIONS = {"M", "Tr", "Lu"}


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
    Each value is a deduplicated list of disruption description strings.
    """
    announcements = fetch_train_messages(api_key)
    result: dict[str, list[str]] = {"malmö_cph": [], "malmö_lund": []}

    seen_cph: set[str] = set()
    seen_lund: set[str] = set()

    for ann in announcements:
        loc = ann.get("LocationSignature", "")
        deviations = ann.get("Deviation", [])
        if not isinstance(deviations, list):
            deviations = [deviations]

        for dev in deviations:
            if not isinstance(dev, dict):
                continue
            text = dev.get("Description", "").strip() or "Avvikelse"

            if loc in CPH_STATIONS and text not in seen_cph:
                result["malmö_cph"].append(text)
                seen_cph.add(text)

            if loc in LUND_STATIONS and text not in seen_lund:
                result["malmö_lund"].append(text)
                seen_lund.add(text)

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
