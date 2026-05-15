#!/usr/bin/env python3
"""Generate minimal extension icons."""
import struct

def create_png(size, color):
    """Create a minimal solid-color PNG."""
    import zlib

    def create_header(width, height):
        return struct.pack('>I', width) + struct.pack('>I', height) + \
               b'\x08\x02\x00\x00\x00'

    def create_idat(raw_data):
        compressed = zlib.compress(raw_data)
        return struct.pack('>I', len(compressed)) + compressed + struct.pack('>I', 0)

    raw = b''
    for y in range(size):
        raw += b'\x00'  # filter byte
        for x in range(size):
            raw += bytes(color)

    ihdr = create_header(size, size)
    idat = create_idat(raw)

    chunks = [
        b'\x89PNG\r\n\x1a\n',
        b'IHDR' + ihdr,
        b'IDAT' + idat,
        b'IEND' + struct.pack('>I', 0)
    ]

    result = b''
    for chunk in chunks:
        result += struct.pack('>I', len(chunk) - 4) + chunk

    return result

# Generate icons
for size, color in [(16, (50, 50, 50)), (32, (60, 60, 60))]:
    data = create_png(size, color)
    with open(f'icon{size}.png', 'wb') as f:
        f.write(data)
