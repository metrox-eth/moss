# Geometry sources and limits

| Item | Source / status |
| --- | --- |
| MOSS CORE PCB | Frozen 30 October 2026 KiCad model, SHA-256 `cffb4a378502802a778fcee618310e6f3fa5c49ad201b0c372728368ae3520d1`. It predates the 31 October integrated converter and H1 GND update. The fixed headers are retained. |
| Orange Pi | Previously supplied Orange Pi Zero 3W CAD. The cooler is a visual illustration within the measured 16 mm board/cooler assembly height. |
| Drive motors | Existing placed MOSS motor geometry. Encoder discs/magnets are visual references. |
| Six-way motor connector | Arduitronics RU00129 and MOSS workshop photos. KiCad XH-style visual reference; procurement retains the motor-supplied cable. See INTERFACE_VERIFICATION.md. |
| Core cable housings | Reconstructed from public JST GH/SH/PH/XH and Molex Mini-SPOX drawings. Detailed manufacturer mating CAD was not downloaded or redistributed. |
| Hoco HB1 | New photo-based visual model. 78 × 25 × 25 mm overall envelope from [HOCO](https://hocotech.com/product/mobile-accessories/cables/hubs-organizers/usb-hub-hb1-four-ports-usb-2-0-charging-and-data-sync/). Port orientation and approximate spacing follow the [official front photo](https://hocotech.com/wp-content/uploads/2018/07/hb1-four-usb-hub-silver-ports.jpg). Fillets, shell thickness and caps are illustrative. |
| Speaker | Existing `Speaker_3W_4Ohm` geometry extracted from the original R92 hardware STEP. Same world position and bounds; re-tessellated for smoother rendering. It is reference geometry, not a printable speaker. |
| Cytron | Existing photo-based visual model; terminal/body positions used to place cable ends. |
| Fans | Visual 30 × 30 × 10 mm models in the reserved fan positions. Lead outlets and vendor identity remain provisional. |
| Battery | Existing 140 × 73 × 48 mm packaging envelope, with a proposed cable outlet and XT30 pair. |
| STOP disconnect | PicoBlade 51021/51047 four-way pair, 9 mm mated length and 6.75 mm width from Molex drawings; simplified internal features. 28 AWG thin-insulation contacts selected. |
| Hull / ties | Separate prototype based on the native V0.7 hull, with five integral bridges and a local divider notch. Not substituted into the released rover print package. |

The hub and its cradle are placed 10 mm further toward +Y than the earlier rectangular envelope, to leave room for cable exits. This is a packaging proposal. The 80 cm captive lead is not fully coiled in the model, and mounting/plug clearance must be tried on the physical rover before committing the loom.

## Public dimensional references

- [JST GH catalogue](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf)
- [JST SH catalogue](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)
- [JST PH catalogue](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)
- [JST XH catalogue](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf)
- [Molex Mini-SPOX housing drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/526/5264/050375023_sd.pdf)
- [Molex PicoBlade mating drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/510/51047/510470400_sd.pdf)

See the machine-readable [connector placements](data/CONNECTOR_PLACEMENT.json), [HB1 record](data/HOCO_PROVENANCE.json), [speaker record](data/SPEAKER_PROVENANCE.json) and [model scope](data/MODEL_SCOPE.json).
