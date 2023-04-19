import json
import os
import requests
import sys


def get_modrinth_data(endpoint):
    base_url = "https://api.modrinth.com/v2"
    url = base_url + endpoint
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching data from Modrinth API. Status code: ",
              response.status_code)
        return None


def download_mod(url, filename):
    if not os.path.exists("mods"):
        os.makedirs("mods")
    filepath = os.path.join("mods", filename)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print("Downloaded " + filename)


def init_json_file():
    if os.path.exists("mcmodmanager.json"):
        return
    else:
        print("[ERROR] Could not find mcmodmanager.json")
        with open("mcmodmanager.json", "w") as file:
            data = {"mods": []}
            json.dump(data, file)
        print("mcmodmanager.json has been created.")
        exit()


def set_server_version(version):
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)

    data["server_version"] = version

    with open("mcmodmanager.json", "w") as file:
        json.dump(data, file)


def add_mod(slug_or_id):
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        server_version = data["server_version"]
        mods = data["mods"]

    mod_info = get_modrinth_data("/project/" + slug_or_id)
    mod_name = mod_info["title"]
    mod_id = mod_info["id"]

    # TODO: Check if the mod already exists

    print("Adding mod: " + mod_name)

    mod_versions = get_modrinth_data(
        "/project/" + slug_or_id + "/version?game_versions=[\"" + server_version + "\"]&loaders=[\"fabric\"]")

    most_recent_version = mod_versions[0]
    mod_version_id = most_recent_version["id"]
    filename = most_recent_version["files"][0]["filename"]
    download_url = most_recent_version["files"][0]["url"]

    new_mod = {
        "mod_name": mod_name,
        "mod_id": mod_id,
        "mod_version_id": mod_version_id,
        "filename": filename,
        "download_url": download_url,
        "current_version": server_version
    }

    mods.append(new_mod)

    download_mod(download_url, filename)

    with open("mcmodmanager.json", "w") as file:
        json.dump(data, file)

    print("Mod successfully added")


def main():
    init_json_file()

    if sys.argv[1] == "-s":
        set_server_version(sys.argv[2])
    elif sys.argv[1] == "-a":
        add_mod(sys.argv[2])


if __name__ == "__main__":
    main()
