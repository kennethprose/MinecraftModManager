# Minecraft Mod Manager

Minecraft Mod Manager is a Python script that allows you to keep track of all the mods installed on your Minecraft server. It leverages the Modrinth website to add, remove, and update mods seamlessly.

## Features

-   Add mods to your Minecraft server by ID or slug.
-   Remove mods from your Minecraft server by ID or slug.
-   Check if all your mods are compatible with a specified Minecraft version.
-   Update all mods with available updates with one command.

## Installation

1. Ensure you have Python installed on your system.
2. Clone or download the mcmodmanager.py file to the parent directory of your Minecraft server's mods folder.

## Usage

The script provides several command-line options for managing your Minecraft mods. Here are the available options:

| Option                   | Required Value | Description                                                                           |
| ------------------------ | -------------- | ------------------------------------------------------------------------------------- |
| `-a`, `--add-mod`        | Mod ID or Slug | Install the mod with the specified ID or slug.                                        |
| `-r`, `--remove-mod`     | Mod ID or Slug | Remove the mod with the specified ID or slug.                                         |
| `-c`, `--check-updates`  | VERSION        | Check to see which mods have new versions available for specified Minecraft version.  |
| `-u`, `--update-mods`    | VERSION        | Updates mods to desired version.                                                      |
| `-s`, `--server-version` | VERSION        | Change the stored value of your Minecraft server version. (Used when adding new mods) |
| `-h`, `--help`           |                | Prints usage.                                                                         |

## Exmaples

-   Adding the Fabric API mod using the mod 'slug':

```
python mcmodmanager.py -a fabric-api
```

-   Removing the Lithium mod using it's mod ID:

```
python mcmodmanager.py --remove-mod gvQqBUqZ
```

-   Checking if your mods can be updated to version 1.19.4

```
python mcmodmanager.py -c 1.19.4
```

-   Updating your mods to version 1.19.4

```
python mcmodmanager.py --update-mods 1.19.4
```

-   Setting the server version to 1.20

```
python mcmodmanager.py -s 1.20
```

## FAQ

### What is a 'slug'

\- In addition to an ID, each mod on Modrinth comes with a more human readable identifier called a slug. For example, the mod ID for Fabric API is P7dR8mSH, which can be hard to remember and not very informative. However, the Fabric API's slug is just fabric-api which is easy to remember and can tell you exactly what the mod is at a glance.

### Where can I find a mod's ID or slug

\- From the [Modrinth website](https://modrinth.com/mods). The slug can be found at the end of the url on a specific mod's page. Fabric API for example: https[]()://modrinth.com/mod/**fabric-api**. The mod's ID can be found at the bottom of the page where it says "Project ID."