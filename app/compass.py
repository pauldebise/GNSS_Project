import math
import requests
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

# Importation de ton module depuis l'autre fichier
from gps.plane_info_receiver import FastOpenSkyWrapper

# Configuration
RAYON_RECHERCHE = 20.0  # Rayon en kilomètres
INTERVALLE_MAJ = 10000  # Intervalle de mise à jour en millisecondes (10 secondes)


def get_user_location():
    """Récupère la position GPS locale de l'utilisateur via son IP."""
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5)
        response.raise_for_status()
        data = response.json()
        loc = data.get("loc", "0,0").split(",")
        lat, lon = float(loc[0]), float(loc[1])
        ville = data.get("city", "Inconnue")
        return lat, lon, ville
    except Exception as e:
        print(f"Erreur de géolocalisation : {e}")
        return 48.8566, 2.3522, "Paris (Défaut)"


def calculate_azimut(lat1, lon1, lat2, lon2):
    """Calcule l'azimut (l'angle par rapport au Nord) entre l'utilisateur et l'avion."""
    lat1_r, lon1_r, lat2_r, lon2_r = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2_r - lon1_r

    y = math.sin(dlon) * math.cos(lat2_r)
    x = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)

    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360


# Initialisation des variables globales pour l'animation
ma_lat, ma_lon, ma_ville = get_user_location()
api = FastOpenSkyWrapper()

# Préparation de la figure Matplotlib
fig, ax = plt.subplots(figsize=(10, 10), facecolor='black')


def update_radar(frame):
    """Fonction de mise à jour appelée toutes les 10 secondes."""
    print("🔄 Balayage du ciel et mise à jour des cibles...")

    # Récupération des nouvelles données
    cibles = api.get_essential_telemetry(ma_lat, ma_lon, RAYON_RECHERCHE)

    # Nettoyage de l'ancien affichage pour redessiner
    ax.clear()
    ax.set_facecolor('black')
    ax.set_aspect('equal')

    # Dimensions du radar
    limit = RAYON_RECHERCHE * 1.1
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)

    # Dessin des cercles concentriques (Boussole)
    step = 10 if RAYON_RECHERCHE <= 50 else 20
    for r in np.arange(step, RAYON_RECHERCHE + 1, step):
        circle = plt.Circle((0, 0), r, color='#004400', fill=False, linestyle='--', linewidth=1)
        ax.add_patch(circle)
        ax.text(0, r + (RAYON_RECHERCHE * 0.02), f"{int(r)}km", color='#00aa00', fontsize=8, ha='center')

    # Croix cardinale
    ax.axhline(0, color='#004400', linestyle='-', linewidth=1)
    ax.axvline(0, color='#004400', linestyle='-', linewidth=1)

    # Centre : Position de l'utilisateur
    ax.plot(0, 0, marker='+', color='white', markersize=15)
    ax.text(0, -(RAYON_RECHERCHE * 0.04), f"VOUS\n({ma_ville})", color='white', fontsize=9, ha='center', va='top')

    # Placement des avions
    for avion in cibles:
        if 'latitude' not in avion or 'longitude' not in avion:
            continue
        if avion['vitesse_kmh'] < 40.0:
            continue

        # Calcul de la position cartésienne
        azimut = calculate_azimut(ma_lat, ma_lon, avion['latitude'], avion['longitude'])
        theta = math.radians(90 - azimut)
        x = avion['distance_km'] * math.cos(theta)
        y = avion['distance_km'] * math.sin(theta)

        # Tracé du spot de l'avion
        ax.plot(x, y, marker='o', color='cyan', markersize=5)

        # Identifiant du vol
        label = avion['callsign'] if avion['callsign'] != "N/A" else avion['id_icao24']
        ax.text(x, y - (RAYON_RECHERCHE * 0.03), label, color='white', fontsize=8, ha='center', va='top')

        # Vecteur de vitesse et cap (Flèche)
        v_scale = avion['vitesse_kmh'] / 50.0
        cap_rad = math.radians(90 - avion['cap_degres'])
        dx = v_scale * math.cos(cap_rad)
        dy = v_scale * math.sin(cap_rad)

        ax.arrow(x, y, dx, dy, head_width=RAYON_RECHERCHE * 0.015, head_length=RAYON_RECHERCHE * 0.02,
                 fc='red', ec='red', alpha=0.8, length_includes_head=True)

    # Suppression des graduations d'axes et mise à jour du titre
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"Radar Trafic Aérien ({len(cibles)} cibles) - Rayon {RAYON_RECHERCHE} km\nMise à jour toutes les 10s",
                 color='lime', pad=20)

    plt.tight_layout()


# ==========================================
# Lancement de l'animation
# ==========================================
if __name__ == "__main__":
    print(f"📍 Position détectée : {ma_ville} ({ma_lat}, {ma_lon})")
    print("Démarrage du radar en temps réel...")

    # Utilisation de FuncAnimation pour gérer la boucle de rafraîchissement
    ani = animation.FuncAnimation(fig, update_radar, interval=INTERVALLE_MAJ, cache_frame_data=False)

    plt.show()