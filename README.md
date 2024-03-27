# Minecraft Mod Manager

Minecraft Mod Manager is a Python script that allows you to keep track of all the mods installed on your Minecraft server. It leverages the Modrinth and CurseForge websites to add, remove, and update mods seamlessly.

## Features

- Add mods to your Minecraft server.
- Remove mods from your Minecraft server.
- Check if all your mods are compatible with a new Minecraft version.
- Update all mods with available updates with one command.

## Installation

1. Ensure you have Python installed on your system.
2. Clone or download the mcmm.py file to the parent directory of your Minecraft server's mods folder.

## Usage

### Interactive Mode

Passing no command line arguments to the program will place you into an interactive mode which is better suited for users less comforatble with the command line.

### CLI Mode

The script provides several command-line options for managing your Minecraft mods. Here are the available options:

| Option                  | Required Value(s)         | Description                                                                                                                                                  |
| ----------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `-a`, `--add-mod`       | [Source] [ModIDs/Slugs]\* | Fetch and install the mods with the given IDs or slugs from the desired sources (Modrinth or CurseForge). Mods can also be passed as a comma-delimited list. |
| `-c`, `--check-updates` | [VERSION]                 | Check to see which mods have new versions available for specified Minecraft version.                                                                         |
| `-h`, `--help`          |                           | Prints usage.                                                                                                                                                |
| `-i`, `--import-mods`   |                           | Scan the mods folder and import any mods that not already monitored (Only works with Modrinth mods)                                                          |
| `-k`, `--api-key`       |                           | Set the API key that is required for CurseForge.                                                                                                             |
| `-l`, `--list-mods`     |                           | Lists all of the mods that are currently installed.                                                                                                          |
| `-r`, `--remove-mod`    | [ModIDs/Slugs/ALL]        | Remove the mod with the specified ID or slug. Mods can also be passed as a comma-delimited list. Pass ALL to remove all installed mods at once.              |
| `-s`, `--set-version`   | [VERSION]                 | Change the stored value of your Minecraft server version. (Used when adding new mods)                                                                        |
| `-u`, `--update-mods`   | [VERSION]                 | Updates mods to desired version.                                                                                                                             |
| `-v`, `--print-version` |                           | Prints the current version of the server and mods.                                                                                                           |
| `--debug`               |                           | Display more information to console. Must be passed as the last argument in your command.                                                                    |

\*NOTE: For a mod to be added using CurseForge, you must use the mod ID. The CurseForge API does not support queries using the mod slugs, even though they exist.

## Exmaples

- Adding the Fabric API mod from Modrinth using the mod 'slug':

```
python mcmm.py -a modrinth fabric-api
```

- Adding the Fabric API mod from CurseForge using the mod ID:

```
python mcmm.py -a CurseForge 306612
```

- Adding multiple mods at once:

```
python mcmm.py -a modrinth fabric-api,lithium,modmenu
```

- Removing the Lithium mod using it's mod ID:

```
python mcmm.py --remove-mod gvQqBUqZ
```

- Checking if your mods can be updated to version 1.19.4

```
python mcmm.py -c 1.19.4
```

- Updating your mods to version 1.19.4 in debug mode

```
python mcmm.py --update-mods 1.19.4 --debug
```

## FAQ

### What is a 'slug'

\- In addition to an ID, each mod on Modrinth comes with a more human readable identifier called a slug. For example, the mod ID for Fabric API is P7dR8mSH, which can be hard to remember and not very informative. However, the Fabric API's slug is just 'fabric-api', which is easy to remember and can tell you exactly what the mod is at a glance.

### Where can I find a Modrinth mod's ID or slug

\- From the [Modrinth website](https://modrinth.com/mods). The slug can be found at the end of the url on a specific mod's page. Fabric API for example: https[]()://modrinth.com/mod/**fabric-api**. The mod's ID can be found at the bottom of the page where it says "Project ID."

### Where can I find a CurseForge mod's ID

\- From the [CurseForge website](https://www.curseforge.com/minecraft). The mod's ID can be found on the right sidebar on the mod page. It is under the "About Project" section where it says "Project ID."
