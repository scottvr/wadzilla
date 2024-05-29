import struct

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

THING_TYPE_DESCRIPTIONS = {
    1: "Player 1 Start",
    2: "Player 2 Start",
    3: "Player 3 Start",
    4: "Player 4 Start",
    11: "Deathmatch Start",
    2001: "Shotgun",
    2002: "Chaingun",
    2003: "Rocket Launcher",
    2004: "Plasma Gun",
    2005: "BFG9000",
    2006: "Chainsaw",
    2045: "Berserk Pack",
    2046: "Partial Invisibility",
    2047: "Computer Area Map",
    2048: "Light Amplification Visor",
    2049: "Megasphere",
    #  and so on ...
}

class Room:
    def __init__(self, sector_id, sector_data):
        self.sector_id = sector_id
        self.floor_height, self.ceiling_height, self.floor_tex, self.ceiling_tex, self.light_level, self.type, self.tag = sector_data
        self.vertexes = set()
        self.linedefs = []
        self.things = []

    def add_vertex(self, vertex):
        self.vertexes.add(vertex)

    def add_linedef(self, linedef):
        self.linedefs.append(linedef)

    def add_thing(self, thing):
        self.things.append(thing)

    def describe_zil(self):
        description = f"<ROOM {self.sector_id} {self.floor_tex}/{self.ceiling_tex}>\n"
        description += f"FLOOR HEIGHT: {self.floor_height}, CEILING HEIGHT: {self.ceiling_height}\n"
        description += "Things:\n"
        for thing in self.things:
            x, y, type = thing
            thing_desc = THING_TYPE_DESCRIPTIONS.get(type, f"Unknown type {type}")
            description += f" - {thing_desc} at ({x}, {y})\n"
        return description

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

# Example usage:
wad = WADFile('doom1.wad')
vertex_data = wad.read_lump('VERTEXES')
linedef_data = wad.read_lump('LINEDEFS')
sidedef_data = wad.read_lump('SIDEDEFS')
sector_data = wad.read_lump('SECTORS')
thing_data = wad.read_lump('THINGS')

# Parsing data
vertexes = parse_vertexes(vertex_data)
linedefs = parse_linedefs(linedef_data)
sidedefs = parse_sidedefs(sidedef_data)
sectors = parse_sectors(sector_data)
things = parse_things(thing_data)

# Create rooms from sectors
rooms = {}
for i, sector_data in enumerate(sectors):
    rooms[i] = Room(i, sector_data)

# Add linedefs to rooms and define their vertexes
for linedef in linedefs:
    v1, v2, flags, types, tag, right_sidedef, left_sidedef = linedef
    if right_sidedef != -1:
        sector_id = sidedefs[right_sidedef][5]
        rooms[sector_id].add_linedef(linedef)
        rooms[sector_id].add_vertex(vertexes[v1])
        rooms[sector_id].add_vertex(vertexes[v2])
    if left_sidedef != -1:
        sector_id = sidedefs[left_sidedef][5]
        rooms[sector_id].add_linedef(linedef)
        rooms[sector_id].add_vertex(vertexes[v1])
        rooms[sector_id].add_vertex(vertexes[v2])

# Print vertices for each room to debug
for room_id, room in rooms.items():
    print(f"Room {room_id} vertices: {room.vertexes}")

# Determine which room each thing belongs to and add it
for thing in things:
    x, y, type = thing
    added = False
    for room in rooms.values():
        if point_in_polygon(x, y, list(room.vertexes)):
            room.add_thing(thing)
            added = True
            break
    if not added:
        print(f"Thing at ({x}, {y}) of type {type} not added to any room.")

# Output ZIL descriptions
for room in rooms.values():
    print(room.describe_zil())

