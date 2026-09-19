# C5TAKO / XIAO ESP32-C5

Build with ESP-IDF v5.5.5. ESP-IDF v6.1 was tried first, but its Mbed TLS 4
removes DES APIs used by this port's NFC/FAP code. v5.5.5 supports ESP32-C5
and stays compatible with the existing port. The build uses
`build_c5tako_idf55/sdkconfig`; the tracked root `sdkconfig` is not used.

```powershell
$env:ESP_IDF_DIR = 'C:\Users\User\.cache\c5tako-idf\esp-idf-v5.5.5'
$env:IDF_TOOLS_PATH = 'C:\Users\User\.cache\c5tako-idf\tools'
python winbuild.py build --board c5tako
python tools/merge_c5tako.py
python -m esptool --chip esp32c5 --port COMx write_flash 0x0 build_c5tako_idf55/FlipperPort-2.0.0-C5TAKO-8MB-merged.bin
```

The merged file and adjacent JSON verification report are in
`build_c5tako_idf55/`. The script reads offsets from `flasher_args.json`,
checks each image and 0xFF padding byte, and verifies app size against the
factory partition. The 8MB layout has a single 6MB factory app; OTA is off.
Use manual flashing at 0x0. Do not use the root S3 `sdkconfig` or OTA image.
Verified build: app 3,598,784 bytes, 2,692,672 bytes free in factory partition;
merged image 3,664,320 bytes, SHA-256
`898cfcdf04a4d94d3b7f841e85a0de5c498518a1af61f24c0d2618888d27ca9f`.
Image regions are bootloader at 0x2000, partition table at 0x8000, app at
0x10000. All intervening padding bytes verified as 0xFF.

| Hardware | GPIO |
| --- | --- |
| SPI SCK / MOSI / MISO | 8 / 10 / 9 |
| ST7789 CS / DC / reset | 7 / 1 / none; software reset |
| Backlight | 25, active high |
| SD CS | 5, shared SPI2 host |
| Left / Center / Up / Right / Down | 23 / 4 / 24 / 0 / 28, active low |
| Battery ADC / divider enable | 6 / 26, active high, nominal 1:2 |
| CC1101 CS / GDO0 / GDO2 | 2 / 12 / 11 (reference wiring) |
| Buzzer / user LED | 3 low / 27 high (LED off) |

Short Left moves left; hold Left for Back. Short Center selects; hold Center
for OK Long in screens that support it. Up/Down navigate.
The Passport profile closes with any short button press, since this board has
no dedicated Back button.
Display renders the original 128x64 Flipper UI at 232x116 on the 240x240
panel, centered without distortion. This preserves menu, dialog, popup,
keyboard and file-browser geometry. Top and bottom margins are unavoidable
with the original 2:1 UI aspect ratio. On-device readability remains to be
checked.

ST7789 starts at RGB order, inversion on, SPI mode 0, 40MHz, zero rotation
and offsets 0/0. SD uses the existing shared SPI host and FAT32 path. The
C5TAKO SD path follows the ZipherDeauthC5 setup: CS GPIO5, SPI 8/10/9,
80 ms settling, idle clocks before CMD0, and a 4 MHz run clock.
Battery voltage is estimated through the switched divider. No charger-status
or VBUS-sense signal exists, so charging is not reported and automatic
low-battery shutdown is disabled on this board. Wi-Fi scan and STA connection use
both 2.4 and 5GHz where local regulatory rules allow; the radio uses one band
at a time. Manual attack/capture flows remain limited to 2.4GHz. The board
has no touch, NFC, IR, nRF24, I2S speaker, or USB-OTG HID; those
hardware-dependent features are off. The ZipherDeauthC5 reference maps CC1101
GDO0/2 to GPIO12/11, currently used by this build's UART console. Sub-GHz
remains off until the console is relocated and CC1101 operation is tested.
The GPIO3 buzzer is held quiet; this port's speaker HAL requires I2S and does
not drive the buzzer yet.

Copy project release `sdcard.zip` contents directly to the root of a FAT32
SD card for apps that need assets and databases. Firmware alone cannot provide
those files. Initial user testing confirmed the display works but reported
`ESP_ERR_TIMEOUT` during SD initialization, followed by CPU lockup/watchdog
resets. The SD error cleanup and bus startup were revised; this build still
needs a hardware retest. Buttons, battery readings, and both Wi-Fi bands also
need on-device checks.
