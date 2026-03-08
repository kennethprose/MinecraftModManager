import argparse
import hashlib
import json
import os
import requests
import sys


version = 'v260308'


def check_new_version():
    response = requests.get(
        "https://api.github.com/repos/kennethprose/MinecraftModManager/releases/latest")
    latest_version = response.json()["tag_name"]
    if latest_version > version:
        print(
            f"[ALERT] A new verison of MCModManager is available. Download {latest_version} here: https://github.com/kennethprose/MinecraftModManager/releases/tag/{latest_version}")


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
        print("Downloading " + filename)
    if not os.path.exists("mods"):
        os.makedirs("mods")
    filepath = os.path.join("mods", filename)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    if debug_mode:
        print("Downloaded " + filename)


def init_json_file():
    if os.path.exists("mcmm.json"):
        return
    else:
        print("[ERROR] Could not find mcmm.json")
        with open("mcmm.json", "w") as file:
            data = {"mods": []}
            json.dump(data, file, indent=4)
        print("mcmm.json has been created.")
        exit()


def init_server_version():
    with open("mcmm.json", "r") as file:
        data = json.load(file)

    if "server_version" not in data:
        print("[ERROR]: Server version not set. Please check documentation.")
        exit()


def check_for_curseforge_mods():
    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    for mod in mods:
        if mod["source"] == 'curseforge':
            return True

    return False


def init_api_key(caller):
    with open("mcmm.json", "r") as file:
        data = json.load(file)

    if "curseforge_api_key" in data:
        global curseforge_api_key
        curseforge_api_key = data["curseforge_api_key"]
    elif caller == 'check' and not check_for_curseforge_mods():
        return
    else:
        print("[ERROR]: Curseforge API key not set. Please check documentation.")
        sys.exit()


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

    with open("mcmm.json", "r") as file:
        data = json.load(file)

    data["server_version"] = version

    with open("mcmm.json", "w") as file:
        json.dump(data, file, indent=4)


def set_curseforge_api_key(key):
    with open("mcmm.json", "r") as file:
        data = json.load(file)
        data["curseforge_api_key"] = key

    with open("mcmm.json", "w") as file:
        json.dump(data, file, indent=4)


def check_mod_exists(slug_or_id):
    with open("mcmm.json", "r") as file:
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
            print(f"{slug_or_id} is already installed")
            continue

        with open("mcmm.json", "r") as file:
            data = json.load(file)
            server_version = data["server_version"]
            mods = data["mods"]

        if source == 'modrinth':
            mod_info = modrinth_api_call("/project/" + slug_or_id)
            if mod_info == None:
                print(
                    f"[ERROR]: {slug_or_id} not found. Make sure the slug/ID is correct.")
                continue
            mod_name = mod_info["title"]
            mod_id = mod_info["id"]
            mod_slug = mod_info["slug"]
        elif source == 'curseforge':
            mod_info = curseforge_api_call("/v1/mods/" + slug_or_id)
            if mod_info == None:
                print(
                    f"[ERROR]: {slug_or_id} not found. Make sure the ID is correct.")
                continue
            mod_name = mod_info["data"]["name"]
            mod_id = str(mod_info["data"]["id"])
            mod_slug = mod_info["data"]["slug"]
        else:
            print("[ERROR] \'" + source + "\' is not a valid source")
            continue

        if debug_mode:
            print("Adding mod: " + mod_name)

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

        with open("mcmm.json", "w") as file:
            json.dump(data, file, indent=4)

        print(mod_name + " installed")


def remove_mod_wrapper(mods_to_remove):
    if mods_to_remove == 'ALL':
        remove_all_mods()
        return

    mod_list = mods_to_remove.split(",")
    for slug_or_id in mod_list:
        remove_mod(slug_or_id)


def remove_mod(slug_or_id):

    if debug_mode:
        print(f"Removing {slug_or_id}")

    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    for i, mod in enumerate(mods):

        if mod["mod_id"] == slug_or_id or mod["mod_slug"] == slug_or_id:

            mod_name = mod["mod_name"]

            os.remove(os.path.join("mods", mod["filename"]))

            mods.pop(i)

            with open("mcmm.json", "w") as file:
                json.dump(data, file, indent=4)

            print(f"Successfully removed {mod_name}")
            return

    print(f"{slug_or_id} not found")


def remove_all_mods():
    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    for mod in mods:
        remove_mod(mod["mod_slug"])


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
        if len(mod_versions["data"]) > 0:
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

    print("Checking for updates for Minecraft " + version + "...")

    with open("mcmm.json", "r") as file:
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

    with open("mcmm.json", "w") as file:
        json.dump(data, file, indent=4)

    print("\nUpdates available for:")
    for mod in mods_with_updates:
        print(mod)

    print("\nNo updates for:")
    for mod in mods_without_updates:
        print(mod)


def check_pending_updates(version):

    pending_updates = 0

    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    for mod in mods:
        if "update" in mod:
            if mod["update"]["new_version"] == version:
                pending_updates += 1

    return pending_updates


def remove_mods_without_updates():

    with open("mcmm.json", "r") as file:
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
        print("\nThere are no pending updates. You must check for updates for the desired version first.\n")
        sys.exit()

    with open("mcmm.json", "r") as file:
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

    with open("mcmm.json", "w") as file:
        json.dump(data, file, indent=4)

    set_server_version(version)


def list_mods():

    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    print("\nInstalled Mods:")

    for mod in mods:
        print(mod["mod_name"])


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
                print('Could not identify the mod at ' + file_path)
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
                    print(mod_name + " is already installed")
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

                    with open("mcmm.json", "r") as file:
                        data = json.load(file)
                        mods = data["mods"]

                    mods.append(new_mod)

                    with open("mcmm.json", "w") as file:
                        json.dump(data, file, indent=4)

                    print(mod_name + " has been imported")


def print_server_version():
    with open("mcmm.json", "r") as file:
        data = json.load(file)
        server_version = data["server_version"]
        print(server_version)


def interactive_mode():

    init_json_file()

    while True:

        check_new_version()

        print('''\nWhat would you like to do?
    1.  Add mod
    2.  Remove mod
    3.  Check for updates
    4.  Run updates
    5.  List mods
    6.  Import mods
    7.  Print server version
    8.  Set server verion
    9.  Set Curseforge API key
    10. Quit
        ''')

        option = input("Enter the number of the option: ")

        match option:
            case '1':
                source = input(
                    "Enter the source of the mod [modrinth/curseforge]: ")
                id = input("Enter the id/slug of the mod: ")

                if source == 'curseforge':
                    init_api_key("add")
                init_server_version()

                add_mod(source, id)

            case '2':
                id = input("Enter the id/slug of the mod or 'ALL': ")

                remove_mod_wrapper(id)

            case '3':
                version = input(
                    "Enter the version of Minecraft you want to check: ")

                init_api_key("check")
                init_server_version()

                check_updates(version)

            case '4':
                version = input(
                    "Enter the version of Minecraft you want to update: ")

                init_server_version()

                update_mods(version)

            case '5':
                list_mods()

            case '6':
                import_mods()

            case '7':
                print_server_version()

            case '8':
                version = input("Enter the version of Minecraft: ")

                set_server_version(version)

            case '9':
                key = input("Enter your Curseforge API key: ")

                set_curseforge_api_key(key)

            case '10':
                exit()


def main():
    check_new_version()

    init_json_file()

    # Create the argument parser
    parser = argparse.ArgumentParser(
        prog="python mcmm.py",
        description="A tool to download, update, and manage mods for your Minecraft server using the Modrinth and CurseForge APIs.")

    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    subparsers = parser.add_subparsers(dest="command")

    p = subparsers.add_parser("add", help="Add mod")
    p.add_argument("source", choices=["modrinth", "curseforge"], help="Repository to add mod from")
    p.add_argument("id_or_slug", help="Mod id or slug (comma-separated supported)")

    p = subparsers.add_parser("check", help="Check for updates")
    p.add_argument("version", nargs="?", help="Minecraft version to check (defaults to server version)")

    p = subparsers.add_parser("update", help="Update mods")
    p.add_argument("version", help="Desired Minecraft version")

    p = subparsers.add_parser("remove", help="Remove mod(s)")
    p.add_argument("id_or_slug", help="IDs/slugs (comma-separated supported), or ALL to remove all mods")

    subparsers.add_parser("import", help="Import mods from ./mods")
    subparsers.add_parser("list", help="List installed mods")

    p = subparsers.add_parser("set-version", help="Set server Minecraft version")
    p.add_argument("version", help="Version to set")

    p = subparsers.add_parser("set-api-key", help="Set CurseForge API key")
    p.add_argument("key", help="API key")

    subparsers.add_parser("version", help="Print server version")

    args = parser.parse_args()

    # Dispatch commands
    def run_command(args):
        global debug_mode
        debug_mode = args.debug

        if args.command == "add":
            if args.source == 'curseforge':
                init_api_key("add")
            init_server_version()
            add_mod(args.source, args.id_or_slug)

        elif args.command == "check":
            init_api_key("check")
            init_server_version()
            if args.version:
                check_updates(args.version)
            else:
                # use stored server version
                with open("mcmm.json", "r") as f:
                    data = json.load(f)
                check_updates(data.get("server_version"))

        elif args.command == "update":
            init_server_version()
            update_mods(args.version)

        elif args.command == "remove":
            remove_mod_wrapper(args.id_or_slug)

        elif args.command == "import":
            import_mods()

        elif args.command == "list":
            list_mods()

        elif args.command == "set-version":
            set_server_version(args.version)

        elif args.command == "set-api-key":
            set_curseforge_api_key(args.key)

        elif args.command == "version":
            print_server_version()

        else:
            # No command given -> interactive mode
            interactive_mode()

    run_command(args)


if __name__ == "__main__":
    main()
