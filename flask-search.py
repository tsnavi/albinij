import requests
import concurrent.futures
from flask import Flask, render_template, request
# import json

# from datetime import datetime
# now = datetime.now()
# current_time = now.strftime("%H:%M:%S")

# def save_to_json(data, filename):
    # with open(filename, 'w') as f:
        # json.dump(data, f)
        

app = Flask(__name__)

# Function to search for an artist and retrieve the artist ID
def search_artist(artist_name, api_key):
    url = f"https://api.discogs.com/database/search?q={artist_name}&type=artist&per_page=1&token={api_key}"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for non-2xx responses
    data = response.json()
    if data['results']:
        return data['results'][0]['id']
    else:
        return None

def fetch_release_data(artist_id, api_key, page_number):
    url = f"https://api.discogs.com/artists/{artist_id}/releases?page={page_number}&per_page=100&type=master&token={api_key}"
    response = requests.get(url)
    try:
        response.raise_for_status()  # Raise an error for non-2xx responses
        return response.json()
    except requests.exceptions.HTTPError as e:
        # If a 404 error occurs (page not found), return an empty list to indicate no more data
        if response.status_code == 404:
            return []
        else:
            raise e  # Re-raise other HTTP errors

# Function to fetch all release data using concurrent requests
def fetch_all_release_data(artist_id, api_key):
    data = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        page_number = 1

        while True:
            # Submit the fetch_release_data function with the current page number
            futures.append(executor.submit(fetch_release_data, artist_id, api_key, page_number))
            page_number += 1

            # Break out of the loop if the last request returned an empty list (indicating no more data)
            if not futures[-1].result():
                break

        # Wait for all futures to complete and collect results
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    data.append(result)
            except Exception as e:
                print(f"Error processing data: {e}")

    return data
    

# Function to filter duplicate titles and keep only the oldest year value
def filter_duplicates(data):
    unique_titles = {}
    filtered_data = []
    
    for release in data:
        filtered_releases = []
        for item in release['releases']:
            # print(current_time," - ",dir(release))
            title = item['title']
            year = item.get('year')  # Use item.get('year') to handle missing 'year' key
            if year is not None and (title not in unique_titles or unique_titles[title] > year):
                unique_titles[title] = year
                item['url'] = item.get('resource_url', '')
                item['role'] = item.get('role', '')
                filtered_releases.append(item)
        # Add filtered releases to the filtered data
        filtered_data.append({'releases': filtered_releases})

    return filtered_data


@app.route('/')
def index():
    api_key = request.args.get('api_key', default=None)
    artist_id = request.args.get('artist_id', default=None)
    if not artist_id:
        artist_name = request.args.get('artist_name', default='')
        if artist_name:
            # Search for the artist and retrieve the artist ID
            artist_id = search_artist(artist_name, api_key)
    release_data = []
    if artist_id:
            # Fetch all release data for the artist using concurrent requests
            all_release_data = fetch_all_release_data(artist_id, api_key)
            # Filter duplicates and keep only the oldest year value
            release_data = filter_duplicates(all_release_data)
    return render_template('index.html', release_data=release_data)

if __name__ == '__main__':
    app.run(debug=True)
