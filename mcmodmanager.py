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


def curseforge_api_call(endpoint):
    base_url = "https://api.curseforge.com"
    url = base_url + endpoint
    headers = {
        "x-api-key": curseforge_api_key}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching data from CurseForge API. Status code: ",
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


def init_api_key():
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)

    global curseforge_api_key
    curseforge_api_key = data["curseforge_api_key"]


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


def set_curseforge_api_key(key):
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        data["curseforge_api_key"] = key

    with open("mcmodmanager.json", "w") as file:
        json.dump(data, file, indent=4)


def check_mod_exists(slug_or_id):
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    for i, mod in enumerate(mods):

        if mod["mod_id"] == slug_or_id or mod["mod_slug"] == slug_or_id:
            return True

    return False


def add_mod(source, slug_or_id):

    if check_mod_exists(slug_or_id):
        print("Mod is already installed")
        exit()

    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        server_version = data["server_version"]
        mods = data["mods"]

    if source == 'modrinth':
        mod_info = modrinth_api_call("/project/" + slug_or_id)
        mod_name = mod_info["title"]
        mod_id = mod_info["id"]
        mod_slug = mod_info["slug"]
    elif source == 'curseforge':
        mod_info = curseforge_api_call("/v1/mods/" + slug_or_id)
        mod_name = mod_info["data"]["name"]
        mod_id = str(mod_info["data"]["id"])
        mod_slug = mod_info["data"]["slug"]

    print("Adding mod: " + mod_name)

    if source == 'modrinth':
        mod_versions = modrinth_api_call(
            "/project/" + slug_or_id + "/version?game_versions=[\"" + server_version + "\"]&loaders=[\"fabric\"]")

        most_recent_version = mod_versions[0]
        mod_version_id = most_recent_version["id"]
        filename = most_recent_version["files"][0]["filename"]
        download_url = most_recent_version["files"][0]["url"]

    elif source == 'curseforge':
        mod_versions = curseforge_api_call(
            "/v1/mods/" + slug_or_id + "/files?gameVersion=" + server_version + "&modLoaderType=4")

        most_recent_version = mod_versions["data"][0]
        mod_version_id = str(most_recent_version["id"])
        filename = most_recent_version["fileName"]
        download_url = most_recent_version["downloadUrl"]

    new_mod = {
        "mod_name": mod_name,
        "mod_slug": mod_slug,
        "mod_id": mod_id,
        "mod_version_id": mod_version_id,
        "filename": filename,
        "download_url": download_url,
        "current_version": server_version,
        "source": source
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


def get_modrinth_mod_info(mod_slug, version, mod_version_id=None):

    mod_versions = modrinth_api_call(
        f"/project/{mod_slug}/version?game_versions=[\"{version}\"]&loaders=[\"fabric\"]")

    if mod_versions:
        newest_mod_version = mod_versions[0]

        if not mod_version_id or newest_mod_version["id"] != mod_version_id:

            new_mod_version_id = newest_mod_version["id"]
            new_mod_version_filename = newest_mod_version["files"][0]["filename"]
            new_mod_version_url = newest_mod_version["files"][0]["url"]

            return {
                "new_version_id": new_mod_version_id,
                "new_filename": new_mod_version_filename,
                "new_download_url": new_mod_version_url,
                "new_version": version
            }

    return None


def get_curseforge_mod_info(mod_id, version, mod_version_id=None):

    mod_versions = curseforge_api_call(
        f"/v1/mods/{mod_id}/files?gameVersion={version}&modLoaderType=4")

    if mod_versions:
        newest_mod_version = mod_versions["data"][0]

        if not mod_version_id or str(newest_mod_version["id"]) != mod_version_id:

            new_mod_version_id = str(newest_mod_version["id"])
            new_mod_version_filename = newest_mod_version["fileName"]
            new_mod_version_url = newest_mod_version["downloadUrl"]

            return {
                "new_version_id": new_mod_version_id,
                "new_filename": new_mod_version_filename,
                "new_download_url": new_mod_version_url,
                "new_version": version
            }

    return None


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
            mod_id = mod["mod_id"]
            mod_version_id = mod["mod_version_id"]
            mod_source = mod["source"]

            if mod_source == 'modrinth':
                update_info = get_modrinth_mod_info(
                    mod_slug, server_version, mod_version_id)
            elif mod_source == 'curseforge':
                update_info = get_curseforge_mod_info(
                    mod_id, server_version, mod_version_id)

            if update_info:
                mod["update"] = update_info
                mods_with_updates.append(mod_name)
            else:
                try:
                    del mod["update"]
                except KeyError:
                    pass
                mods_without_updates.append(mod_name)

    else:

        for mod in mods:

            mod_name = mod["mod_name"]
            mod_slug = mod["mod_slug"]
            mod_id = mod["mod_id"]
            mod_source = mod["source"]

            if mod_source == 'modrinth':
                update_info = get_modrinth_mod_info(mod_slug, version)
            elif mod_source == 'curseforge':
                update_info = get_curseforge_mod_info(mod_id, version)

            if update_info:
                mod["update"] = update_info
                mods_with_updates.append(mod_name)
            else:
                try:
                    del mod["update"]
                except KeyError:
                    pass
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


def check_pending_updates(version):

    pending_updates = 0

    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    for mod in mods:
        if "update" in mod:
            if mod["update"]["new_version"] == version:
                pending_updates += 1

    return pending_updates


def remove_mods_without_updates():

    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    mods_without_updates = []
    for mod in mods:
        if "update" not in mod:
            mods_without_updates.append(mod["mod_slug"])

    for mod_slug in mods_without_updates:
        remove_mod(mod_slug)


def update_mods(version):

    if not check_version_exists(version):
        print("[ERROR]: " + version + " is not a valid Minecraft version")
        exit()

    pending_updates = check_pending_updates(version)
    if pending_updates == 0:
        print("\nThere are no pending updates.\nCheck for updates by using the -c flag.\nSee usage (-h) for more information.\n")
        sys.exit()

    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]
        server_version = data["server_version"]

        # Only need to remove mods without updates if we are upgrading to a newer server version,
        # as that would lead to mod files for different versions of Minecraft
        if server_version != version and pending_updates < len(mods):

            confirmation = input(
                "\nAny mods that do not have pending updates will be removed. Do you want to proceed? (yes/no): ")

            if confirmation.lower() != "yes":
                sys.exit()

            remove_mods_without_updates()

        for mod in mods:
            if "update" in mod:

                # Remove old file
                os.remove(os.path.join("mods", mod["filename"]))

                # Download new file
                download_mod(mod["update"]["new_download_url"],
                             mod["update"]["new_filename"])

                # Copy 'update' data to primary data variables
                mod["mod_version_id"] = mod["update"]["new_version_id"]
                mod["filename"] = mod["update"]["new_filename"]
                mod["download_url"] = mod["update"]["new_download_url"]
                mod["current_version"] = mod["update"]["new_version"]

                # Remove pending update data
                del mod["update"]

                print(mod["mod_name"] + " has been updated")

    with open("mcmodmanager.json", "w") as file:
        json.dump(data, file, indent=4)

    set_server_version(version)


def print_usage():
    print('''
    Usage: python mcmodmanager.py [OPTIONS]

    Options:
    -a, --add-mod [Source] [ID|Slug]    Fetch and install the mod with the given ID or slug from the desired source (Modrinth or CurseForge).
    -c, --check-updates [VERSION]       Check to see if mods have new versions available for specified Minecraft version. 
    -h, --help                          Prints usage.
    -k, --api-key                       Set the API key that is required for CurseForge
    -r, --remove-mod [ID|Slug]          Remove the mod with the specified ID or slug.
    -s, --server-version [VERSION]      Change the stored value of your Minecraft server version to VERSION.
    -u, --update-mods [VERSION]         Removes any mods without pending updates to the desired version and updates the rest
    ''')


def main():
    init_json_file()
    init_api_key()

    if len(sys.argv) > 1:

        match sys.argv[1]:
            case "-a" | "--add-mod":
                add_mod(sys.argv[2], sys.argv[3])
            case "-c" | "--check-updates":
                check_updates(sys.argv[2])
            case "-h" | "--help":
                print_usage()
            case "-k" | "--api-key":
                set_curseforge_api_key(sys.argv[2])
            case "-r" | "--remove-mod":
                remove_mod(sys.argv[2])
            case "-s" | "--server-version":
                set_server_version(sys.argv[2])
            case "-u" | "--update-mods":
                update_mods(sys.argv[2])

    else:
        print_usage()


if __name__ == "__main__":
    main()
