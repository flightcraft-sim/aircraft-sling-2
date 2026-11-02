# Panel review

The previews are 1728 × 968 pixels, matching the reference aspect ratio. `tests/render.rs` loads the pack into a real FlightCraft session and rasterizes actual egui meshes and the font atlas. The in-flight capture uses the engine's New York region. The PFD and MFD images are crops of that capture, not separately invented instrument artwork.

The reference photo was inspected alongside both the initial and revised renders. It remains external and is neither embedded nor redistributed. Revisions separated the tightly spaced breaker and switch labels into sized placards, enlarged breaker collars, and moved switch labels above the switches. FlightCraft's screen designs are intentionally original.

## Placement comparison

Coordinates below are in the supplied 1728 × 968 measurement frame. Equipment data uses the uniform conversion 0.77 mm per pixel (about 1,250 mm across the shell). This table compares **declared layout rectangles**, which are independently checked by the harness; it does not claim every host-drawn face fills its rectangle.

| Unit | Spec top-left | Pack top-left | Spec and pack size | Position error |
|---|---|---|---|---|
| Left touch display | 248, 308 | 248, 308 | 424 × 308 | <0.01 px |
| Right touch display | 1062, 308 | 1062, 308 | 424 × 308 | <0.01 px |
| Electronic standby | 798, 238 | 798, 238 | 132 × 137 | <0.01 px |
| Navigator | 745, 382 | 745, 382 | 235 × 98 | <0.01 px |
| Autopilot installation | 742, 485 | 742, 485 | 243 × 77 | <0.01 px |
| Floor selector centre | 865, 890 | 865, 890 | Handle face controlled by host | <0.01 px |

All 23 measured breakers have individual declared electrical loads and the specified amp ratings. Their caps are centred at the supplied block coordinates; cell rectangles also reserve space for labels. There are separate bracket, guard-bar, placard, vent, dimmer, cabin-heat, ELT, key, lane-control, and recovery installations. The original measured anchors are retained in `data/panel-measurements.json`.

## Outstanding visible differences

A few-percent **photo** match has not been achieved. The pack cannot repair these host limitations without engine changes:

- The shell can select only `panel`, `raised`, or `dial` theme tokens. None is the measured neutral charcoal; the existing raised token is blue-grey. Arbitrary panel colours are rejected.
- Touch-display bezel margins, soft keys, knobs, and card-slot details are fixed. The original display skins remain distinct from real screen software.
- The digital autopilot face preserves its own wide aspect ratio inside the measured installation and therefore does not fill the required 243 × 77 rectangle.
- The navigator's fixed font sizing is too large for this measured narrow unit. Master-light captions also overlap at their real spacing.
- Functional lane controls are host rockers with decorative guard bars. The generic guarded-toggle element has no typed lane binding, and its decorative red lamps do not follow lane fault state. A true guarded lane toggle is needed.
- The parachute element draws pin/pull controls rather than the measured red rounded handle. ELT, cabin knobs, and vents retain generic host artwork. The floor selector's handle shape is generic.
- EMS BKUP and EFIS BKUP use declared generic control values. The host has no connection from those generic controls to backup power routing. They are not incorrectly bound to master or alternator switches.
- NAV powers the navigation and strobe loads together, matching the NAV + STROBE sublabel; breakers remain individual. WIGWAG is a placard only; alternating landing-light timing is not available.

There is also a conflict in the supplied references: the written specification places the floor selector at y = 890 and extends the console to y = 968, while the photograph visibly places the selector higher and ends its console earlier. The pack follows the written coordinates exactly. Resolving that discrepancy is necessary before both references can be matched within a few percent.

The layout and private skin slot identifiers are ready for a host equipment-skin extension. Its current limitation is described in `private-skins.md`. No reference-photo pixels, brand logos, or replica display software are present in these previews.
