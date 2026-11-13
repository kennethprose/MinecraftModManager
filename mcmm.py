import argparse
import hashlib
import json
import os
from urllib.parse import quote
import requests
import sys
import tempfile


version = 'v260814'


def get_release_asset_digest(release_tag):
    try:
        response = requests.get(
            f"https://api.github.com/repos/kennethprose/MinecraftModManager/releases/tags/{release_tag}",
            timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR]: Failed to fetch release info: {e}")
        return None

    release_info = response.json()

    for asset in release_info.get("assets", []):
        if asset["name"] == 'mcmm.py':
            digest = asset.get("digest")
            if digest and digest.startswith("sha256:"):
                return digest.split(":", 1)[1].lower()

    return None


def self_update(latest_version):
    download_url = f"https://github.com/kennethprose/MinecraftModManager/releases/download/{latest_version}/mcmm.py"

    current_script_path = os.path.abspath(__file__)
    temp_path = current_script_path + ".tmp"

    expected_hash = get_release_asset_digest(latest_version)
    if not expected_hash:
        print("[ERROR]: Could not retrieve checksum for mcmm.py from the release. Update aborted.")
        return False

    try:
        with requests.get(download_url, stream=True, timeout=15) as r:
            r.raise_for_status()
            with open(temp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.exceptions.RequestException as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"[ERROR]: Failed to download update: {e}")
        return False

    actual_hash = generate_file_hash(temp_path, 'sha256')
    if actual_hash != expected_hash:
        os.remove(temp_path)
        print(
            f"[ERROR]: Checksum mismatch — downloaded file does not match expected hash. "
            f"Update aborted for safety (expected {expected_hash[:12]}..., got {actual_hash[:12]}...)")
        return False

    try:
        original_mode = os.stat(current_script_path).st_mode
    except OSError:
        original_mode = None

    os.replace(temp_path, current_script_path)

    if original_mode is not None:
        try:
            os.chmod(current_script_path, original_mode)
        except OSError:
            pass

    print(f"Updated to {latest_version}. Please re-run your command.")
    return True


def check_new_version():
    try:
        response = requests.get(
            "https://api.github.com/repos/kennethprose/MinecraftModManager/releases/latest",
            timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        # Can't reach GitHub, fail quietly
        return
    
    latest_version = response.json().get("tag_name")
    if latest_version and latest_version > version:
        print(f"[ALERT] A new version of MCModManager is available: {latest_version} (you have {version})")

        if sys.stdin.isatty():
            choice = input("Would you like to update now? (yes/no): ")
            if choice.lower() == "yes":
                if self_update(latest_version):
                    sys.exit()
        else:
            print(f"Download manually: https://github.com/kennethprose/MinecraftModManager/releases/tag/{latest_version}")

class ApiError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def request_json(provider, url, *, params=None, headers=None):
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        status_code = getattr(e.response, "status_code", None)
        raise ApiError(f"{provider} request failed: {e}", status_code) from e

    try:
        data = response.json()
    except ValueError as e:
        raise ApiError(f"{provider} returned invalid JSON") from e

    if not isinstance(data, (dict, list)):
        raise ApiError(f"{provider} returned an unexpected response structure")
    return data


def modrinth_api_call(endpoint, params=None):
    return request_json("Modrinth", "https://api.modrinth.com/v2" + endpoint, params=params)


def curseforge_api_call(endpoint, params=None):
    return request_json("CurseForge", "https://api.curseforge.com" + endpoint,
                        params=params, headers={"x-api-key": curseforge_api_key})


def generate_file_hash(file_path, algorithm='sha512'):
    hash_obj = hashlib.new(algorithm)
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def download_mod(url, filename, expected_hash=None, hash_algorithm='sha512'):
    if debug_mode:
        print("Downloading " + filename)
    if not os.path.exists("mods"):
        os.makedirs("mods")
    filepath = os.path.join("mods", filename)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=os.path.dirname(filepath),
                                         prefix=".mcmm-", suffix=".tmp", delete=False) as f:
            temp_path = f.name
            with requests.get(url, stream=True, timeout=15) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        if expected_hash:
            actual_hash = generate_file_hash(temp_path, hash_algorithm)
            if actual_hash.lower() != expected_hash.lower():
                raise Exception(
                    f"Hash mismatch for {filename} — file may be corrupted or tampered with "
                    f"(expected {expected_hash[:12]}..., got {actual_hash[:12]}...)")

        os.replace(temp_path, filepath)
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to download {filename}: {e}")
    finally:
        if temp_path is not None and os.path.exists(temp_path):
            os.remove(temp_path)
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
        sys.exit()


def init_server_version():
    with open("mcmm.json", "r") as file:
        data = json.load(file)

    if "server_version" not in data:
        print("[ERROR]: Server version not set. Please check documentation.")
        sys.exit()


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
    elif (caller == 'check' or caller == 'update') and not check_for_curseforge_mods():
        return
    else:
        print("[ERROR]: Curseforge API key not set. Please check documentation.")
        sys.exit()


def check_version_exists(version):

    valid_versions = modrinth_api_call("/tag/game_version")

    if not isinstance(valid_versions, list) or any(
            not isinstance(v, dict) or not isinstance(v.get("version"), str)
            for v in valid_versions):
        raise ApiError("Modrinth returned an invalid Minecraft version list")

    for v in valid_versions:
        if v["version"] == version:
            return True

    return False


def set_server_version(version):

    if not check_version_exists(version):
        print(f"[ERROR]: {version} is not a valid Minecraft version")
        sys.exit(1)

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
            try:
                mod_info = modrinth_api_call("/project/" + quote(slug_or_id, safe=""))
            except ApiError as e:
                if e.status_code != 404:
                    raise
                print(
                    f"[ERROR]: {slug_or_id} not found. Make sure the slug/ID is correct.")
                continue
            mod_name = mod_info["title"]
            mod_id = mod_info["id"]
            mod_slug = mod_info["slug"]
        elif source == 'curseforge':
            try:
                mod_info = curseforge_api_call("/v1/mods/" + quote(slug_or_id, safe=""))
            except ApiError as e:
                if e.status_code != 404:
                    raise
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
                f"/project/{quote(slug_or_id, safe='')}/version",
                params={"game_versions": f'["{server_version}"]', "loaders": '["fabric"]'}
            )

            if not isinstance(mod_versions, list):
                raise ApiError("Modrinth returned an invalid mod version list")
            if not mod_versions:
                print(f"[ERROR]: No Fabric release of {mod_name} found for Minecraft {server_version}. Skipping.")
                continue

            most_recent_version = mod_versions[0]
            mod_version_id = most_recent_version["id"]
            filename = most_recent_version["files"][0]["filename"]
            download_url = most_recent_version["files"][0]["url"]
            file_hashes = most_recent_version["files"][0].get("hashes", {})
            expected_hash = file_hashes.get("sha512")
            hash_algorithm = 'sha512'
            if not expected_hash:
                expected_hash = file_hashes.get("sha1")
                hash_algorithm = 'sha1'

        elif source == 'curseforge':
            mod_versions = curseforge_api_call(
                f"/v1/mods/{quote(slug_or_id, safe='')}/files",
                params={"gameVersion": server_version, "modLoaderType": 4}
            )

            if not isinstance(mod_versions, dict) or not isinstance(mod_versions.get("data"), list):
                raise ApiError("CurseForge returned an invalid mod version list")
            if not mod_versions["data"]:
                print(f"[ERROR]: No Fabric release of {mod_name} found for Minecraft {server_version}. Skipping.")
                continue

            most_recent_version = mod_versions["data"][0]
            mod_version_id = str(most_recent_version["id"])
            filename = most_recent_version["fileName"]
            download_url = most_recent_version["downloadUrl"]
            file_hashes = most_recent_version.get("hashes", [])
            expected_hash = file_hashes[0]["value"] if file_hashes else None
            hash_algorithm_id = file_hashes[0]["algo"] if file_hashes else None
            hash_algorithm = 'sha1' if hash_algorithm_id == 1 else 'md5' if hash_algorithm_id == 2 else None

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

        try:
            download_mod(download_url, filename, expected_hash=expected_hash, hash_algorithm=hash_algorithm)
        except Exception as e:
            print(f"[ERROR]: Failed to add {mod_name}: {e}")
            continue

        mods.append(new_mod)
        data.pop("last_check", None)

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

            filepath = os.path.join("mods", mod["filename"])
            if os.path.exists(filepath):
                os.remove(filepath)
            else:
                print(f"[WARNING]: {filepath} was already missing from disk. Removing entry from modlist.")

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
        f"/project/{quote(mod_slug, safe='')}/version",
        params={"game_versions": f'["{version}"]', "loaders": '["fabric"]'}
    )

    if not isinstance(mod_versions, list):
        raise ApiError("Modrinth returned an invalid mod version list")
    if not mod_versions:
        return None

    try:
        newest_mod_version = mod_versions[0]
        new_version_id = newest_mod_version["id"]
        file_info = newest_mod_version["files"][0]
        filename = file_info["filename"]
        download_url = file_info["url"]
    except (KeyError, IndexError, TypeError) as e:
        raise ApiError("Modrinth returned invalid mod file information") from e
    if not all(isinstance(value, str) and value for value in (new_version_id, filename, download_url)):
        raise ApiError("Modrinth returned invalid mod file information")

    if mod_version_id and new_version_id == mod_version_id:
        return None
    return {
        "new_version_id": new_version_id,
        "new_filename": filename,
        "new_download_url": download_url,
        "new_version": version
    }


def get_curseforge_mod_info(mod_id, version, mod_version_id=None):

    mod_versions = curseforge_api_call(
        f"/v1/mods/{quote(str(mod_id), safe='')}/files",
        params={"gameVersion": version, "modLoaderType": 4}
    )

    if not isinstance(mod_versions, dict) or not isinstance(mod_versions.get("data"), list):
        raise ApiError("CurseForge returned an invalid mod version list")
    if not mod_versions["data"]:
        return None

    try:
        newest_mod_version = mod_versions["data"][0]
        new_version_id = newest_mod_version["id"]
        filename = newest_mod_version["fileName"]
        download_url = newest_mod_version["downloadUrl"]
    except (KeyError, TypeError) as e:
        raise ApiError("CurseForge returned invalid mod file information") from e
    if (not isinstance(new_version_id, (int, str)) or isinstance(new_version_id, bool)
            or not new_version_id
            or not all(isinstance(value, str) and value for value in (filename, download_url))):
        raise ApiError("CurseForge returned invalid mod file information or no download URL")

    new_version_id = str(new_version_id)
    if mod_version_id and new_version_id == mod_version_id:
        return None
    return {
        "new_version_id": new_version_id,
        "new_filename": filename,
        "new_download_url": download_url,
        "new_version": version
    }


def check_updates(version):
    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    # Persist this before any requests so failed or interrupted checks block updates.
    data["last_check"] = {"version": version, "status": "incomplete"}
    with open("mcmm.json", "w") as file:
        json.dump(data, file, indent=4)

    try:
        version_status = check_version_exists(version)
    except ApiError as e:
        print(f"[ERROR]: Could not verify Minecraft version {version}: {e}")
        print("Compatibility check incomplete. Previous pending updates were preserved.")
        sys.exit(1)
    if not version_status:
        print(f"[ERROR]: {version} is not a valid Minecraft version")
        sys.exit(1)

    print("Checking for updates for Minecraft " + version + "...")
    mods_with_updates = []
    mods_without_updates = []
    failed_checks = []

    for mod in mods:
        # A partially migrated mod may already be at the target server version.
        installed_id = mod["mod_version_id"] if mod["current_version"] == version else None
        try:
            if mod["source"] == 'modrinth':
                update_info = get_modrinth_mod_info(mod["mod_slug"], version, installed_id)
            elif mod["source"] == 'curseforge':
                update_info = get_curseforge_mod_info(mod["mod_id"], version, installed_id)
            else:
                raise ApiError(f"Unknown mod source: {mod['source']}")
        except ApiError as e:
            failed_checks.append((mod["mod_name"], str(e)))
            continue

        if update_info:
            mod["update"] = update_info
            mods_with_updates.append(mod["mod_name"])
        else:
            mod.pop("update", None)
            mods_without_updates.append(mod["mod_name"])

    if failed_checks:
        print("\nCould not check:")
        for mod_name, reason in failed_checks:
            print(f"  {mod_name}: {reason}")
        print("[ERROR]: Compatibility check incomplete. Previous pending updates were preserved.")
        sys.exit(1)

    data["last_check"]["status"] = "complete"
    with open("mcmm.json", "w") as file:
        json.dump(data, file, indent=4)

    print("\nUpdates available for:")
    for mod in mods_with_updates:
        print(mod)

    print("\nNo updates for:")
    for mod in mods_without_updates:
        print(mod)


def has_pending_update(mod, version):
    return mod.get("update", {}).get("new_version") == version


def check_pending_updates(version):

    pending_updates = 0

    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    for mod in mods:
        if has_pending_update(mod, version):
            pending_updates += 1

    return pending_updates


def remove_mods_without_updates(version):

    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    mods_without_updates = []
    for mod in mods:
        if mod["current_version"] != version and not has_pending_update(mod, version):
            mods_without_updates.append(mod["mod_slug"])

    for mod_slug in mods_without_updates:
        remove_mod(mod_slug)


def update_mods(version):
    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]
        server_version = data["server_version"]

        last_check = data.get("last_check", {})
        if (last_check.get("version") != version
                or last_check.get("status") != "complete"):
            print(f"[ERROR]: Run 'check {version}' successfully before updating. The last check is missing, incomplete, or for another version.")
            sys.exit(1)

        if not check_version_exists(version):
            print(f"[ERROR]: {version} is not a valid Minecraft version")
            sys.exit(1)

        pending_updates = check_pending_updates(version)

        # Allow a retry to finish recording a migration after every mod was saved.
        if pending_updates == 0 and (not mods or any(mod["current_version"] != version for mod in mods)):
            print("\nThere are no pending updates. You must check for updates for the desired version first.\n")
            sys.exit(1)

        # Keep mods that already reached the target version during an earlier attempt.
        if server_version != version and any(
                mod["current_version"] != version and not has_pending_update(mod, version)
                for mod in mods):

            confirmation = input(
                f"\nMods not installed for Minecraft {version} and without pending updates for it will be removed. Do you want to proceed? (yes/no): ")

            if confirmation.lower() != "yes":
                sys.exit()

            remove_mods_without_updates(version)

            # Reload state so later saves do not restore removed mods.
            with open("mcmm.json", "r") as updated_file:
                data = json.load(updated_file)
            mods = data["mods"]

        for mod in mods:
            if has_pending_update(mod, version):

                new_filename = mod["update"]["new_filename"]
                old_filepath = os.path.join("mods", mod["filename"])
                new_filepath = os.path.join("mods", new_filename)

                try:
                    # Fetch expected hash of new mod version file.
                    if mod["source"] == 'modrinth':
                        new_version = modrinth_api_call(f"/version/{mod['update']['new_version_id']}")
                        if not new_version or not new_version.get("files"):
                            raise ValueError("Could not retrieve Modrinth file information")
                        new_version_hashes = new_version["files"][0].get("hashes", {})
                        expected_hash = new_version_hashes.get("sha512")
                        hash_algorithm = 'sha512'
                        if not expected_hash:
                            expected_hash = new_version_hashes.get("sha1")
                            hash_algorithm = 'sha1'
                    elif mod["source"] == 'curseforge':
                        new_version = curseforge_api_call(f"/v1/mods/{mod['mod_id']}/files/{mod['update']['new_version_id']}")
                        if not new_version or not new_version.get("data"):
                            raise ValueError("Could not retrieve CurseForge file information")
                        new_version_hashes = new_version["data"].get("hashes", [])
                        expected_hash = new_version_hashes[0]["value"] if new_version_hashes else None
                        hash_algorithm_id = new_version_hashes[0]["algo"] if new_version_hashes else None
                        hash_algorithm = 'sha1' if hash_algorithm_id == 1 else 'md5' if hash_algorithm_id == 2 else None
                    else:
                        raise ValueError(f"Unknown mod source: {mod['source']}")

                    # Download new file.
                    download_mod(mod["update"]["new_download_url"], new_filename, expected_hash=expected_hash, hash_algorithm=hash_algorithm)
                except Exception as e:
                    print(f"[ERROR]: Failed to update {mod['mod_name']}: {e}")
                    continue

                # Remove old file
                if old_filepath != new_filepath and os.path.exists(old_filepath):
                    os.remove(old_filepath)

                # Copy 'update' data to primary data variables
                mod["mod_version_id"] = mod["update"]["new_version_id"]
                mod["filename"] = mod["update"]["new_filename"]
                mod["download_url"] = mod["update"]["new_download_url"]
                mod["current_version"] = mod["update"]["new_version"]

                # Remove pending update data
                del mod["update"]

                with open("mcmm.json", "w") as file:
                    json.dump(data, file, indent=4)

                print(mod["mod_name"] + " has been updated")

    incomplete_mods = [
        mod["mod_name"] for mod in mods
        if mod["current_version"] != version or has_pending_update(mod, version)
    ]
    if incomplete_mods:
        print(f"[ERROR]: Update to Minecraft {version} is incomplete for: {', '.join(incomplete_mods)}.")
        print(f"Stored server version remains {server_version}. Successful updates have been saved.")
        print(f"Run 'update {version}' again to retry the remaining updates.")
        sys.exit(1)

    # The target was validated above; record it only after all retained mods succeeded.
    data["server_version"] = version
    with open("mcmm.json", "w") as file:
        json.dump(data, file, indent=4)


def list_mods():

    with open("mcmm.json", "r") as file:
        data = json.load(file)
        mods = data["mods"]

    if not mods:
        print("No mods are currently installed.")
        return

    rows = []
    for mod in mods:
        name = mod["mod_name"]
        source = mod["source"].capitalize()
        identifier = mod.get("mod_slug") or mod["mod_id"]
        current_version = mod["current_version"]

        if "update" in mod:
            status = f"Update available -> {mod['update']['new_version']}"
        else:
            status = "Up to date"

        rows.append((name, source, identifier, current_version, status))

    headers = ("Mod Name", "Source", "Slug/ID", "MC Version", "Status")

    # Column widths based on content
    col_widths = [
        max(len(headers[i]), max((len(row[i]) for row in rows), default=0))
        for i in range(len(headers))
    ]

    def format_row(row):
        return "  ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row))

    pending_count = sum(1 for mod in mods if "update" in mod)

    print(f"Installed Mods ({len(mods)} total, {pending_count} update(s) available):\n")
    print(format_row(headers))
    print("  ".join("-" * w for w in col_widths))
    for row in rows:
        print(format_row(row))


def import_mods():
    # Iterate over all mods in the mods folder
    for filename in os.listdir('./mods/'):
        file_path = os.path.join('./mods/', filename)
        if os.path.isfile(file_path) and file_path.endswith('.jar'):

            # Get the hash of the function and use it to check the modrinth api
            sha1_hash = generate_file_hash(file_path, 'sha1')
            try:
                mod_info = modrinth_api_call('/version_file/' + sha1_hash)
            except ApiError as e:
                if e.status_code != 404:
                    raise
                mod_info = None

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
                    data.pop("last_check", None)

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

                init_api_key("update")
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
                sys.exit()


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
            init_api_key("update")
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

    try:
        run_command(args)
    except ApiError as e:
        print(f"[ERROR]: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
