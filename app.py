import gradio as gr
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_stops():
    query = """
    [out:json][timeout:90];
    area["name"="Bistrița"]["admin_level"="8"]["boundary"="administrative"]->.a;
    (
      node(area.a)["public_transport"="stop_position"]["bus"="yes"];
      node(area.a)["highway"="bus_stop"];
      node(area.a)["public_transport"="platform"]["bus"="yes"];
      way(area.a)["public_transport"="platform"]["bus"="yes"];
      relation(area.a)["public_transport"="stop_area"];
    );
    out geom;
    """
    try:
        r = requests.post(OVERPASS_URL, data={"data": query})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return ["Eroare la preluarea stațiilor: " + str(e)]

    stops = set()
    for e in data["elements"]:
        name = e.get("tags", {}).get("name") or e.get("tags", {}).get("local_ref")
        if name:
            stops.add(name)

    return sorted(stops) if stops else ["Nicio stație găsită"]


stops_list = fetch_stops()


def find_route(from_stop, to_stop):
    if from_stop == to_stop:
        return "Stațiile sunt identice."
    if not from_stop or not to_stop:
        return "Selectați ambele stații."

    query = """
    [out:json][timeout:180];
    area["name"="Bistrița"]["admin_level"="8"]["boundary"="administrative"]->.a;
    relation(area.a)["type"="route"]["route"="bus"]->.routes;
    (.routes; .routes >; .routes >>;);
    out geom;
    """
    try:
        r = requests.post(OVERPASS_URL, data={"data": query})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return "Eroare API: " + str(e)

    # Map element IDs to names
    name_map = {}
    for e in data["elements"]:
        if "name" in e.get("tags", {}):
            name_map[e["id"]] = e["tags"]["name"]

    routes_found = []
    for rel in [e for e in data["elements"] if e["type"] == "relation" and e.get("tags", {}).get("type") == "route"]:
        ref = rel.get("tags", {}).get("ref", rel.get("tags", {}).get("name", "?"))
        stops = []
        for m in rel.get("members", []):
            if m["role"] in {"platform", "stop", "platform_entry_only", "platform_exit_only", "stop_entry_only", "stop_exit_only", ""}:
                name = name_map.get(m["ref"])
                if name:
                    stops.append(name)

        if from_stop in stops and to_stop in stops:
            i1 = stops.index(from_stop)
            i2 = stops.index(to_stop)
            if i1 < i2:
                segment = " → ".join(stops[i1:i2 + 1])
                routes_found.append(f"Linia {ref}: {segment}")
            elif i2 < i1:  # Check reverse for completeness
                segment = " → ".join(stops[i2:i1 + 1][::-1])
                routes_found.append(f"Linia {ref} (sens opus): {segment}")

    return "\n\n".join(routes_found) if routes_found else "Niciun traseu direct găsit."


with gr.Blocks() as app:
    gr.Markdown("### Trasee autobuz Bistrița (OpenStreetMap)")

    f = gr.Dropdown(stops_list, label="Stație plecare")
    t = gr.Dropdown(stops_list, label="Stație sosire")
    out = gr.Textbox(lines=10, label="Rezultate")

    gr.Button("Caută").click(find_route, [f, t], out)

if __name__ == "__main__":
    app.launch()