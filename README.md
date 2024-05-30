# Wadzilla

Wadzilla is a tool designed to facilitate the conversion of Doom WAD files into ZIL files, suitable for creating interactive fiction in the style of Infocom games. 

Quite possibly it was actually designed to facilitate the long-standing "Doom on Everything" initiative.  I am aware that it is a ludicrous tool. 

A wiki page explaining the motivation and some history of Zork and Doom is here: https://github.com/scottvr/wadzilla/wiki

## Overview

Wadzilla extracts information from Doom WAD files, including map geometry, texture descriptions and thing types, and utilizes it to generate text that describes the rooms and objects in ZIL code format, so that the map can be explored within the Zork runtime environment.

## Usage

To use Wadzilla, execute the following command:

```bash
python wadzilla.py -basewad /path/to/doom1.wad 
```

Mods (PWADs) can also be specified. the argument syntax for specifying IWAD and PWAD is based on the Doom game's command-line options in homage; apologies for their sorta non-intuitive (to me) option names but... y'know, tribute. 

See the output from --help for more usage info. 

Note that Wadzilla is still in embryonic stage amd under active development. Of its committed to main, then it should be functional, just note that it may change minute to minute for as long as I still have interest in working on it.  after larger milestone changes, I am tagging releases though so you can always use of those commits for stable reproducable resukts across different machines and whatnot.  

## Dependencies

- Python 3.x
- Requests
- BeautifulSoup
- an IWAD file, such as doom1.wad from id Software. the Doom shareware WAD is freely distributable per John Carmack, and it is also readily available all over the Internet, so I won't waste bits by including it here. archive.org will have it, as well as many other places. 

## Optionally
- a patch level (mod/PWAD file)
- If you actually want to PLAY your Doom IF, you will need to compile it and run it on a z-machine.

A video explaining this can be found here: https://m.youtube.com/watch?v=JpaBCb6qCCo

A website linking to many tools that can be used in the process is here: https://eblong.com/infocom/

if you are after the ultimate goal of *playing Doom inside of Zork* you will need the decompiled Zork ZIL to which you can use Wadzilla to add a portal into E1M1 in a specified Zork room. See the usage info for how. Then of course, the aforementioned compilation and execution on a z-machine is needed.

## Aditionally
Descriptions for Things found in the wad will either be just the item number (not very descriptive) or the string from the file data/thing_types.json, which contains a dict mapping the item id (decimal) to a string. By default if the file does not exist, the script will attempt to create a dict populated with data it finds in the Doom Wiki (https://doomwiki.org/wiki/Thing_types_by_number) table.

You can edit this file for your needs, or even create it manually. (Oh yeah, because Wadzilla should work with Doom 2, Hexen, etc WADs equally.)  Also, if you want to have the script scrape a table you know exists in the aforementioned Doom Wiki doc (as in the example below, for the Strife game), you can alter the function to search for the table header like so:

``` python
# Using the wikitable on that page for the Things in the Doom-engine game "Strife"
def scrape_thing_types(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    thing_dict = {}
    tables = soup.find_all('table', class_='wikitable')

    for table in tables:
        # Check if the table header matches the one for "Strife"
        header = table.find_previous('h2')
        if header and 'Strife' in header.get_text():
            for row in table.find_all('tr')[1:]:  # Skip the header row
                cols = row.find_all('td')
                if len(cols) >= 9:  # Ensure there are enough columns
                    type_id = cols[0].get_text(strip=True)
                    description = cols[8].get_text(strip=True)
                    if type_id.isdigit():
                        thing_dict[int(type_id)] = description

    return thing_dict
```

Just as I finished writing this section I realized I should probably just add a variable to contain the section header name (string to match) and perhaps even allow it passed as a command-line option argument. TBD.

## LICENSES
wadzilla is um, MIT licensed I guess. I'll put something proper here before anyone learns of Wadzilla's existence. 
