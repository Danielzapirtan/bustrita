import gradio as gr
import requests
from bs4 import BeautifulSoup
import datetime

def get_next_arrivals(station):
    # Step 1: Find the stop URL by scraping the stops list page
    stops_url = "https://moovitapp.com/index/en/public_transit-stops-Bistri%C8%9Ba-4880"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    response = requests.get(stops_url, headers=headers)
    if response.status_code != 200:
        return "Failed to access stops list."
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    stop_links = {}
    for a in soup.find_all('a', href=True):
        if '-stop_' in a['href'] and 'Bistri' in a['href']:
            name = a.text.strip()
            stop_links[name] = "https://moovitapp.com" + a['href']
    
    # Find matching station (case-insensitive partial match)
    matching = [name for name in stop_links if station.lower() in name.lower()]
    if not matching:
        return "No matching station found."
    if len(matching) > 1:
        return "Multiple stations found: " + ", ".join(matching) + ". Please be more specific."
    
    stop_name = matching[0]
    stop_url = stop_links[stop_name]
    
    # Step 2: Scrape the stop page for schedule
    response = requests.get(stop_url, headers=headers)
    if response.status_code != 200:
        return "Failed to access stop page."
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the schedule table (assuming it's the first table on the page)
    table = soup.find('table')
    if not table:
        return "No schedule table found on the page."
    
    # Get current time
    now = datetime.datetime.now()
    current_time = now.time()
    
    # Collect next arrivals per line
    lines_next = {}
    for row in table.find_all('tr')[1:]:  # Skip header
        cells = row.find_all('td')
        if len(cells) >= 3:
            line = cells[0].text.strip()
            direction = cells[1].text.strip()
            time_str = cells[2].text.strip()
            try:
                h, m = map(int, time_str.split(':'))
                arrival_time = datetime.time(h, m)
                if arrival_time > current_time:
                    if line not in lines_next or arrival_time < lines_next[line]['time']:
                        lines_next[line] = {'time': arrival_time, 'direction': direction}
            except ValueError:
                continue
    
    if not lines_next:
        return "No upcoming buses found for today."
    
    # Format output
    output = f"Next arrivals at {stop_name}:\n\n"
    for line, info in sorted(lines_next.items(), key=lambda x: x[0]):
        output += f"Line {line} to {info['direction']}: {info['time'].strftime('%H:%M')}\n"
    
    return output

# Create Gradio interface
app = gr.Interface(
    fn=get_next_arrivals,
    inputs=gr.Textbox(label="Bus Station in Bistrita"),
    outputs="text",
    title="Bistrita Bus Next Arrivals",
    description="Enter a bus station name in Bistrita to get the next arrival times for each bus line."
)

if __name__ == "__main__":
    app.launch()
