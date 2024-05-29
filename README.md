# Wadzilla

Wadzilla is a tool designed to facilitate the conversion of Doom WAD files into ZIL files, suitable for creating interactive fiction in the style of Infocom games.

## Overview

Wadzilla extracts information from Doom WAD files, including texture descriptions and thing types, and utilizes it to generate ZIL code that describes the rooms and objects within the game environment.

## Usage

To use Wadzilla, execute the following command:

```bash
python wadzilla.py -basewad /path/to/doom1.wad 
```

Mods (PWADs) can also be specified. the argument syntax for specifying IWAD and PWAD are based on the Doom game's command-line options in homage; apologies for their sorta non-intuitive (to me) option names. See the output from --help for more usage info. 
