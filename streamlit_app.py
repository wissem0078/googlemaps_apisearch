# streamlit_app.py

import os
import streamlit as st
import googlemaps
import pandas as pd
import re
import math
import time

def haversine(lat1, lng1, lat2, lng2):
    """Berechnet die Distanz (in Metern) zwischen zwei Geo-Punkten."""
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

st.title("Multi-Place-Suche mit Google Maps API")

# API-Key aus Streamlit Secrets / Umgebungsvariable
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ Bitte setze in den Streamlit-Secrets den Schlüssel GOOGLE_API_KEY.")
    st.stop()

# Eingabefelder
queries = st.text_input("Suchbegriffe (kommagetrennt)", "coach,Arzt,Trainer")
lat     = st.number_input("Latitude",  value=51.0341, format="%.6f")
lng     = st.number_input("Longitude", value=7.8578, format="%.6f")
radius  = st.number_input("Radius (m)", value=35000, step=100)

if st.button("Suche starten"):
    gmaps   = googlemaps.Client(key=api_key)
    results = []

    for q in [q.strip() for q in queries.split(",") if q.strip()]:
        st.write(f"🔍 Suche nach: **{q}** …")
        page_token = None

        # Paginierte Nearby-Search
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

                detail = gmaps.place(
                    place_id=p["place_id"],
                    fields=[
                        "name",
                        "formatted_address",
                        "formatted_phone_number",
                        "international_phone_number"
                    ]
                )["result"]

                name  = detail.get("name", "")
                addr  = detail.get("formatted_address", "")
                phone = detail.get("formatted_phone_number") or detail.get("international_phone_number", "")

                # Adresse parsen
                m = re.match(r"^(.*?)\s+(\d+\w*),\s*(\d{5})\s+(.*)$", addr)
                if m:
                    street, housenr, plz, city = m.groups()
                else:
                    parts         = [x.strip() for x in addr.split(",")]
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
                    "Entfernung (m)": int(d)
                })

            page_token = res.get("next_page_token")
            if not page_token:
                break
            time.sleep(2)

    # Ergebnis anzeigen und Download-Button
    df = pd.DataFrame(results)
    st.dataframe(df)
    st.download_button(
        label="Excel herunterladen",
        data=df.to_excel(index=False),
        file_name="results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
