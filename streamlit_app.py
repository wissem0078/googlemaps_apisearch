import io
import time
import re
import math

import streamlit as st
import pandas as pd
import googlemaps
from googlemaps.exceptions import ApiError

# ── API‑Key aus Streamlit‑Secrets (le­ge in .streamlit/secrets.toml an):
# [googlemaps]
# api_key = "AIzaSyBgR_NacUFMmP4Nl-qCadyZ0rG4frXdbUc"
api_key = st.secrets["googlemaps"]["api_key"]
gmaps    = googlemaps.Client(key=api_key)

def haversine(lat1, lng1, lat2, lng2):
    """Berechnet die Distanz (in Metern) zwischen zwei Geo‑Punkten."""
    R   = 6371000
    φ1  = math.radians(lat1)
    φ2  = math.radians(lat2)
    Δφ  = math.radians(lat2 - lat1)
    Δλ  = math.radians(lng2 - lng1)
    a   = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

st.title("Multi‑Place‑Suche mit Google Maps API")

# ── Eingabefelder
queries = st.text_input("Suchbegriffe (kommagetrennt)", "coach,Arzt,Trainer")
lat     = st.number_input("Latitude",  value=51.0341, format="%.6f")
lng     = st.number_input("Longitude", value=7.8578, format="%.6f")
radius  = st.number_input("Radius (m)", value=35000, step=100)

if st.button("Suche starten"):
    results      = []
    queries_list = [q.strip() for q in queries.split(",") if q.strip()]

    for q in queries_list:
        st.write(f"🔍 Suche nach: **{q}** …")
        try:
            page_token = None
            while True:
                res = gmaps.places_nearby(
                    location=(lat, lng),
                    radius=radius,
                    keyword=q,
                    page_token=page_token
                )
                for p in res.get("results", []):
                    loc = p["geometry"]["location"]
                    d   = haversine(lat, lng, loc["lat"], loc["lng"])
                    if d > radius:
                        continue

                    # Detail‑Abfrage inklusive Website
                    try:
                        detail = gmaps.place(
                            place_id=p["place_id"],
                            fields=[
                                "name",
                                "formatted_address",
                                "formatted_phone_number",
                                "international_phone_number",
                                "website"
                            ]
                        )["result"]
                    except ApiError as e:
                        st.warning(f"⚠️ Detail‑Abfrage fehlgeschlagen: {e}")
                        continue

                    name    = detail.get("name", "")
                    addr    = detail.get("formatted_address", "")
                    phone   = detail.get("formatted_phone_number") or detail.get("international_phone_number", "")
                    website = detail.get("website", "")

                    # Adresse parsen
                    m = re.match(r"^(.*?)\s+(\d+\w*),\s*(\d{5})\s+(.*)$", addr)
                    if m:
                        street, housenr, plz, city = m.groups()
                    else:
                        parts          = [x.strip() for x in addr.split(",")]
                        street, housenr = parts[0], ""
                        plz, city       = ("", parts[-1]) if len(parts) > 1 else ("", "")

                    results.append({
                        "Suchbegriff":    q,
                        "Name":           name,
                        "Straße":         street,
                        "Hausnummer":     housenr,
                        "PLZ":            plz,
                        "Ort":            city,
                        "Telefon":        phone,
                        "Website":        website,
                        "Entfernung (m)": int(d)
                    })

                page_token = res.get("next_page_token")
                if not page_token:
                    break
                time.sleep(2)

        except ApiError as e:
            st.error(f"❌ Fehler bei Google‑Maps‑Suche für “{q}”: {e}")
            continue

    if results:
        df = pd.DataFrame(results)
        st.dataframe(df)

        # Excel in-memory erzeugen
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Ergebnisse")
        data = output.getvalue()

        st.download_button(
            label="Excel herunterladen",
            data=data,
            file_name="results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Keine Ergebnisse gefunden.")
