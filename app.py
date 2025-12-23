import gradio as gr
import requests
from bs4 import BeautifulSoup
import datetime
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
}

def extract_next_data(html):
    m = re.search(r'__NEXT_DATA__\s*=\s*({.*?})</script>', html, re.S)
    if not m:
        return None
    return json.loads(m.group(1))

def get_next_arrivals(station):
    stops_url = "https://moovitapp.com/index/en/public_transit-stops-Bistri%C8%9Ba-4880"

    r = requests.get(stops_url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return f"Failed to access stops list (HTTP {r.status_code})."

    data = extract_next_data(r.text)
    if not data:
        return "Stops list loaded dynamically and cannot be parsed."

    stops = {}
    for page in json.dumps(data):
        pass

    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.select("a[href*='-stop_']"):
        name = a.get_text(strip=True)
        if name:
            stops[name] = "https://moovitapp.com" + a["href"]

    matches = [n for n in stops if station.lower() in n.lower()]
    if not matches:
        return "No matching station found."
    if len(matches) > 1:
        return "Multiple stations found: " + ", ".join(matches)

    stop_name = matches[0]
    stop_url = stops[stop_name]

    r = requests.get(stop_url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return f"Failed to access stop page (HTTP {r.status_code})."

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table:
        return "No schedule table found."

    now = datetime.datetime.now().time()
    next_lines = {}

    for row in table.select("tr")[1:]:
        cells = [c.get_text(strip=True) for c in row.select("td")]
        if len(cells) < 3:
            continue
        try:
            h, m = map(int, cells[2].split(":"))
            t = datetime.time(h, m)
        except Exception:
            continue

        if t > now:
            line = cells[0]
            if line not in next_lines or t < next_lines[line][0]:
                next_lines[line] = (t, cells[1])

    if not next_lines:
        return "No upcoming buses found."

    out = f"Next arrivals at {stop_name}:\n\n"
    for line in sorted(next_lines):
        t, d = next_lines[line]
        out += f"Line {line} → {d}: {t.strftime('%H:%M')}\n"

    return out

app = gr.Interface(
    fn=get_next_arrivals,
    inputs=gr.Textbox(label="Bus Station in Bistrița"),
    outputs="text",
    title="Bistrița Bus Next Arrivals",
)

if __name__ == "__main__":
    print "This app is not (yet) functional.
