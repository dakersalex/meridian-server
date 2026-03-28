#!/usr/bin/env python3
"""Generate Meridian PWA icons without any dependencies."""
import struct, zlib, os

os.makedirs('/Users/alexdakers/meridian-server/icons', exist_ok=True)

def make_png(size):
    """Create a PNG with dark background and amber M lettermark."""
    # Colours
    bg   = (26, 25, 23)      # #1a1917
    amber = (196, 120, 58)   # #c4783a

    # Build pixel grid
    pixels = [list(bg) for _ in range(size * size)]

    def set_pixel(x, y, colour):
        if 0 <= x < size and 0 <= y < size:
            pixels[y * size + x] = list(colour)

    def draw_line(x0, y0, x1, y1, colour, stroke):
        """Bresenham line with thickness."""
        dx, dy = abs(x1-x0), abs(y1-y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for tx in range(-stroke//2, stroke//2+1):
                for ty in range(-stroke//2, stroke//2+1):
                    set_pixel(x0+tx, y0+ty, colour)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy; x0 += sx
            if e2 < dx:
                err += dx; y0 += sy

    pad = size // 7
    stroke = max(size // 12, 3)
    mid_x = size // 2
    mid_y = size // 2 - size // 16  # slightly above centre

    # Draw M: left leg, left diagonal, right diagonal, right leg
    draw_line(pad, size-pad, pad, pad, amber, stroke)
    draw_line(pad, pad, mid_x, mid_y, amber, stroke)
    draw_line(mid_x, mid_y, size-pad, pad, amber, stroke)
    draw_line(size-pad, pad, size-pad, size-pad, amber, stroke)

    # Encode as PNG
    def png_chunk(tag, data):
        c = zlib.crc32(tag + data) & 0xffffffff
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', c)

    raw = b''
    for y in range(size):
        raw += b'\x00'  # filter type None
        for x in range(size):
            r, g, b = pixels[y * size + x]
            raw += bytes([r, g, b])

    compressed = zlib.compress(raw, 9)

    png  = b'\x89PNG\r\n\x1a\n'
    png += png_chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
    png += png_chunk(b'IDAT', compressed)
    png += png_chunk(b'IEND', b'')
    return png

for size in [192, 512]:
    path = f'/Users/alexdakers/meridian-server/icons/icon-{size}.png'
    with open(path, 'wb') as f:
        f.write(make_png(size))
    print(f'Created {path} ({os.path.getsize(path)} bytes)')

print('Done')
