import requests
import math


class FastOpenSkyWrapper:
    """
    Un wrapper léger pour récupérer uniquement l'ID, la vitesse et le cap
    des avions dans un rayon donné.
    """

    def __init__(self, username=None, password=None):
        self.base_url = "https://opensky-network.org/api/states/all"
        self.auth = (username, password) if username and password else None

    def _get_bounding_box(self, lat, lon, radius_km):
        """Calcule la zone de recherche pour filtrer la requête API."""
        lat_delta = radius_km / 111.32
        lon_delta = radius_km / (111.32 * math.cos(math.radians(lat)))
        return {
            "lamin": lat - lat_delta,
            "lamax": lat + lat_delta,
            "lomin": lon - lon_delta,
            "lomax": lon + lon_delta
        }

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Calcule la distance réelle pour le filtrage circulaire."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def get_essential_telemetry(self, lat, lon, radius_km):
        """
        Récupère l'ID, la vitesse et le cap des avions à proximité.
        """
        bbox = self._get_bounding_box(lat, lon, radius_km)

        try:
            response = requests.get(
                self.base_url,
                params=bbox,  # OpenSky accepte directement lamin, lomin, lamax, lomax
                auth=self.auth,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if not data or not data.get("states"):
                return []

            nearby_flights = []

            for state in data["states"]:
                flight_lon = state[5]
                flight_lat = state[6]

                if flight_lat is None or flight_lon is None:
                    continue

                distance = self._haversine(lat, lon, flight_lat, flight_lon)

                if distance <= radius_km:
                    nearby_flights.append({
                        "id_icao24": state[0],
                        "callsign": state[1].strip() if state[1] else "N/A",
                        "vitesse_kmh": round(state[9] * 3.6, 1) if state[9] else 0.0,
                        "cap_degres": state[10] if state[10] else 0.0,
                        "distance_km": round(distance, 2),
                        "latitude": flight_lat,
                        "longitude": flight_lon
                    })

            # Tri par distance (optionnel mais souvent utile)
            return sorted(nearby_flights, key=lambda x: x["distance_km"])

        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête API : {e}")
            return []


# ==========================================
# Exemple d'exécution
# ==========================================
if __name__ == "__main__":
    api = FastOpenSkyWrapper()

    # Coordonnées (Ex: Centre-ville de Toulouse)
    ma_lat = 43.6047
    ma_lon = 1.4442
    rayon = 20.0

    print(f"Recherche de télémétrie dans un rayon de {rayon} km...\n")

    avions = api.get_essential_telemetry(ma_lat, ma_lon, rayon)

    if avions:
        for avion in avions:
            print(f"🎯 ID (ICAO24) : {avion['id_icao24']} | Vol : {avion['callsign']}")
            print(f"   Vitesse     : {avion['vitesse_kmh']} km/h")
            print(f"   Cap         : {avion['cap_degres']}°")
            print(f"   Distance    : {avion['distance_km']} km")
            print("-" * 45)
    else:
        print("Aucun aéronef détecté dans la zone.")