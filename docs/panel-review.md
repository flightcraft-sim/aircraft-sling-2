# Panel review

The panel uses FlightCraft main revision `3512ca9` and its placed equipment, shell palette, display composition, and typed hardware controls. The 1728 × 968 previews preserve the reference image's aspect ratio. `tests/render.rs` loads the distributed pack into a real session. The in-flight capture runs the actual egui and GPU synthetic-vision passes over original procedural review terrain; the detail images are crops of that capture. The ground preview uses the engine's public CPU preview helper, which omits GPU synthetic vision.

The reference and successive renders were inspected side by side. The photograph, comparison overlays, and side-by-side files remain outside this repository. No reference pixels, manufacturer logos, or replica screen software appear in the pack's previews.

## Placement comparison

Coordinates below use the supplied 1728 × 968 frame, with a uniform conversion of 0.77 mm per pixel. Rectangles include the installation's bezel or reserved label area. The harness checks their declared bounds; these errors do not imply that every native painted detail matches the photograph.

| Installation | Spec top-left | Pack top-left | Spec and pack size | Declared error |
|---|---|---|---|---|
| Left touch display | 248, 308 | 248, 308 | 424 × 308 | <0.01 px |
| Right touch display | 1062, 308 | 1062, 308 | 424 × 308 | <0.01 px |
| Electronic standby | 798, 238 | 798, 238 | 132 × 137 | <0.01 px |
| Navigator | 745, 382 | 745, 382 | 235 × 98 | <0.01 px |
| Autopilot | 742, 485 | 742, 485 | 243 × 77 | <0.01 px |
| Floor selector pivot | Photo: 865, 770 | 865, 770 | Native T-handle | <0.01 px |
| Console bottom | Photo: y = 855 | y = 855 | Separate console outline | <0.01 px |
| Vent centres | Photo: 145/1575, 585 | 145/1575, 585 | 144 × 144 installation; approximately 137 px rim | <0.01 px |

The selector now follows the photograph at y = 770 instead of the written y = 890. Its console ends at y = 855 instead of continuing to the image bottom at y = 968. This resolves the conflict in favour of the photograph, as requested. Side-by-side inspection also moved the vent centres from the written y = 560 to the photographed y = 585 and enlarged their rims. These corrections and their reasons are recorded in `data/panel-measurements.json`.

All 23 breaker caps have the measured labels, ratings, and centres. Native label offsets are compensated in their installation envelopes. The same distinction is recorded for the lane levers and lamps, rocker faces, and cabin knobs. Small bracket captions, separate knob placards, guard bars, screws, and the chute placard use original measured geometry.

## Equipment and colour

Both touch displays default to `integrated_pfd`, with synthetic vision, a left engine strip, a bottom-left map, and a bottom-right terrain inset. Their configurable bezels use the specified margins, four softkeys, two corner knobs, and a card slot. The navigator has a home column, four-by-two tiles, and a frequency column. The autopilot fills its measured rectangle with individually placed controls; LVL is cyan when the host reports its level mode active.

The shell face is `#333333`, the glare shield is near-black `#0b0b0b`, the bezels are `#080808`, and the placards are `#f5f5f2`. These follow the requested charcoal range. A flat-face sample at image coordinate (730, 275) is RGB (51, 51, 51) in the render and (77, 77, 77) in the supplied photograph. Thus the requested material colour is implemented, but a few-percent photographic colour match is not claimed; exposure, reflections, and shading differ.

The hardware uses native black rockers, black push-pull breakers, guarded lane toggles with typed lane bindings, a rounded red chute pull, a silver ignition key, louvred vents, an ELT plate with a red rocker, and a red floor T-handle. EMS BKUP and EFIS BKUP feed real independent backup buses. LAND controls both landing-light loads and its WIGWAG function alternates them. Tests verify guarded input, loss of main power, backup discharge, breaker isolation on backup, and both wigwag phases.

## Comparison artifacts and tool limitation

The requested engine `cargo xtask panel-compare` command was run through the build queue with the external reference and external output directory. It failed its output-location guard: the guard considers empty ancestor `.git` marker directories to be repositories, even when Git reports that the output is outside a checkout. Repeating the command with an external temporary output target produced the same error. The engine was left unchanged.

The pack's optional render test therefore includes a local comparison helper. With `SLING2_REFERENCE_PANEL` and `SLING2_COMPARE_OUTPUT` set, it writes `render.png`, `side-by-side.png`, `overlay.png`, `edge-difference.png`, and `alignment.json` outside any Git checkout. The report explicitly records that the engine comparison did not complete. The helper compares actual in-flight GPU pixels; it does not substitute replica instrument artwork. Its symmetric edge-proximity scores are sensitive to fonts, hardware artwork, and screen content, so they are review aids rather than percentage placement errors or acceptance thresholds.

## Remaining differences

A few-percent overall photograph match remains incomplete:

- FlightCraft's original screen artwork differs deliberately. The native standby face also omits the photograph's detailed bezel controls.
- Bezel shading, knob profiles, softkey spacing, and card-slot placement remain those of the native configurable style. The photograph has raised, textured hardware and reflections.
- The louvred vents have straight slats rather than the photographed curved openings. Their rim position and diameter have been corrected.
- Lane switches have the host's small red guard frames as well as the measured silver guard bars. The key is a simplified silver symbol. The ELT rocker has native segment proportions.
- The chute pull retains the host's pin/hold state text, and its red follows the host theme. The selector is a flat red T-handle rather than the photographed raised, sculpted handle. Both are functional controls at the corrected locations.
- Warning and caution lamps show simulated state; they are dark in the in-flight review while both are illuminated in the photograph. Their housings and captions retain native styling.
- The native LVL highlight checks ROL/PIT mode, while its button action selects the host's level guidance. The capture uses an actual ROL/PIT state to show the requested cyan light; this does not change host autopilot logic.
- The single visible LAND breaker interrupts the left logical lamp load; the right lamp has an independent logical breaker. Shared physical-breaker wiring remains a host limitation, documented in the estimate register.

The private skin extension now has working host registration hooks, described in `private-skins.md`. Stable installation ids and rectangles allow a separate private artwork pack to refine hardware and screens without moving this public layout.
