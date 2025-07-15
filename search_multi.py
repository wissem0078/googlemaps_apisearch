#!/usr/bin/env python3
# search_multi.py

import googlemaps
import pandas as pd
import re
import argparse
import math
from time import sleep

def haversine(lat1, lng1, lat2, lng2):
    """Berechnet die Luftlinie zwischen zwei Punkten (in Metern)."""
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def main():
    parser = argparse.ArgumentParser(
        description="Mehrfach-Places-Search um einen Punkt herum via Google Maps API"
    )
    parser.add_argument("--api_key", required=True, help="Google Maps API-Key")
    parser.add_argument("--lat",     type=float, required=True, help="Breitengrad")
    parser.add_argument("--lng",     type=float, required=True, help="Längengrad")
    parser.add_argument("--radius",  type=int,   default=35000,    help="Radius in Metern")
    parser.add_argument("--queries", required=True,
                        help="Kommagetrennte Suchbegriffe, z.B. coach,Arzt,Trainer")
    parser.add_argument("--output",  default="results.xlsx",
                        help="Name der Excel-Ausgabedatei")
    args = parser.parse_args()

    gmaps    = googlemaps.Client(key=args.api_key)
    queries  = [q.strip() for q in args.queries.split(",") if q.strip()]
    all_data = []
    seen_ids = set()

    for query in queries:
        print(f"→ Suche nach '{query}' …")
        page_token = None
        places     = []

        while True:
            res = gmaps.places_nearby(
                location=(args.lat, args.lng),
                radius=args.radius,
                keyword=query,
                page_token=page_token
            )
            places.extend(res.get("results", []))
            page_token = res.get("next_page_token")
            if not page_token:
                break
            sleep(2)

        for p in places:
            pid = p["place_id"]
            if pid in seen_ids:
                continue
            seen_ids.add(pid)

            loc  = p["geometry"]["location"]
            dist = haversine(args.lat, args.lng, loc["lat"], loc["lng"])
            if dist > args.radius:
                continue

            detail = gmaps.place(
                place_id=pid,
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

            m = re.match(r"^(.*?)\s+(\d+\w*),\s*(\d{5})\s+(.*)$", addr)
            if m:
                street, housenr, plz, city = m.groups()
            else:
                parts          = [x.strip() for x in addr.split(",")]
                street, housenr = parts[0], ""
                plz, city       = ("", parts[-1]) if len(parts) > 1 else ("", "")

            all_data.append({
                "Suchbegriff":    query,
                "Name":           name,
                "Straße":         street,
                "Hausnummer":     housenr,
                "PLZ":            plz,
                "Ort":            city,
                "Telefon":        phone,
                "Entfernung (m)": int(dist)
            })

    df = pd.DataFrame(all_data)
    df.to_excel(args.output, index=False)
    print(f"✅ {len(df)} Einträge in '{args.output}' gespeichert.")

if __name__ == "__main__":
    main()
