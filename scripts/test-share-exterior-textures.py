#!/usr/bin/env python3
"""Storage-only repacking must preserve mesh bytes and deduplicate identical images."""
import importlib.util
import json
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('share', Path(__file__).with_name('share-exterior-textures.py'))
share = importlib.util.module_from_spec(spec)
spec.loader.exec_module(share)

class SharedStorage(unittest.TestCase):
    def test_lossless_views_and_shared_images(self):
        geometry = bytes(range(24))
        png = b'\x89PNG\r\n\x1a\n' + bytes(range(19))
        blob = geometry + png
        blob += b'\0' * (-len(blob) % 4)
        doc = dict(asset={'version':'2.0'}, buffers=[{'byteLength':len(blob)}],
                   bufferViews=[{'buffer':0,'byteOffset':0,'byteLength':24,'byteStride':12},
                                {'buffer':0,'byteOffset':24,'byteLength':len(png)}],
                   accessors=[{'bufferView':0,'count':2,'componentType':5126,'type':'VEC3'}],
                   images=[{'bufferView':1,'mimeType':'image/png','name':'paint'}])
        encoded = json.dumps(doc).encode(); encoded += b' ' * (-len(encoded) % 4)
        data = (struct.pack('<IIIII',0x46546c67,2,28+len(encoded)+len(blob),len(encoded),0x4e4f534a)
                + encoded + struct.pack('<II',len(blob),0x004e4942) + blob)
        textures = {}
        first = share.externalize(data, textures)
        self.assertEqual(first, share.externalize(data, textures))
        self.assertEqual(len(textures), 1)
        size = struct.unpack_from('<I',first,12)[0]
        result = json.loads(first[20:20+size])
        self.assertEqual(first[28+size:], geometry)
        self.assertEqual(result['accessors'], doc['accessors'])
        self.assertEqual(result['bufferViews'], doc['bufferViews'][:1])
        self.assertEqual(textures[result['images'][0]['uri']], png)
        self.assertNotIn('bufferView', result['images'][0])
        self.assertLess(len(first) + sum(map(len,textures.values())), 3 * len(data))

if __name__ == '__main__':
    unittest.main()
