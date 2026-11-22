# Supported printers

`brother_pt` speaks Brother's P-touch **raster** protocol. Its print path targets
the **128-pin, 180-dpi** head used by the PT tape family. The model registry is in
`brother_pt/cmd.py` (`SUPPORTED_MODELS` / `UNSUPPORTED_MODELS`).

## Supported

All USB vendor id `0x04f9`, 128 pins, 180 dpi, tape widths 3.5–24 mm:

| Product id | Model | Notes |
| --- | --- | --- |
| 0x2060 | PT-E550W | |
| 0x2062 | PT-P750W | status frame after mode switch |
| 0x20af | PT-P710BT | pre-cut |
| 0x205f | PT-E500 | |
| 0x205e | PT-H500 | pre-cut |
| 0x2061 | PT-P700 | status frame after mode switch, pre-cut |
| 0x2073 | PT-D450 | sends print-information command |
| 0x2074 | PT-D600 | |
| 0x2007 | PT-2420PC | |
| 0x2011 | PT-2450PC | |
| 0x202d | PT-2430PC | pre-cut |
| 0x201f | PT-2700 | pre-cut |

The first three are verified against Brother's own documentation; the rest share
the identical raster wire format and are added on that basis — please report
results (good or bad) for any model beyond the first three.

## Recognised but not supported

These are detected (the CLI tells you why) but not driven, to avoid mis-printing:

- **360-dpi / wide-format heads** — PT-P900 / P900W / P950NW / P910BT / PT-9700PC.
  Different head width (560 or 384 pins, 70 bytes/raster row vs 16) and high-res
  modes; needs a separate print path.
- **D460BT-family** — PT-D410 / D460BT / D610BT / E310BT / E560BT. Need a
  model-specific init sequence.
- **P-Lite mode** — a PT-1230PC / P700 / P750W reporting a P-Lite product id is in
  mass-storage mode and does not accept raster; switch it out of P-Lite/EL mode.

Other media types (heat-shrink HSe, Fle) are not yet handled — the driver sends
the laminated-tape media byte.

## References

Brother's "Software Developer's Manual — Raster Command Reference" documents are
copyrighted by Brother Industries, Ltd. and are **cited, not redistributed**:

- Command-reference index: <https://support.brother.com/g/s/es/dev/en/command/reference/index.html>
- PT-P900/P900W/P950NW/P910BT raster reference:
  <https://download.brother.com/welcome/docp100407/cv_ptp900_eng_raster_102.pdf>
- PT-E550W/P750W/P710BT raster reference: `cv_pte550wp750wp710bt_eng_raster_102.pdf`
  (v1.02, 2014), reached through the index above.

Model ids and per-model quirks cross-checked against `ptouch-print`
(<https://git.familie-radermacher.ch/linux/ptouch-print.git>), which is GPL —
values are used as factual data, not copied code.
