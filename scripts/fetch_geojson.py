"""
scripts/fetch_geojson.py
========================
Downloads the official CC BY 4.0 BBMP Ward Boundary GeoJSON from DataMeet.
Saves to frontend/public/bbmp_wards.geojson.
"""

import os
import json
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Bangalore/BBMP.geojson"
TARGET_DIR = Path(__file__).parent.parent / "frontend" / "public"
TARGET_DIR.mkdir(parents=True, exist_ok=True)
TARGET_FILE = TARGET_DIR / "bbmp_wards.geojson"


def download_geojson():
    print(f"Downloading BBMP GeoJSON from DataMeet...")
    print(f"URL: {URL}")
    urllib.request.urlretrieve(URL, TARGET_FILE)
    print(f"Downloaded to {TARGET_FILE} ({TARGET_FILE.stat().st_size / 1024:.1f} KB)")

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"Features loaded: {len(features)}")
    if features:
        print("Sample properties:", features[0].get("properties"))


if __name__ == "__main__":
    download_geojson()
