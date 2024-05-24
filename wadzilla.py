import struct

class WADFile:
    def __init__(self, filename):
        self.filename = filename
        self.lumps = {}
        self._load_wad()

    def _load_wad(self):
        with open(self.filename, 'rb') as f:
            header = f.read(12)
            if header[:4] not in (b'IWAD', b'PWAD'):
                raise ValueError("Not a valid WAD file")
            num_lumps, info_table_offset = struct.unpack('<II', header[4:])
            f.seek(info_table_offset)
            for _ in range(num_lumps):
                lump_info = f.read(16)
                offset, size, name = struct.unpack('<II8s', lump_info)
                name = name.rstrip(b'\0').decode('ascii')
                self.lumps[name] = (offset, size)

    def get_lump_data(self, lump_name):
        if lump_name not in self.lumps:
            raise ValueError(f"Lump {lump_name} not found")
        offset, size = self.lumps[lump_name]
        with open(self.filename, 'rb') as f:
            f.seek(offset)
            return f.read(size)

def parse_vertexes(data):
    num_vertexes = len(data) // 4
    vertexes = []
    for i in range(num_vertexes):
        x, y = struct.unpack_from('<hh', data, i * 4)
        vertexes.append((x, y))
    return vertexes

def parse_linedefs(data):
    num_linedefs = len(data) // 14
    linedefs = []
    for i in range(num_linedefs):
        v1, v2, flags, types, tag, right_sidedef, left_sidedef = struct.unpack_from('<hhhhhhh', data, i * 14)
        linedefs.append((v1, v2, flags, types, tag, right_sidedef, left_sidedef))
    return linedefs

def parse_sidedefs(data):
    num_sidedefs = len(data) // 30
    sidedefs = []
    for i in range(num_sidedefs):
        x_offset, y_offset, upper_tex, lower_tex, middle_tex, sector = struct.unpack_from('<hh8s8s8sh', data, i * 30)
        upper_tex = upper_tex.rstrip(b'\0').decode('ascii')
        lower_tex = lower_tex.rstrip(b'\0').decode('ascii')
        middle_tex = middle_tex.rstrip(b'\0').decode('ascii')
        sidedefs.append((x_offset, y_offset, upper_tex, lower_tex, middle_tex, sector))
    return sidedefs

def parse_sectors(data):
    num_sectors = len(data) // 26
    sectors = []
    for i in range(num_sectors):
        floor_height, ceiling_height, floor_tex, ceiling_tex, light_level, sector_type, tag = struct.unpack_from('<hh8s8shhh', data, i * 26)
        floor_tex = floor_tex.rstrip(b'\0').decode('ascii')
        ceiling_tex = ceiling_tex.rstrip(b'\0').decode('ascii')
        sectors.append((floor_height, ceiling_height, floor_tex, ceiling_tex, light_level, sector_type, tag))
    return sectors

def parse_things(data):
    num_things = len(data) // 10
    things = []
    for i in range(num_things):
        x, y, angle, type, flags = struct.unpack_from('<hhhhh', data, i * 10)
        things.append((x, y, angle, type, flags))
    return things

class Room:
    def __init__(self, sector_id, sector_data):
        self.sector_id = sector_id
        self.floor_height = sector_data[0]
        self.ceiling_height = sector_data[1]
        self.floor_tex = sector_data[2]
        self.ceiling_tex = sector_data[3]
        self.light_level = sector_data[4]
        self.type = sector_data[5]
        self.tag = sector_data[6]
        self.linedefs = []
        self.things = []

    def add_linedef(self, linedef):
        self.linedefs.append(linedef)

    def add_thing(self, thing):
        self.things.append(thing)

    def describe_zil(self, vertexes, sectors):
        description = f"<ROOM ROOM-{self.sector_id}\n"
        description += f"      (DESC \"Room {self.sector_id}: Floor texture is {self.floor_tex}, ceiling texture is {self.ceiling_tex}.\")\n"
        if self.light_level > 0:
            description += f"      (FLAGS LIGHTBIT)\n"
        # Define exits based on linedefs
        exits = ""
        for linedef in self.linedefs:
            v1, v2, flags, types, tag, right_sidedef, left_sidedef = linedef
            start_vertex = vertexes[v1]
            end_vertex = vertexes[v2]
            if right_sidedef != -1:
                right_sector_id = sidedefs[right_sidedef][5]
                if right_sector_id != self.sector_id:
                    exits += f"      ({self._get_direction(start_vertex, end_vertex)} TO ROOM-{right_sector_id})\n"
        if exits:
            description += exits
        else:
            description += f"      (FLAGS LIGHTBIT)\n"
        description += ">\n"
        return description

    def _get_direction(self, start, end):
        if start[0] == end[0]:  # Vertical line
            return "NORTH" if end[1] > start[1] else "SOUTH"
        elif start[1] == end[1]:  # Horizontal line
            return "EAST" if end[0] > start[0] else "WEST"
        else:
            return "UNKNOWN"  # Should not happen in typical DOOM maps

        return description

def describe_map(wad_filename):
    wad = WADFile(wad_filename)

    vertexes = parse_vertexes(wad.get_lump_data('VERTEXES'))
    linedefs = parse_linedefs(wad.get_lump_data('LINEDEFS'))
    sidedefs = parse_sidedefs(wad.get_lump_data('SIDEDEFS'))
    sectors = parse_sectors(wad.get_lump_data('SECTORS'))
    things = parse_things(wad.get_lump_data('THINGS'))

    rooms = {i: Room(i, sector) for i, sector in enumerate(sectors)}

    for linedef in linedefs:
        v1, v2, flags, types, tag, right_sidedef, left_sidedef = linedef
        if right_sidedef != -1:
            sidedef = sidedefs[right_sidedef]
            rooms[sidedef[5]].add_linedef(linedef)

    for thing in things:
        x, y, angle, type, flags = thing
        # Assuming thing sector ID can be determined somehow
        for room in rooms.values():
            if some_condition_to_determine_thing_in_room(thing, room):  # Needs proper implementation
                room.add_thing(thing)
                break

    descriptions = [room.describe() for room in rooms.values()]
    return "\n".join(descriptions)

def describe_map_in_zil(wad_filename):
    wad = WADFile(wad_filename)

    vertexes = parse_vertexes(wad.get_lump_data('VERTEXES'))
    linedefs = parse_linedefs(wad.get_lump_data('LINEDEFS'))
    sidedefs = parse_sidedefs(wad.get_lump_data('SIDEDEFS'))
    sectors = parse_sectors(wad.get_lump_data('SECTORS'))
    things = parse_things(wad.get_lump_data('THINGS'))

    rooms = {i: Room(i, sector) for i, sector in enumerate(sectors)}

    for linedef in linedefs:
        v1, v2, flags, types, tag, right_sidedef, left_sidedef = linedef
        if right_sidedef != -1:
            sidedef = sidedefs[right_sidedef]
            rooms[sidedef[5]].add_linedef(linedef)

    for thing in things:
        x, y, angle, type, flags = thing
        for room in rooms.values():
            if some_condition_to_determine_thing_in_room(thing, room):  # Implement proper condition
                room.add_thing(thing)
                break

    zil_output = "\n".join(room.describe_zil(vertexes, sectors) for room in rooms.values())
    return zil_output

# Example usage
wad_filename = 'doom1.wad'
print(describe_map_in_zil(wad_filename))



