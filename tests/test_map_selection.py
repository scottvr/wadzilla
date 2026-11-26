import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'wadzilla.py'


def map_lumps(marker, floor):
    # A triangular room with one Thing. Every level uses identical lump names.
    vertices = [(0, 0), (64, 0), (0, 64)]
    return [
        (marker, b''),
        ('THINGS', struct.pack('<5h', 8, 8, 0, 1, 7)),
        ('LINEDEFS', b''.join(struct.pack('<7h', i, (i + 1) % 3, 1, 0, 0, i, -1)
                              for i in range(3))),
        ('SIDEDEFS', struct.pack('<hh8s8s8sh', 0, 0, b'-', b'-', floor, 0) * 3),
        ('VERTEXES', b''.join(struct.pack('<hh', *v) for v in vertices)),
        ('SEGS', b''), ('SSECTORS', b''), ('NODES', b''),
        ('SECTORS', struct.pack('<hh8s8shhh', 0, 128, floor, b'SKY', 160, 0, 0)),
        ('REJECT', b''), ('BLOCKMAP', b''),
    ]


def write_wad(path, lumps, kind=b'IWAD'):
    payload = bytearray()
    directory = bytearray()
    for name, data in lumps:
        directory.extend(struct.pack('<II8s', 12 + len(payload), len(data), name.encode()))
        payload.extend(data)
    path.write_bytes(struct.pack('<4sII', kind, len(lumps), 12 + len(payload))
                     + payload + directory)


class MapSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        data = self.root / 'data'
        data.mkdir()
        for filename in ('thing_types.json', 'texture_descriptions.json'):
            (data / filename).write_text(json.dumps({}))
        self.first = map_lumps('E1M1', b'HANGAR')
        self.second = map_lumps('E1M2', b'PLANT')
        self.base = self.root / 'base.wad'
        write_wad(self.base, self.first + self.second)

    def convert(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '-b', str(self.base), *args],
                              cwd=self.root, capture_output=True, text=True)

    def assert_room(self, floor, *args):
        output = self.root / 'output.zil'
        output.unlink(missing_ok=True)
        result = self.convert(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        rooms = output.read_text()
        self.assertEqual(rooms.count('<ROOM '), 1)
        self.assertIn(f'(DESC "{floor}/SKY Room")', rooms)
        self.assertIn(f'MIDDLE "{floor}"', rooms)

    def test_select_first_then_second(self):
        self.assert_room('HANGAR', '--map', 'e1m1')
        self.assert_room('PLANT', '--map', 'E1M2')

    def test_default_remains_last_map(self):
        self.assert_room('PLANT')

    def test_missing_map(self):
        result = self.convert('--map', 'E1M3')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Map E1M3 not found', result.stderr)

    def test_missing_lump_is_not_borrowed_from_next_map(self):
        write_wad(self.base, [lump for lump in self.first if lump[0] != 'SECTORS']
                  + self.second)
        result = self.convert('--map', 'E1M1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SECTORS', result.stderr)
        self.assertIn('E1M1', result.stderr)

    def test_patch_overrides_only_its_own_maps(self):
        patch = self.root / 'patch.wad'
        write_wad(patch, map_lumps('E1M2', b'PATCH') + map_lumps('MAP01', b'ENTRY'), b'PWAD')
        self.assert_room('HANGAR', '-f', str(patch), '--map', 'E1M1')
        self.assert_room('PATCH', '-f', str(patch), '--map', 'E1M2')
        self.assert_room('ENTRY', '-f', str(patch), '--map', 'MAP01')
