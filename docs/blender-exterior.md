# Blender exterior review job

**V10 is installed**, following flight lead's accepted confined Blender 5.2 run. The source
`scripts/blender-exterior.py` and queued `fc-plane-sling2-exterior-v10.py` have SHA-256
`1a0747181cf824794f5c54c9d3afbef73bd1cb672254b7cb5c5dd748bd4c74ee`.
The installed `docs/exterior-blender-validation.json` records revision
`v10-smooth-canopy-attached-latch`, with **102,411 / 19,023 / 4,837 triangles**.
The pack is format **3**, version **0.3.0**, with `canopy_slide` translating on body axis
`[-1, 0, 0]` through the unchanged **1.10 m** estimated travel.

Every checked surface-mounted hardware vertex is within **2.507 mm** of its actual exported
glass triangles (3 mm limit). The conservative continuous canopy/turtledeck separation is
**23.648 / 23.097 / 24.575 mm** at LOD0/1/2. The original V9 and accepted V10 Blender outputs
remain in their separate queue `.out` folders.

Flight lead runs the queued V10 source in Blender 5.2.0 LTS, offline, with only its output folder
writable. Supply a fresh absolute output folder after `--`:

```sh
flatpak run org.blender.Blender -b --python-exit-code 1 --python /home/ray/builds/codex-jobs/blender-queue/fc-plane-sling2-exterior-v10.py -- /home/ray/builds/codex-jobs/blender-queue/fc-plane-sling2-exterior-v10.out
```

The job uses four CPU render threads and writes three GLBs, six 4096² baked textures, the source
`.blend`, nine Cycles views (seven closed plus beauty/side open), exact cameras, interior and
dimension receipts, per-node triangle budgets, clearance measurements, hardware distances, and
the executed source SHA-256. No external images or source POH pages are embedded or distributed.

Every GLB must retain the 120k/25k/5k limits and full-travel canopy/turtledeck clearance. Every
vertex of surface-mounted canopy hardware is fitted to that LOD's actual glass triangles and
checked within 3 mm after export; new unchecked moving hardware fails validation. The fixed
inside latch is mounted to the roll-over bar, while rails/runners belong to the mechanism.
V10 uses one Bezier meridian for both pieces, with a shared seam/tangent and no height clamping.
The outside handle is flush at canopy centre-top, supported by a moving crown frame strip.
Travel remains the original 1.10 m estimate.

The engine's `scripts/finalize-sling-exterior.py` completed the installation and proof capture
synchronously. All three actual-pack proof tests passed: isolated canopy motion at every LOD,
nine matched camera/pose renders, and the 68-frame motion proof with eight canopy poses in its
sixth row. Captures used the actual PBR renderer on Vulkan llvmpipe (Mesa 26.0.8).
The engine open beauty/side views and contact sheet were visually inspected.

Queue artifacts under `~/builds/codex-jobs/blender-queue/` are `fc-plane-engine-v10/` (nine PNGs
and exact cameras), `fc-plane-v10-comparison.html` (nine Cycles/engine pairs), and
`fc-plane-v10-proof.json` (status `installed_and_captured`, no pending steps, source/asset/image
hashes and validation receipts). Separate `fc-plane-v10-engine-changed-files.txt` and
`fc-plane-v10-pack-changed-files.txt`, plus combined `fc-plane-v10-changed-files.txt`, list the
uncommitted changes. The 68 motion PNGs, manifest and `contact-sheet.png` are in the engine's
`out/plane/motion/`. Queue wrapper `fc-plane-v10-engine-proof.sh` repeats the synchronous run.
Both repositories remain uncommitted for flight lead's merge. Do not run the legacy generator afterward.

V1's six bakes completed successfully in Blender 5.2.0 LTS, but its 122,714-triangle GLB failed
the unchanged 120,000-triangle gate. V2 reduced brake-line and stitching tube sections/samples,
tie-downs, belts, sticks, throttle, tire tori (32 × 8), hubs, hidden intake recesses, and concealed
floor/console bevels. V2 completed in Blender 5.2.0 LTS: 113,962 triangles at LOD0, all three
LODs, all six bakes, and five Cycles stills. The 120k/25k/5k acceptance limits remain unchanged.
V3 exported 116,084 LOD0 triangles and 20,874 LOD1 triangles, and completed all six bakes.
LOD0 and LOD1 passed containment, but LOD2 decimation moved a floor vertex aft to -3.0454545 m
and failed the cockpit station gate. No V3 Cycles renders were produced.

V4 shortens the seating floor to body X [-2.70, -1.45] m (1.25 m long), ending at the front
baggage retaining wall immediately behind the modeled seat backs. POH 7.6/7.9 describes baggage
behind the seats; these body stations are independent layout estimates, not published cabin
dimensions. A thin retaining wall marks that boundary. The small floor and wall meshes retain
their geometry and UVs across LODs so aggressive quadric decimation cannot move them beyond
their authored bounds. The global station limits are unchanged; floor vertices additionally
must remain within the seating floor's explicit fore/aft extent. V4 passed all bakes, containment checks, and three LOD exports: 116,128 / 20,956 / 3,663 triangles.
It then failed at render setup because Blender 5.2 no longer accepts the NISHITA sky enum.

V4 removes the registration background rectangle. The navy marks now sit above the uninterrupted
sweeps directly on the skin. Original vector outlines use straight strokes and circular arcs:
30 cm height, 20 cm width (the digit 1 is naturally narrower), 5 cm uniform stroke, and 5 cm
spacing. A 4×4 coverage rasterizer antialiases the outlines into the projected source masks,
which then bake into the 4096² base-color atlas. No bitmap glyphs, font files, tracing, or floating
letter geometry are used. Both sides bake the configured registration; V5 defaults to N371FC.

V5 uses Blender 5.x's `MULTIPLE_SCATTERING` sky. Its sun elevation is 28°, rotation 295°,
angular size 0.53°, and intensity 1. The world sun disk is disabled because the matched separate
SUN supplies direct light. Sky-node configuration runs before modeling and baking to catch API
incompatibilities early. V5 uses the pack's b982418 default N371FC, adding original 7, F, and open
elliptical-arc C glyphs. No geometry allocation or acceptance budgets change from V4. V5 ran cleanly after flight lead corrected `dust_density` to Blender 5.2's `aerosol_density`;
all five Cycles stills and three LODs completed. The checked-in source preserves that correction.

V6-airframe supersedes the earlier, immutable `v6.py` and `v6-final.py` jobs. Its Blender
run completed all bakes and exported 108,152 / 19,518 / 3,279 triangles. LOD0 and LOD1 passed
the POH bounds gate, but LOD2 measured 2.554286 m tall and failed before any Cycles stills.
Binary inspection identifies the lower extremum as `prop_blur`, not the antenna or fin:
QEM collapsed its 64-triangle coplanar fan to one triangle with body Z +0.950601 m,
beyond its authored +0.735 m edge. The beacon also moved upward by 3.7 mm, and the
20-triangle exhaust and boarding support vanished after tangent failures.

V7 retains the V6 paint and seven cameras and corrects the remaining raised-spinner
mismatch: body Z -0.06 m now equals the blunt front cowl section's vertical midpoint.
The cowl top still slopes gently down toward the nose; its lower edge tapers straight
from the flat cabin belly to the front opening. The 1.79 m blur disc clears the ground
by 15 mm in the neutral proof attitude. Other V6 airframe contours remain unchanged.
Per-object LOD reduction:

- Preserve the blur fan, beacon, exhaust, and boarding support in both reduced LODs,
  alongside the already protected cabin floor and baggage wall. Check their exported
  triangle counts against LOD0 so an omitted mesh cannot silently pass.
- Use ratio 0.18 for tires and wingtips at both reduced LODs; other reducible objects
  retain 0.18 / 0.029. All original triangle limits remain unchanged.
- Compare all six exported outer bounds to LOD0 within 5 mm, in addition to the unchanged
  1% POH dimension gate. Report each extremum's mesh name in validation and failure output.
  No scaling or post-export vertex adjustment is used to pass a gate.

V7 completed all seven renders and three LODs (108,120 / 19,785 / 4,142 triangles).
All POH dimension and cross-LOD extremum gates passed. Ray approved its overall profile.

V8 retains the approved fuselage, canopy, tail, stripe, lettering, and seven cameras:

- Replace tubular wing-root trim with a smooth saddle projected onto the closed fuselage
  envelope and blending into the upper airfoil, ending before the moving flap hinge.
- Remove the oversized wing/flap/tip bevels. All neutral wing and flap surfaces use one
  analytic section with a rounded nose and a 0.7 mm trailing edge; no separate flap drop.
- Keep the red/green navigation bindings at the tips, using smaller seated lenses. The large
  red disc in V7 side elevation was the wingtip projected over the root, not a fuel cap.
  Actual filler caps are flush 84 mm aluminium patches with metallic/roughness detail.
- Main leg fairings taper from 34 to 20 cm chord and sweep 48 cm aft into the existing pants.
  Retain more gear and fillet samples in distant LODs. Wheel track and bindings stay intact.
- Replace the near-black walk with a mid-grey non-slip strip, with fine colour, roughness,
  and normal grain. All six maps must be rebuilt.

V8 completed in Blender 5.2.0 LTS and was accepted for integration. The installed receipt
`docs/exterior-blender-validation.json` records the Blender version, source SHA-256, geometry
revision, per-LOD GLB hashes/bounds/counts, and containment results. `docs/exterior-cameras.json`
retains the exact seven-view manifest. Fresh regeneration must rebuild every atlas and rerun
the same gates before using the installer below.
The shape constraints in V7 are:

- Rounded-rectangle cross-sections (superellipse exponent 3.5) replace the elliptical tube.
  Explicit top/bottom station heights give the cabin a flat deck and belly, a nearly straight
  descending turtledeck, and a straight rising tailcone belly. The cowl stays full-depth until
  its short rounded front. The spinner axis is centered at body Z -0.06 m in the blunt front
  cowl section, and the cowl top descends toward it.
- A broad canopy arch loft sits on the flat deck. Its rear is closed by a fairly upright cap
  and frame bow. The Boolean cockpit opening follows that footprint; the existing strict
  interior hull/rail/station gates are retained.
- The wing uses a nearly straight leading edge, constant inboard chord, moderately tapered
  outer panels, small rounded/upturned tip fairings, and long inboard flaps. Nominal plan area
  remains 11.845 m², including an allowance for rounded tip corners. The conventional tail
  has straight swept fin edges, a squared tip, low horizontal tail, and a baked trim-tab seam.
- Wide, swept-aft main legs and the nose leg have closed painted oval fairings. Pants retain
  their tire openings and Boolean-unioned leg cuffs. Brake-line meshes are deleted. A rigid
  boarding platform and short straight metal exhaust replace the V5 black curls.
- A single straight teal stripe runs at wing-root height; navy N371FC sits above it. Both
  bowls of the 3 are rounded arcs. The 30 cm marks still bake into the base-color atlas.
- Five original body-frame camera poses are retained, plus `elevation-side` and `plan-top`.
  Both new cameras are orthographic: horizontal field widths 8.0 m and 12.4 m, respectively.
  Their metadata records `ortho_width_m`; perspective views record vertical FOV. The side
  view checks 6.675 m length and 2.45 m height, and the top checks 9.165 m span. Exported
  bounds and station tables are recorded in `orthographic-dimensions.json` after the 1% gates.
- A proper 180° X rotation maps Blender to body coordinates (`x,-y,-z`). This fixes the old
  reflection that mirrored geometry/lettering between Cycles and the real renderer. Normals
  and tangent XYZ rotate; winding and tangent handedness stay intact. Image masks use each
  physical side's reading direction; a raw body-X source mask may read backward in isolation.

Shape observations came only from flight lead's written description of the type. No photograph,
handbook drawing, mesh, font, or external texture was supplied to or used by this generator.

V4 retains V3's changes for the reviewed panel protrusion, hanging pitot and brake lines, missing paint,
weak surface detail, indoor lighting, and detached-looking wheel fairings:

- Cabin parts are resized and lowered. Every interior mesh vertex, including stitches and
  display bezels, must lie at least 3 mm inside the closed, uncut fuselage envelope, below the
  canopy rail with 5 mm clearance, and inside cockpit station limits. The gate runs before
  baking and after LOD decimation. Violations include the part, body coordinates, and reason.
- The 22 cm forward-facing pitot has a 10 cm drop, with its mount ray-projected onto the actual
  wing underside. V6 deletes all brake-line meshes; plumbing is concealed. Teardrop pants have rounded
  tire openings and Boolean-unioned cuffs where the painted gear legs enter them.
- Two original body-coordinate paint masks shade the fuselage directly during baking.
  The straight teal accent and continuous 30 cm N371FC characters become base-color atlas texels;
  no floating paint or registration strips remain. The named registration binding remains.
- Wing/flap/aileron, stabilizer/elevator, and fin/rudder boundaries have physical gaps. Cowl
  and access seams, filler-cap rings, and skin-projected painted rivet heads contribute to the
  normal bake. A worn left-root wing walk contributes color, normal, and roughness detail.
  Baked AO is limited to a subtle 22% cavity contribution and is exported separately.

All six bakes must be regenerated at 4096². Do not reuse earlier maps or GLBs.

V5 preserves flight lead's `export_image_format='AUTO'` fix for Blender 5.2. Sources remain PNG,
and the exported-image gate still requires embedded PNGs. Materials reuse their node trees;
the deprecated `use_nodes` switch is only a compatibility fallback when a node tree is absent.
The high-poly source retains its n-gon topology for subdivision. Game meshes are triangulated
before normal baking and export, and LOD copies after decimation, to fix v1's missing-tangent
export warnings. Normal-mapped exported primitives must contain tangents and UVs or fail review.
UV packing changes with the new detail allocation, so rerun all six bakes rather than reuse v1 maps.

The script validates each GLB before rendering: the same required motion/light/registration names,
128 nodes, 120k/25k/5k triangles, dimensions within 1% of POH SI facts, embedded PNG dimensions,
and a 64 MiB file cap. It applies the proper Blender/body rotation to positions, normals, tangent XYZ,
accessor bounds, and node translations, preserving winding and tangent handedness. Original registration
masks use no external font. All contours are modeling estimates; dimensional agreement is not
proof of shape fidelity. The paint scheme is original, with no manufacturer markings.

```sh
python3 scripts/test-blender-exterior.py
python3 scripts/blender-exterior.py /path/to/output --validate-only
```

Return the complete Blender log, `validation.json`, `cameras.json`, and all seven stills before
promoting the outputs. A failed acceptance check should be fixed in the generator, not bypassed.
The camera file records body-frame eye/target/up, projection, vertical FOV or orthographic width, and image size for exact engine proof
captures. These are exterior review views, distinct from the legacy scene director test, whose
cockpit view deliberately omits the exterior. Engine comparisons must use these exact cameras,
with body reference coordinates converted relative to the loaded CG, a stationary propeller, neutral controls, the same ground attitude, and matched exposure.

The uncommitted engine integration includes a bounded embedded-PNG/PBR loader, optional LOD2,
PBR material/normal/AO/emissive shading, sorted canopy blending, and a scenery-fed sky-probe
interface with a procedural fallback. `Scene::set_registration` retains main f066ed5's API
and caching/reset behavior; a declared `registration.surface` selects base-color atlas painting
for all three LODs, while legacy geometry lettering retains its original path. Main's existing
UI call continues to supply the saved user override. Other texture channels remain immutable.
Flight lead owns the rebase onto main `460784d` (Rust 1.98, scenery/city providers, and web
packaging). Git metadata is read-only in this worktree. Keep main's scene,
scenery, callsign persistence, and UI plumbing when resolving the overlap; these changes add
PBR, the atlas branch in `registration::paint`, and optional LOD2, without replacing those paths.

Flight lead real-window shots after integration: beauty/front-left three-quarter in daylight;
left and right registration at taxi distance; canopy close-up with seats, two displays, and sticks;
head-on view of cowl inlets and stopped blades; rear-quarter tail/control-surface view; taxi with
nose steering and wheel rotation; flaps/elevator/aileron/rudder deflected; night nav/strobe/landing
lights on and off; distant LOD transitions. Use the camera manifest for the seven exterior review
views. Capture desktop and browser at 1600 × 1000.

After the matched engine captures exist, make the self-contained proof page with:

```sh
python3 scripts/compare-exterior.py /path/to/cycles-output /path/to/engine-output /path/to/comparison.html
```

Both folders must contain identical `cameras.json` files. The engine images must be named
`engine-<camera-label>.png`; the tool refuses different camera metadata or image dimensions.
It embeds the original PNG bytes without editing or resampling them.

After the V8 Blender gates pass, install its GLBs,
standalone PNG sets, LOD2 declaration, and registration-paint surface with:

```sh
python3 scripts/install-blender-exterior.py /path/to/fc-plane-sling2-exterior-v8.out
```

The installer validates all outputs before replacing assets. The installer losslessly extracts one shared PNG set under `textures/exterior/` and lists it in
`exterior.textures`; standalone bake channels remain in the confined output for review. Distant
LODs use smaller filtered upload levels without extra texture files. The old procedural
generator remains unchanged for reproducing earlier pack revisions. Runtime overrides erase
and repaint only the specified white tail patch in the base-color atlas; other PBR channels
and the original default atlas remain intact. Clean paint samples from the same declared
patch calibrate the erase colour against the actual bake, avoiding a visible rectangle when
the source material colour and baked colour differ.

Runtime registration verification uses the installed GLBs, through the same scene API as main:

```sh
export CARGO_TARGET_DIR="$HOME/builds/cargo-target/flightcraft/fc-plane"
export PKG_CONFIG_PATH="$HOME/builds/pkgconfig-shim"
export FLIGHTCRAFT_SLING_PACK="$HOME/builds/worktrees/sling-exterior"
cargo +1.98.0 test --offline -j 4 -p flightcraft-render sling_baked_registration -- --ignored --nocapture
```

The test checks both sides at all LODs: old baked ink is cleared, new ink appears, geometry
and other texture channels are unchanged, and reset restores the immutable original. For
additional visual captures, set `FLIGHTCRAFT_PROOF_REGISTRATION=N824RX` and use a separate
`FLIGHTCRAFT_EXTERIOR_PROOF` directory with the matched-camera engine test. Leave the variable
unset for the normal Cycles comparison. V7 diagnostics remain historical preflight evidence;
the V8 captures described below use the installed accepted assets.

## Installed V8 proof

The engine offscreen run uses the installed pack and the actual PBR loader, renderer, posing,
texture upload, and sorted glass path, with Vulkan llvmpipe and WebGL2 device limits. All seven
frames are 1600 × 1000; `cameras.json` is byte-identical between Cycles and engine outputs.
The default and N824RX runs retain neutral controls and a stopped propeller.

Artifacts (outside the pack, under `~/builds/codex-jobs/blender-queue/`):

- `fc-plane-v8-comparison.html`: all seven unchanged Cycles/engine pairs side by side.
- `fc-plane-engine-v8/`: the seven default N371FC engine PNGs and camera manifest.
- `fc-plane-engine-v8-registration/`: the seven N824RX engine PNGs and camera manifest.

Repeat the engine proof from the `fc-plane` engine worktree:

```sh
export CARGO_TARGET_DIR="$HOME/builds/cargo-target/flightcraft/fc-plane"
export CARGO_BUILD_JOBS=4
export PKG_CONFIG_PATH="$HOME/builds/pkgconfig-shim"
export FLIGHTCRAFT_SLING_PACK="$HOME/builds/worktrees/sling-exterior"
export FLIGHTCRAFT_CYCLES_OUTPUT="$HOME/builds/codex-jobs/blender-queue/fc-plane-sling2-exterior-v8.out"
export FLIGHTCRAFT_EXTERIOR_PROOF="$HOME/builds/codex-jobs/blender-queue/fc-plane-engine-v8"
cargo +1.98.0 test --offline -j 4 -p flightcraft-render matched_sling_exterior_cameras -- --ignored --nocapture
```

Then set `FLIGHTCRAFT_PROOF_REGISTRATION=N824RX` and change the proof output to
`fc-plane-engine-v8-registration` to repeat the custom-number capture. Run the pack's
`compare-exterior.py` with the Cycles and default engine output directories to assemble the page.

The pack's Rust harness includes all three GLBs. Physics measurements reuse a cloned aircraft
configuration after one full embedded-pack validation, avoiding repeated 4K atlas decoding;
the native `read_pack`/session-install check still reads and installs the files independently.

The actual-GLB registration test passed on both sides at all three LODs: it checks erased baked N371FC ink,
visible N824RX ink, unchanged geometry and other PBR channels, and reset to the immutable
original atlas. The left side elevation and right rear-quarter renders were also inspected;
N824RX is legible, with no old-number overlap or background rectangle.

The engine direction test checks both actual aileron trailing edges at every LOD of Corvid,
Larrow, and this installed V8: positive right roll raises the right edge and lowers the left,
and negative demand reverses both directions. All existing bindings passed without changes.

The actual V8 motion proof is in the engine worktree at `out/plane/motion/`: 60 unmodified
1280×800 engine PNGs, `contact-sheet.png`, and `manifest.json`. There are twelve-frame
aileron, elevator, and rudder sweeps from full negative to full positive demand; twelve
flap frames from 0% to 100%; two identical 0 RPM frames; eight distinct 300 RPM blade
orientations at 1/120-second intervals; and two 2,000 RPM blur-disc frames. Other controls,
camera, and lighting stay fixed. The camera uses Director Wing's eye, with its aim centred
to retain the tail. The manifest records the exact camera, poses, phases, trailing-edge
positions, visible vertex counts, and pixel changes. Repeat it from the engine with:

```sh
export XDG_RUNTIME_DIR=/tmp/fc-plane-runtime
export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json
cargo +1.98.0 test --offline -j 4 -p flightcraft-render sling_exterior_motion_proof -- --ignored --nocapture
```

The motion proof uses explicit renderer poses; separate unit tests cover simulation inputs
and paused phases. This is an exterior animation proof, rather than a flight manoeuvre.

Visible differences from Cycles: geometry and camera framing match, including the accepted
chunky wing root; the engine proof has no cast shadow and a flat grey apron/background,
where Cycles has a textured blue apron, physical sky, and cast shadows. Procedural reflections
and tone mapping produce different clearcoat highlights and darker side surfaces. Glass uses
sorted alpha/Fresnel rather than Cycles transmission/refraction, so cabin contrast differs.
The single-sample engine edges show more aliasing than Cycles stills.

Unverified here: the main-460784d rebase/combined scenery path, packaged desktop and browser
real-window captures, and performance on a hardware GPU. A wasm build check is compilation
coverage, not a browser visual test. No rebase or commit was performed.

Verified on the installed V8 pack: all 15 Python authoring/export tests, all 68 aero/render
tests (including all-LOD bounds, aileron directions, and nested moving meshes), three ignored
exterior proof tests, the custom-number seven-camera run, and all 10 pack fidelity tests. The pack fidelity run
also exercises native `read_pack`, session installation, and aircraft selection.
Engine aero/render and pack-harness Clippy passed with `-D warnings`; render/control
wasm compilation passed. `cargo deny check licenses` was attempted but unavailable because
`cargo-deny` is not installed. Full workspace CI remains for the flight lead after rebase.

## V9 mechanism revision (historical)

`scripts/blender-exterior.py` now authors V9 from accepted V8; installed binary assets and
`exterior.json` remain V8 until flight lead runs and accepts the queue job. Run
`fc-plane-sling2-exterior-v9.py` in the same confined Blender environment, output to its `.out`
folder, then run `scripts/install-blender-exterior.py OUTPUT`. That installer validates all LODs,
continuous swept canopy/turtledeck clearance and nine stills before installing format 3, the
`canopy_slide` binding, and the `sliding_canopy` capability together. Use the current engine with
format-3 support. Render seven closed views plus fully open beauty and side elevation.
The 1.10 m aft travel is an estimate, recorded in `docs/estimates.md`.

## Pilot-seat revision and shared downloads

Installed geometry remains accepted V10; current authoring source queues V11. The installed maps
are 4096². The GLBs now reference four byte-identical shared PNGs by relative URI, rather than
embedding four copies at each LOD. Total runtime assets shrink from 57,977,784 to 22,648,650 bytes;
see `exterior-storage.json`. Redundant standalone review bakes are removed from the pack.
The engine requires shared-PNG and `interior.pilot_eye_m` support from the fc-cockpit lane.
The declared body-space pilot eye is (-2.30, -0.205, -0.72) m; the renderer subtracts loaded CG.

Run `python3 scripts/share-exterior-textures.py .` to losslessly repack embedded exports; it is
idempotent. Normal regeneration uses `install-blender-exterior.py OUTPUT`, which performs the
same extraction after all Blender acceptance checks. No Blender was executed in the cockpit lane.
The V11 queue job is `~/builds/codex-jobs/blender-queue/fc-cockpit-sling2-interior-v11.py`.
It authors woven seats, matte panel coating, anodized controls, side trim, armrests, pedals, a
throttle grip, and a curved dash and coaming. Source/output validation must complete before install.
The engine's `docs/cockpit-interior.md` gives the offscreen and real-window pilot-seat shot list.
