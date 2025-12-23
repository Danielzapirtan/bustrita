import gradio as gr
import requests
import json

# Coordonatele aproximative pentru orașul Bistrița (pentru a limita căutarea la zonă relevantă)
BISTRITA_BBOX = "47.08,24.42,47.18,24.58"  # south, west, north, east

# Query Overpass API pentru toate stațiile de autobuz din Bistrița
# Folosim atât tag-ul clasic highway=bus_stop, cât și public_transport=platform cu bus=yes
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
QUERY = f"""
[out:json];
(
  node["highway"="bus_stop"]({BISTRITA_BBOX});
  node["public_transport"="platform"]["bus"="yes"]({BISTRITA_BBOX});
);
out body;
"""

response = requests.get(OVERPASS_URL, params={'data': QUERY})
data = response.json()

# Extragem numele stațiilor și coordonatele (lat, lon)
bus_stops = []
seen_names = set()
for element in data['elements']:
    if 'tags' in element and 'name' in element['tags']:
        name = element['tags']['name'].strip()
        if name not in seen_names:
            seen_names.add(name)
            lat = element['lat']
            lon = element['lon']
            bus_stops.append((name, lat, lon))

# Sortăm alfabetic pentru o listă ordonată
bus_stops.sort(key=lambda x: x[0])
stop_names = [stop[0] for stop in bus_stops]

# Dicționar pentru acces rapid la coordonate
stop_coords = {name: (lat, lon) for name, lat, lon in bus_stops}

def gaseste_ruta(start, destinatie):
    if start == destinatie:
        return "Stația de plecare și destinația sunt aceleași."
    
    if start not in stop_coords or destinatie not in stop_coords:
        return "Una dintre stații nu a fost găsită în baza de date."
    
    start_lat, start_lon = stop_coords[start]
    destin_lat, destin_lon = stop_coords[destinatie]
    
    # Apel către OSRM (Open Source Routing Machine) - profil public_transport (include autobuze unde sunt mapate)
    osrm_url = "http://router.project-osrm.org/route/v1/public_transport/"
    coords = f"{start_lon},{start_lat};{destin_lon},{destin_lat}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }
    
    osrm_response = requests.get(osrm_url + coords, params=params)
    
    if osrm_response.status_code != 200:
        return "Eroare la comunicarea cu serviciul de rutare."
    
    osrm_data = osrm_response.json()
    
    if osrm_data.get("code") != "Ok" or not osrm_data.get("routes"):
        return ("Nu s-a găsit nicio rută cu transport public între aceste stații.\n"
                "Notă: Datele de transport public în OpenStreetMap pentru Bistrița sunt limitate, "
                "deci este posibil să existe rute în realitate care nu sunt mapate complet.")
    
    route = osrm_data["routes"][0]
    durata = route["duration"] / 60  # în minute
    distanta = route["distance"] / 1000  # în km
    
    rezultat = f"**Durată estimată:** {durata:.1f} minute\n"
    rezultat += f"**Distanță:** {distanta:.1f} km\n\n"
    rezultat += "**Pași detaliați:**\n"
    
    for leg in route["legs"]:
        for step in leg["steps"]:
            instruction = step.get("instruction", "Continuați")
            if "name" in step:
                instruction += f" pe {step['name']}"
            distance_step = step["distance"] / 1000
            duration_step = step["duration"] / 60
            mode = step.get("mode", "unknown")
            if mode == "walking":
                rezultat += f"- Mergeți pe jos {distance_step:.2f} km ({duration_step:.1f} min): {instruction}\n"
            elif mode in ["bus", "public_transport"]:
                rezultat += f"- Luați autobuzul {distance_step:.2f} km ({duration_step:.1f} min): {instruction}\n"
            else:
                rezultat += f"- {mode.capitalize()}: {instruction} ({distance_step:.2f} km, {duration_step:.1f} min)\n"
    
    return rezultat

with gr.Blocks(title="Transport public Bistrița", theme=gr.themes.Soft()) as app:
    gr.Markdown("# Cum să ajung cu autobuzul în Bistrița")
    gr.Markdown("Selectați stația de plecare și destinația. Aplicația utilizează date OpenStreetMap și OSRM pentru a calcula ruta cu transport public (unde datele sunt disponibile).")
    
    with gr.Row():
        start_input = gr.Dropdown(choices=stop_names, label="Stație de plecare")
        dest_input = gr.Dropdown(choices=stop_names, label="Stație destinație")
    
    btn = gr.Button("Caută ruta")
    output = gr.Textbox(label="Rezultat")
    
    btn.click(fn=gaseste_ruta, inputs=[start_input, dest_input], outputs=output)

app.launch()