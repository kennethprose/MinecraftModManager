import json
import os
import requests
import sys


def modrinth_api_call(endpoint):
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
    print("Downloading " + filename)
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
            json.dump(data, file, indent=4)
        print("mcmodmanager.json has been created.")
        exit()


def check_version_exists(version):

    valid_versions = modrinth_api_call("/tag/game_version")

    for v in valid_versions:
        if v["version"] == version:
            return True

    return False


def set_server_version(version):

    if not check_version_exists(version):
        print("[ERROR]: " + version + " is not a valid Minecraft version")
        exit()

    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)

    data["server_version"] = version

    with open("mcmodmanager.json", "w") as file:
        json.dump(data, file, indent=4)


def check_mod_exists(slug_or_id):
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        server_version = data["server_version"]
        mods = data["mods"]

    for i, mod in enumerate(mods):

        if mod["mod_id"] == slug_or_id or mod["mod_slug"] == slug_or_id:
            return True

    return False


def add_mod(slug_or_id):

    if check_mod_exists(slug_or_id):
        print("Mod is already installed")
        exit()

    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        server_version = data["server_version"]
        mods = data["mods"]

    mod_info = modrinth_api_call("/project/" + slug_or_id)
    mod_name = mod_info["title"]
    mod_id = mod_info["id"]
    mod_slug = mod_info["slug"]

    print("Adding mod: " + mod_name)

    mod_versions = modrinth_api_call(
        "/project/" + slug_or_id + "/version?game_versions=[\"" + server_version + "\"]&loaders=[\"fabric\"]")

    most_recent_version = mod_versions[0]
    mod_version_id = most_recent_version["id"]
    filename = most_recent_version["files"][0]["filename"]
    download_url = most_recent_version["files"][0]["url"]

    new_mod = {
        "mod_name": mod_name,
        "mod_slug": mod_slug,
        "mod_id": mod_id,
        "mod_version_id": mod_version_id,
        "filename": filename,
        "download_url": download_url,
        "current_version": server_version
    }

    mods.append(new_mod)

    download_mod(download_url, filename)

    with open("mcmodmanager.json", "w") as file:
        json.dump(data, file, indent=4)

    print(mod_name + " installed")


def remove_mod(slug_or_id):
    print("Removing mod...")

    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    for i, mod in enumerate(mods):

        if mod["mod_id"] == slug_or_id or mod["mod_slug"] == slug_or_id:

            mod_name = mod["mod_name"]

            os.remove(os.path.join("mods", mod["filename"]))

            mods.pop(i)

            with open("mcmodmanager.json", "w") as file:
                json.dump(data, file, indent=4)

            print("Successfully removed " + mod_name)
            return

    print("Mod not found")


def check_updates(version):

    if not check_version_exists(version):
        print("[ERROR]: " + version + " is not a valid Minecraft version")
        exit()

    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        server_version = data["server_version"]
        mods = data["mods"]

    mods_with_updates = []
    mods_without_updates = []

    if version == server_version:

        for mod in mods:

            mod_name = mod["mod_name"]
            mod_slug = mod["mod_slug"]
            mod_version_id = mod["mod_version_id"]

            mod_versions = modrinth_api_call(
                "/project/" + mod_slug + "/version?game_versions=[\"" + server_version + "\"]&loaders=[\"fabric\"]")
            newest_mod_version = mod_versions[0]

            if newest_mod_version["id"] != mod_version_id:

                new_mod_version_id = newest_mod_version["id"]
                new_mod_version_filename = newest_mod_version["files"][0]["filename"]
                new_mod_version_url = newest_mod_version["files"][0]["url"]

                update_info = {
                    "new_version_id": new_mod_version_id,
                    "new_filename": new_mod_version_filename,
                    "new_download_url": new_mod_version_url,
                    "new_version": server_version
                }

                mod["update"] = update_info

                mods_with_updates.append(mod_name)

            else:
                mods_without_updates.append(mod_name)

    else:

        for mod in mods:

            mod_name = mod["mod_name"]
            mod_slug = mod["mod_slug"]

            mod_versions = modrinth_api_call(
                "/project/" + mod_slug + "/version?game_versions=[\"" + version + "\"]&loaders=[\"fabric\"]")

            if len(mod_versions) > 0:

                new_mod = mod_versions[0]

                new_mod_id = new_mod["id"]
                new_mod_filename = new_mod["files"][0]["filename"]
                new_mod_url = new_mod["files"][0]["url"]

                update_info = {
                    "new_version_id": new_mod_id,
                    "new_filename": new_mod_filename,
                    "new_download_url": new_mod_url,
                    "new_version": version
                }

                mod["update"] = update_info

                mods_with_updates.append(mod_name)

            else:
                del mod["update"]

                mods_without_updates.append(mod_name)

    with open("mcmodmanager.json", "w") as file:
        json.dump(data, file, indent=4)

    print("\nUpdates available for:")
    for mod in mods_with_updates:
        print(mod)

    print("\nNo updates for:")
    for mod in mods_without_updates:
        print(mod)
    print()


def print_usage():
    print('''
    Usage: python mcmodmanager.py [OPTIONS]

    Options:
    -a, --add-mod ID|Slug               Install the mod with the specified ID or slug.
    -c, --check-updates VERSION         Check to see if mods have new versions available for specified Minecraft version. 
    -h, --help                          Prints usage.
    -r, --remove-mod ID|Slug            Remove the mod with the specified ID or slug.
    -s, --server-version VERSION        Change the stored value of your Minecraft server version to VERSION.
    ''')


def main():
    init_json_file()

    if len(sys.argv) > 1:

        match sys.argv[1]:
            case "-a" | "--add-mod":
                add_mod(sys.argv[2])
            case "-c" | "--check-updates":
                check_updates(sys.argv[2])
            case "-h" | "--help":
                print_usage()
            case "-r" | "--remove-mod":
                remove_mod(sys.argv[2])
            case "-s" | "--server-version":
                set_server_version(sys.argv[2])

    else:
        print_usage()


if __name__ == "__main__":
    main()
