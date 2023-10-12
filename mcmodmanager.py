import argparse
import hashlib
import json
import os
import requests
import sys
import datetime


version = 'v231011'


def check_new_version():
    response = requests.get(
        "https://api.github.com/repos/kennethprose/MinecraftModManager/releases/latest")
    latest_version = response.json()["tag_name"]
    if latest_version > version:
        message(
            f"[ALERT] A new verison of MCModManager is available. Download {latest_version} here: https://github.com/kennethprose/MinecraftModManager/releases/tag/{latest_version}")


def message(message=""):
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{formatted_time}] {message}")


def modrinth_api_call(endpoint):
    base_url = "https://api.modrinth.com/v2"
    url = base_url + endpoint
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
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
        return None


def download_mod(url, filename):
    if debug_mode:
        message("Downloading " + filename)
    if not os.path.exists("mods"):
        os.makedirs("mods")
    filepath = os.path.join("mods", filename)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    if debug_mode:
        message("Downloaded " + filename)


def init_json_file():
    if os.path.exists("mcmodmanager.json"):
        return
    else:
        message("[ERROR] Could not find mcmodmanager.json")
        with open("mcmodmanager.json", "w") as file:
            data = {"mods": []}
            json.dump(data, file, indent=4)
        message("mcmodmanager.json has been created.")
        exit()


def init_server_version():
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)

    if "server_version" not in data:
        message("[ERROR]: Server version not set. Set the server version using the -s flag. See usage (-h) for more information.")
        exit()


def check_for_curseforge_mods():
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    for mod in mods:
        if mod["source"] == 'curseforge':
            return True

    return False


def init_api_key():
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)

    if "curseforge_api_key" in data:
        global curseforge_api_key
        curseforge_api_key = data["curseforge_api_key"]
    elif not check_for_curseforge_mods():
        return
    else:
        message("[ERROR]: Curseforge API key not set. Set API key by using the -k flag. See usage (-h) for more information.")
        sys.exit()


def check_version_exists(version):

    valid_versions = modrinth_api_call("/tag/game_version")

    for v in valid_versions:
        if v["version"] == version:
            return True

    return False


def set_server_version(version):

    if not check_version_exists(version):
        message("[ERROR]: " + version + " is not a valid Minecraft version")
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


def add_mod(source, mods_to_add):

    mod_list = mods_to_add.split(",")

    for slug_or_id in mod_list:

        if check_mod_exists(slug_or_id):
            message(f"{slug_or_id} is already installed")
            continue

        with open("mcmodmanager.json", "r") as file:
            data = json.load(file)
            server_version = data["server_version"]
            mods = data["mods"]

        if source == 'modrinth':
            mod_info = modrinth_api_call("/project/" + slug_or_id)
            if mod_info == None:
                message(
                    f"[ERROR]: {slug_or_id} not found. Make sure the slug/ID is correct.")
                continue
            mod_name = mod_info["title"]
            mod_id = mod_info["id"]
            mod_slug = mod_info["slug"]
        elif source == 'curseforge':
            mod_info = curseforge_api_call("/v1/mods/" + slug_or_id)
            if mod_info == None:
                message(
                    f"[ERROR]: {slug_or_id} not found. Make sure the ID is correct.")
                continue
            mod_name = mod_info["data"]["name"]
            mod_id = str(mod_info["data"]["id"])
            mod_slug = mod_info["data"]["slug"]
        else:
            message("[ERROR] \'" + source + "\' is not a valid source")
            continue

        if debug_mode:
            message("Adding mod: " + mod_name)

        if source == 'modrinth':
            mod_versions = modrinth_api_call(
                f"/project/{slug_or_id}/version?game_versions=[\"{server_version}\"]&loaders=[\"fabric\"]")
            most_recent_version = mod_versions[0]
            mod_version_id = most_recent_version["id"]
            filename = most_recent_version["files"][0]["filename"]
            download_url = most_recent_version["files"][0]["url"]

        elif source == 'curseforge':
            mod_versions = curseforge_api_call(
                f"/v1/mods/{slug_or_id}/files?gameVersion={server_version}&modLoaderType=4")
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

        message(mod_name + " installed")


def remove_mod(slug_or_id):
    if debug_mode:
        message("Removing mod...")

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

            message("Successfully removed " + mod_name)
            return

    message("Mod not found")


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
        message("[ERROR]: " + version + " is not a valid Minecraft version")
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

    message()
    message("Updates available for:")
    for mod in mods_with_updates:
        message(mod)

    message()
    message("No updates for:")
    for mod in mods_without_updates:
        message(mod)
    message()


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
        message("[ERROR]: " + version + " is not a valid Minecraft version")
        exit()

    pending_updates = check_pending_updates(version)
    if pending_updates == 0:
        message("\nThere are no pending updates.\nCheck for updates by using the -c flag.\nSee usage (-h) for more information.\n")
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

                message(mod["mod_name"] + " has been updated")

    with open("mcmodmanager.json", "w") as file:
        json.dump(data, file, indent=4)

    set_server_version(version)


def list_mods():

    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    message()
    message("Installed Mods:")

    for mod in mods:
        message(mod["mod_name"])

    message()


def generate_file_sha1_hash(file_path):
    sha1_hash = hashlib.sha1()
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            sha1_hash.update(chunk)
    return sha1_hash.hexdigest()


def import_mods():
    # Iterate over all mods in the mods folder
    for filename in os.listdir('./mods/'):
        file_path = os.path.join('./mods/', filename)
        if os.path.isfile(file_path) and file_path.endswith('.jar'):

            # Get the hash of the function and use it to check the modrinth api
            sha1_hash = generate_file_sha1_hash(file_path)
            mod_info = modrinth_api_call('/version_file/' + sha1_hash)

            if mod_info == None:
                message('Could not identify the mod at ' + file_path)
            else:

                # If mod is found, get relevant info
                mod_id = mod_info["project_id"]
                mod_version_id = mod_info["id"]
                download_url = mod_info["files"][0]["url"]
                current_version = mod_info["game_versions"][0]
                source = "modrinth"

                more_mod_info = modrinth_api_call('/project/' + mod_id)
                mod_name = more_mod_info["title"]
                mod_slug = more_mod_info["slug"]

                # Check if mod is already documented
                if check_mod_exists(mod_id):
                    message(mod_name + " is already installed")
                else:

                    # Add mod info to json
                    new_mod = {
                        "mod_name": mod_name,
                        "mod_slug": mod_slug,
                        "mod_id": mod_id,
                        "mod_version_id": mod_version_id,
                        "filename": filename,
                        "download_url": download_url,
                        "current_version": current_version,
                        "source": source
                    }

                    with open("mcmodmanager.json", "r") as file:
                        data = json.load(file)
                        mods = data["mods"]

                    mods.append(new_mod)

                    with open("mcmodmanager.json", "w") as file:
                        json.dump(data, file, indent=4)

                    message(mod_name + " has been imported")


def print_server_version():
    with open("mcmodmanager.json", "r") as file:
        data = json.load(file)
        server_version = data["server_version"]
        message(server_version)


def print_usage():
    print('''
    usage: python mcmodmanager.py [-h] [-a [source] [id_or_slug]] [-c [version]] [-i] [-k [api_key]] [-l] [-r [id_or_slug]] [-s [version]] [-u [version]] [--debug]

    A tool to download, update, and manage mods for your Minecraft server using the Modrinth and CursgeForge APIs.

    Flag                    Args                Description
    -------------------------------------------------------------------------------------------------------------------------------------------------
    -a, --add-mod           [Source] [ID|Slug]  Fetch and install the mod with the given ID or slug from the desired source (Modrinth or CurseForge).
    -c, --check-updates     [VERSION]           Check to see if mods have new versions available for specified Minecraft version. 
    -h, --help                                  Prints usage.
    -i, --import-mods                           Scan the mods folder and import any mods that not already monitored. (Only works with Modrinth mods)
    -k, --api-key                               Set the API key that is required for CurseForge.
    -l, --list-mods                             Lists all of the mods that are currently installed.
    -r, --remove-mod        [ID|Slug]           Remove the mod with the specified ID or slug.
    -s, --set-version       [VERSION]           Change the stored value of your Minecraft server version to VERSION.
    -u, --update-mods       [VERSION]           Removes any mods without pending updates to the desired version and updates the rest.
    -v, --print-version                         Prints the current version of the server and mods.
    --debug                                     Display more information to console. Must be passed as the last argument in your command.
    ''')


def main():
    check_new_version()

    init_json_file()

    # Create the argument parser
    parser = argparse.ArgumentParser(
        prog="python mcmodmanager.py",
        description="A tool to download, update, and manage mods for your Minecraft server using the Modrinth and CursgeForge APIs.",
        add_help=False)

    # Add command line arguments and their respective handlers
    parser.add_argument("-a", "--add-mod", nargs=2,
                        metavar=("[source]", "[id_or_slug]"))
    parser.add_argument("-c", "--check-updates", metavar="[version]")
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-i", "--import-mods", action="store_true")
    parser.add_argument("-k", "--api-key", metavar="[api_key]")
    parser.add_argument("-l", "--list-mods", action="store_true")
    parser.add_argument("-r", "--remove-mod", metavar="[id_or_slug]")
    parser.add_argument("-s", "--set-version", metavar="[version]")
    parser.add_argument("-u", "--update-mods", metavar="[version]")
    parser.add_argument("-v", "--print-version",  action="store_true")
    parser.add_argument("--debug", action="store_true")

    # Parse the arguments from the command line
    args = parser.parse_args()

    # Check if --debug mode is enabled
    global debug_mode
    debug_mode = args.debug

    # Check which command was invoked and execute the corresponding function
    if args.add_mod:
        # Init API key only if needed
        if args.add_mod[0] == 'curseforge':
            init_api_key()
        init_server_version()
        add_mod(args.add_mod[0], args.add_mod[1])
    elif args.check_updates:
        init_api_key()
        init_server_version()
        check_updates(args.check_updates)
    elif args.help:
        print_usage()
    elif args.import_mods:
        import_mods()
    elif args.api_key:
        set_curseforge_api_key(args.api_key)
    elif args.list_mods:
        list_mods()
    elif args.remove_mod:
        remove_mod(args.remove_mod)
    elif args.set_version:
        set_server_version(args.set_version)
    elif args.update_mods:
        init_server_version()
        update_mods(args.update_mods)
    elif args.print_version:
        print_server_version()
    else:
        # If no argument was provided or unrecognized argument, print usage
        print_usage()


if __name__ == "__main__":
    main()
