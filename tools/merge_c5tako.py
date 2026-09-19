"""Merge and verify the C5TAKO flash image from ESP-IDF's actual offsets."""

import hashlib
import json
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build_c5tako_idf55"
FLASH_SIZE = 8 * 1024 * 1024


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    args = json.loads((BUILD / "flasher_args.json").read_text())
    if args["flash_settings"]["flash_size"] != "8MB":
        raise ValueError("build flash size is not 8MB")
    files = sorted((int(offset, 0), BUILD / name)
                   for offset, name in args["flash_files"].items())
    if not files or files[0][0] < 0 or args["extra_esptool_args"]["chip"] != "esp32c5":
        raise ValueError("not an ESP32-C5 build")

    regions = []
    end = 0
    for offset, path in files:
        data = path.read_bytes()
        if offset < end or offset + len(data) > FLASH_SIZE:
            raise ValueError(f"overlap or flash overflow: {path}")
        regions.append((offset, path, data))
        end = offset + len(data)

    table = (BUILD / args["partition-table"]["file"]).read_bytes()
    factory = None
    for pos in range(0, len(table) - 31, 32):
        magic, kind, subtype, offset, size = struct.unpack_from("<HBBII", table, pos)
        if magic == 0xFFFF:
            break
        if magic == 0x50AA and kind == 0 and subtype == 0:
            factory = (offset, size)
            break
    if factory is None:
        raise ValueError("factory app partition missing")
    app_offset = int(args["app"]["offset"], 0)
    app_size = (BUILD / args["app"]["file"]).stat().st_size
    if app_offset != factory[0] or app_size > factory[1]:
        raise ValueError("app offset/size does not fit factory partition")
    if factory[0] + factory[1] > FLASH_SIZE:
        raise ValueError("partition exceeds flash")

    version_header = (ROOT / "components/toolbox/fw_version.h").read_text()
    version = re.search(r'#define\s+FURI_ESP32_VERSION\s+"([^"]+)"', version_header).group(1)
    output = BUILD / f"FlipperPort-{version}-C5TAKO-8MB-merged.bin"
    image = bytearray(b"\xff" * end)
    for offset, _, data in regions:
        image[offset:offset + len(data)] = data
    output.write_bytes(image)

    merged = output.read_bytes()
    cursor = 0
    report_regions = []
    for offset, path, data in regions:
        if any(b != 0xFF for b in merged[cursor:offset]):
            raise ValueError(f"padding before {path} is not 0xFF")
        if merged[offset:offset + len(data)] != data:
            raise ValueError(f"byte mismatch at {path}")
        cursor = offset + len(data)
        report_regions.append({"offset": hex(offset), "file": str(path.relative_to(BUILD)),
                               "size": len(data), "sha256": sha256(data)})
    if len(merged) != cursor or len(merged) > FLASH_SIZE:
        raise ValueError("merged image length invalid")

    report = {"image": output.name, "size": len(merged), "sha256": sha256(merged),
              "flash_size": FLASH_SIZE, "factory_offset": hex(factory[0]),
              "factory_size": factory[1], "app_size": app_size,
              "factory_free": factory[1] - app_size, "regions": report_regions}
    (BUILD / (output.stem + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
