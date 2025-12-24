import gradio as gr
import requests

def fetch_stops():
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = '''
    [out:json][timeout:25];
    area["name"="București"]["admin_level"="4"]->.searchArea;
    node(area.searchArea)["highway"="bus_stop"]["name"];
    out body;
    '''
    response = requests.post(overpass_url, data={'data': query})
    
    if response.status_code != 200:
        return []
    
    data = response.json()
    names = set()
    
    for elem in data['elements']:
        name = elem['tags'].get('name')
        if name:
            names.add(name)
    
    return sorted(names)

stops_list = fetch_stops()

def find_route(from_stop, to_stop):
    if from_stop == to_stop:
        return "Stațiile de plecare și sosire sunt identice."
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = '''
    [out:json][timeout:25];
    area["name"="București"]["admin_level"="4"]->.searchArea;
    rel(area.searchArea)["type"="route"]["route"="bus"];
    out body;
    >;
    out skel qt;
    '''
    
    response = requests.post(overpass_url, data={'data': query})
    
    if response.status_code != 200:
        return "A apărut o eroare la interogarea datelor."
    
    data = response.json()
    
    # Map node IDs to names
    id_to_name = {}
    for elem in data['elements']:
        if elem['type'] == 'node' and 'tags' in elem and 'name' in elem['tags']:
            id_to_name[elem['id']] = elem['tags']['name']
    
    routes = []
    
    for elem in data['elements']:
        if elem['type'] == 'relation':
            tags = elem['tags']
            ref = tags.get('ref', tags.get('name', 'necunoscută'))
            stops_in_route = []
            
            for member in elem['members']:
                # Accept nodes with role 'stop', 'platform', or empty role
                if member['type'] == 'node':
                    role = member.get('role', '')
                    if role in ['stop', 'platform', ''] or role.startswith('platform') or role.startswith('stop'):
                        node_id = member['ref']
                        name = id_to_name.get(node_id)
                        if name:
                            stops_in_route.append(name)
            
            if from_stop in stops_in_route and to_stop in stops_in_route:
                try:
                    idx_from = stops_in_route.index(from_stop)
                    idx_to = stops_in_route.index(to_stop)
                    
                    if idx_from < idx_to:
                        intermediate = stops_in_route[idx_from + 1: idx_to]
                        route_info = f"Linia {ref}: {' -> '.join([from_stop] + intermediate + [to_stop])}"
                        routes.append(route_info)
                except ValueError:
                    pass
    
    if routes:
        return "\n\n".join(routes)
    else:
        return "Nu există un traseu direct cu autobuzul între stațiile selectate."

with gr.Blocks() as app:
    gr.Markdown("### Aplicație pentru trasee de autobuz în București")
    
    from_dropdown = gr.Dropdown(choices=stops_list, label="Stație de plecare")
    to_dropdown = gr.Dropdown(choices=stops_list, label="Stație de sosire")
    output = gr.Textbox(label="Informații traseu", lines=10)
    
    btn = gr.Button("Căutare traseu")
    btn.click(find_route, inputs=[from_dropdown, to_dropdown], outputs=output)

if __name__ == "__main__":
    app.launch()