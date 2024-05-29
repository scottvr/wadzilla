import os
import sys
import json
import requests
from bs4 import BeautifulSoup
import struct
import argparse

class WADFile:
    def __init__(self, filename):
        self.filename = filename
        self.lumps = {}
        self.read_wad()

    def read_wad(self):
        with open(self.filename, 'rb') as f:
            header = f.read(12)
            wad_type, num_lumps, dir_offset = struct.unpack('4sII', header)
            f.seek(dir_offset)

            for _ in range(num_lumps):
                lump_data = f.read(16)
                lump_offset, lump_size, lump_name = struct.unpack('II8s', lump_data)
                lump_name = lump_name.strip(b'\x00').decode('ascii')
                self.lumps[lump_name] = (lump_offset, lump_size)

    def read_lump(self, lump_name):
        if lump_name in self.lumps:
            offset, size = self.lumps[lump_name]
            with open(self.filename, 'rb') as f:
                f.seek(offset)
                return f.read(size)
        else:
            raise ValueError(f'Lump {lump_name} not found in WAD.')

def parse_vertexes(data):
    vertexes = []
    for i in range(0, len(data), 4):
        x, y = struct.unpack('hh', data[i:i+4])
        vertexes.append((x, y))
    return vertexes

def parse_linedefs(data):
    linedefs = []
    for i in range(0, len(data), 14):
        v1, v2, flags, types, tag, right_sidedef, left_sidedef = struct.unpack('hhhhhhh', data[i:i+14])
        linedefs.append((v1, v2, flags, types, tag, right_sidedef, left_sidedef))
    return linedefs

def parse_sidedefs(data):
    sidedefs = []
    for i in range(0, len(data), 30):
        x_offset, y_offset, upper_tex, lower_tex, middle_tex, sector_id = struct.unpack('hh8s8s8sh', data[i:i+30])
        sidedefs.append((x_offset, y_offset, upper_tex.strip(b'\x00').decode(), lower_tex.strip(b'\x00').decode(), middle_tex.strip(b'\x00').decode(), sector_id))
    return sidedefs

def parse_sectors(data):
    sectors = []
    for i in range(0, len(data), 26):
        floor_height, ceiling_height, floor_tex, ceiling_tex, light_level, sector_type, tag = struct.unpack('hh8s8shhh', data[i:i+26])
        sectors.append((floor_height, ceiling_height, floor_tex.strip(b'\x00').decode(), ceiling_tex.strip(b'\x00').decode(), light_level, sector_type, tag))
    return sectors

def parse_things(data):
    things = []
    for i in range(0, len(data), 10):
        x, y, angle, type, flags = struct.unpack('hhhhH', data[i:i+10])
        things.append((x, y, type))
    return things

def point_in_polygon(x, y, polygon):
    num = len(polygon)
    j = num - 1
    c = False
    for i in range(num):
        if ((polygon[i][1] > y) != (polygon[j][1] > y)) and \
                (x < polygon[i][0] + (polygon[j][0] - polygon[i][0]) * (y - polygon[i][1]) / (polygon[j][1] - polygon[i][1])):
            c = not c
        j = i
    return c

def scrape_texture_descriptions(url):
# stub until I arrive at a way to describe the textures. The script will just use the texture names for now.
#    response = requests.get(url)
#    soup = BeautifulSoup(response.text, 'html.parser')

    texture_dict = {}
#    for table in soup.find_all('table', class_='wikitable'):
#        for row in table.find_all('tr')[1:]:
#            cols = row.find_all('td')
#            if len(cols) >= 2:
#                texture_name = cols[0].get_text(strip=True)
#                description = cols[1].get_text(strip=True)
#                texture_dict[texture_name] = description

    return texture_dict

def scrape_thing_types(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    thing_dict = {}
    tables = soup.find_all('table', class_='wikitable')

    for table in tables:
        # Check if the table header matches the one for "Doom, Doom II, Final Doom"
        header = table.find_previous('h2')
        if header and 'Doom, Doom II, Final Doom' in header.get_text():
            for row in table.find_all('tr')[1:]:  # Skip the header row
                cols = row.find_all('td')
                if len(cols) >= 9:  
                    type_id = cols[0].get_text(strip=True)
                    description = cols[8].get_text(strip=True)
                    if type_id.isdigit():
                        thing_dict[int(type_id)] = description

    return thing_dict

class Room:
    def __init__(self, sector_id, sector_data):
        self.sector_id = sector_id
        self.floor_height, self.ceiling_height, self.floor_tex, self.ceiling_tex, self.light_level, self.type, self.tag = sector_data
        self.vertexes = set()
        self.linedefs = []
        self.things = []
        self.wall_textures = []  

    def add_vertex(self, vertex):
        self.vertexes.add(vertex)

    def add_linedef(self, linedef, sidedefs):
        self.linedefs.append(linedef)
        v1, v2, flags, types, tag, right_sidedef, left_sidedef = linedef
        
        right_sidedef_data = sidedefs[right_sidedef]
        left_sidedef_data = sidedefs[left_sidedef] if left_sidedef != -1 else None
        
        self.wall_textures.append({
            'right': {
                'upper': right_sidedef_data[2] if right_sidedef_data[2] != '-' else None,
                'lower': right_sidedef_data[3] if right_sidedef_data[3] != '-' else None,
                'middle': right_sidedef_data[4] if right_sidedef_data[4] != '-' else None
            },
            'left': {
                'upper': left_sidedef_data[2] if left_sidedef_data and left_sidedef_data[2] != '-' else None,
                'lower': left_sidedef_data[3] if left_sidedef_data and left_sidedef_data[3] != '-' else None,
                'middle': left_sidedef_data[4] if left_sidedef_data and left_sidedef_data[4] != '-' else None
            }
        })

    def add_thing(self, thing):
        self.things.append(thing)

    def describe_zil(self, texture_descriptions, thing_type_descriptions):
        description = f"<ROOM {self.sector_id} {self.floor_tex}/{self.ceiling_tex}>\n"
        description += f"FLOOR HEIGHT: {self.floor_height}, CEILING HEIGHT: {self.ceiling_height}\n"

        floor_desc = texture_descriptions.get(self.floor_tex, f"Unknown texture {self.floor_tex}")
        ceiling_desc = texture_descriptions.get(self.ceiling_tex, f"Unknown texture {self.ceiling_tex}")
        description += f"Floor: {floor_desc}\nCeiling: {ceiling_desc}\n"

        description += "Walls:\n"
        for wall in self.wall_textures:
            description += " - "
            if wall['right']['upper']:
                description += f"Right: {wall['right']['upper']}"
                if wall['right']['middle'] or wall['right']['lower']:
                    description += ', '
            if wall['right']['middle']:
                description += f"{wall['right']['middle']}"
                if wall['right']['lower']:
                    description += ', '
            if wall['right']['lower']:
                description += f"{wall['right']['lower']}"
            if wall['left']['upper'] or wall['left']['middle'] or wall['left']['lower']:
                description += ', Left: '
                if wall['left']['upper']:
                    description += f"{wall['left']['upper']}"
                    if wall['left']['middle'] or wall['left']['lower']:
                        description += ', '
                if wall['left']['middle']:
                    description += f"{wall['left']['middle']}"
                    if wall['left']['lower']:
                        description += ', '
                if wall['left']['lower']:
                    description += f"{wall['left']['lower']}"
            description += '\n'

        description += "Things:\n"
        for thing in self.things:
            x, y, type = thing
            thing_desc = thing_type_descriptions.get(type, f"Unknown type {type}")
            description += f" - {thing_desc} at ({x}, {y})\n"
        return description

def main():
    parser = argparse.ArgumentParser(description='Process WAD files and output room descriptions.')
    parser.add_argument('-basewad', required=True, help='The base WAD file (e.g., doom1.wad)')
    parser.add_argument('-file', required=False, help='The patch WAD file (e.g., some_mod_pwad.wad)')
    parser.add_argument('-output', required=False, help='The output file for ZIL code', default='output.zil')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    def debug_log(message):
        if args.verbose:
            print(message, file=sys.stderr)

    if not os.path.exists(args.basewad):
        print(f"Base WAD file '{args.basewad}' not found.")
        sys.exit(1)

    wad = WADFile(args.basewad)

    if args.file:
        if not os.path.exists(args.file):
            print(f"Patch WAD file '{args.file}' not found.")
            sys.exit(1)
        patch_wad = WADFile(args.file)
        wad = wad.merge(patch_wad)

    # Define paths
    DATA_DIR = 'data'
    TEXTURE_DESCRIPTIONS_FILE = os.path.join(DATA_DIR, 'texture_descriptions.json')
    THING_TYPES_FILE = os.path.join(DATA_DIR, 'thing_types.json')

    os.makedirs(DATA_DIR, exist_ok=True)

    # WIP: Scrape and save texture descriptions if not present
    if not os.path.exists(TEXTURE_DESCRIPTIONS_FILE):
        texture_url = 'https://doomwiki.org/wiki/Texture'
        textures = scrape_texture_descriptions(texture_url)
        with open(TEXTURE_DESCRIPTIONS_FILE, 'w') as f:
            json.dump(textures, f, indent=4)

    # Scrape and save thing types if not present
    if not os.path.exists(THING_TYPES_FILE):
        thing_url = 'https://doomwiki.org/wiki/Thing_types_by_number'
        things = scrape_thing_types(thing_url)
        with open(THING_TYPES_FILE, 'w') as f:
            json.dump(things, f, indent=4)

    # Load the texture descriptions from the JSON file
    with open(TEXTURE_DESCRIPTIONS_FILE, 'r') as f:
        texture_descriptions = json.load(f)

    # Load the thing descriptions from the JSON file
    with open(THING_TYPES_FILE, 'r') as f:
        thing_type_descriptions = json.load(f)

    thing_type_descriptions = {int(k): v for k, v in thing_type_descriptions.items()}

    vertex_data = wad.read_lump('VERTEXES')
    linedef_data = wad.read_lump('LINEDEFS')
    sidedef_data = wad.read_lump('SIDEDEFS')
    sector_data = wad.read_lump('SECTORS')
    thing_data = wad.read_lump('THINGS')

    vertexes = parse_vertexes(vertex_data)
    linedefs = parse_linedefs(linedef_data)
    sidedefs = parse_sidedefs(sidedef_data)
    sectors = parse_sectors(sector_data)
    things = parse_things(thing_data)

    rooms = {}
    for i, sector_data in enumerate(sectors):
        rooms[i] = Room(i, sector_data)

    for linedef in linedefs:
        v1, v2, flags, types, tag, right_sidedef, left_sidedef = linedef
        right_sector_id = sidedefs[right_sidedef][5]
        rooms[right_sector_id].add_linedef(linedef, sidedefs)
        rooms[right_sector_id].add_vertex(vertexes[v1])
        rooms[right_sector_id].add_vertex(vertexes[v2])
        if left_sidedef != -1:
            left_sector_id = sidedefs[left_sidedef][5]
            rooms[left_sector_id].add_linedef(linedef, sidedefs)
            rooms[left_sector_id].add_vertex(vertexes[v1])
            rooms[left_sector_id].add_vertex(vertexes[v2])

    if args.verbose:
        for room_id, room in rooms.items():
            debug_log(f"Room {room_id} vertices: {room.vertexes}")

    for thing in things:
        x, y, type = thing
        added = False
        for room in rooms.values():
            if point_in_polygon(x, y, list(room.vertexes)):
                room.add_thing(thing)
                added = True
                break
        if not added:
            if args.verbose:
                debug_log(f"Thing at ({x}, {y}) of type {type} not added to any room.")

    with open(args.output, 'w') as f:
        for room in rooms.values():
            zil_description = room.describe_zil(texture_descriptions, thing_type_descriptions)
            if args.verbose:
                debug_log(zil_description)
            f.write(zil_description)
            f.write('\n')

    debug_log(f"ZIL descriptions written to {args.output}")

if __name__ == "__main__":
    main()

