import re
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path


PDFS = [Path("resune.pdf"), Path("Chinmoy Biswas CV_Short.docx.pdf")]
PNGS = [Path("style_example.png"), Path("experiences.png")]


def extract_url_candidates(path: Path):
    data = path.read_bytes()
    pattern = re.compile(rb"https?://[^\s<>()\[\]{}\"']+|www\.[^\s<>()\[\]{}\"']+")
    urls = {
        match.decode("latin1", "ignore").rstrip(").,;]")
        for match in pattern.findall(data)
    }
    return sorted(urls)


def parse_png(path: Path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")

    offset = 8
    width = height = bit_depth = color_type = None
    idat = bytearray()

    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_data = data[offset + 8:offset + 8 + length]
        offset += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", chunk_data
            )
            if interlace != 0:
                raise ValueError("Interlaced PNGs are not supported by this helper")
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if bit_depth != 8 or color_type not in (2, 6):
        raise ValueError(
            f"Unsupported PNG format for {path.name}: bit_depth={bit_depth}, color_type={color_type}"
        )

    bpp = 3 if color_type == 2 else 4
    raw = zlib.decompress(bytes(idat))
    stride = width * bpp
    pos = 0
    prev = [0] * stride
    pixels = []

    def paeth(a, b, c):
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    for _ in range(height):
        filter_type = raw[pos]
        pos += 1
        row = list(raw[pos:pos + stride])
        pos += stride
        recon = [0] * stride

        for i, value in enumerate(row):
            left = recon[i - bpp] if i >= bpp else 0
            up = prev[i]
            up_left = prev[i - bpp] if i >= bpp else 0

            if filter_type == 0:
                recon[i] = value
            elif filter_type == 1:
                recon[i] = (value + left) & 0xFF
            elif filter_type == 2:
                recon[i] = (value + up) & 0xFF
            elif filter_type == 3:
                recon[i] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                recon[i] = (value + paeth(left, up, up_left)) & 0xFF
            else:
                raise ValueError(f"Unsupported filter type {filter_type}")

        prev = recon
        for x in range(width):
            base = x * bpp
            r, g, b = recon[base], recon[base + 1], recon[base + 2]
            a = recon[base + 3] if bpp == 4 else 255
            pixels.append((r, g, b, a))

    return width, height, pixels


def summarize_png(path: Path):
    width, height, pixels = parse_png(path)
    visible = [(r, g, b) for r, g, b, a in pixels if a > 8]
    if not visible:
        return {"width": width, "height": height, "palette": [], "brightness": []}

    quantized = [((r // 32) * 32, (g // 32) * 32, (b // 32) * 32) for r, g, b in visible]
    palette = [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in Counter(quantized).most_common(8)]

    bands = []
    band_count = 6
    for band_idx in range(band_count):
        y0 = (height * band_idx) // band_count
        y1 = (height * (band_idx + 1)) // band_count
        band_pixels = []
        for y in range(y0, max(y0 + 1, y1)):
          start = y * width
          end = start + width
          band_pixels.extend(pixels[start:end])
        avg = sum((r + g + b) / 3 for r, g, b, a in band_pixels if a > 8) / max(
            1, sum(1 for _, _, _, a in band_pixels if a > 8)
        )
        bands.append(round(avg, 2))

    return {"width": width, "height": height, "palette": palette, "brightness": bands}


def main():
    print("PDF URL CANDIDATES")
    for pdf in PDFS:
        print(f"-- {pdf.name} --")
        try:
            urls = extract_url_candidates(pdf)
            print("\n".join(urls) if urls else "no URL-like strings found")
        except Exception as exc:
            print(f"error: {exc}")

    print("\nPNG SUMMARIES")
    for png in PNGS:
        print(f"-- {png.name} --")
        try:
            summary = summarize_png(png)
            print(f"size: {summary['width']}x{summary['height']}")
            print("palette:", ", ".join(summary["palette"]))
            print("band brightness:", ", ".join(map(str, summary["brightness"])))
        except Exception as exc:
            print(f"error: {exc}")


if __name__ == "__main__":
    sys.exit(main())