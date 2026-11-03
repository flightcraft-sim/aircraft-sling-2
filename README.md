# Sling 2

A clean-room FlightCraft aircraft pack for the Sling 2 with a Rotax 912 iS and an advanced IFR two-display panel. **Not affiliated with or endorsed by Sling Aircraft.** Original files are Apache-2.0. This is simulation software, not flight-planning or training material.

Both touch displays start on the integrated PFD page, with engine strips, synthetic vision, a lower-left map, and a lower-right terrain inset. A centre navigator, digital autopilot with flight director, electronic standby, electronic engine lanes, independent fuel pumps, key start, breakers, annunciators, and recovery parachute use the engine's existing equipment. The measured panel uses original FlightCraft screen artwork and no manufacturer logos. Its registration is **N371FC**, with spoken type **Sling**: “Sling Three Seven One Foxtrot Charlie.”

Place this directory immediately inside a packs directory, then launch the desktop application:

```text
flightcraft --packs-dir ./packs
```

Select **Sling 2** (`sling2`) in the aircraft picker. On a static web host, serve this directory with the app, and open:

```text
?pack=packs/aircraft-sling-2/pack.json
```

Absolute HTTPS manifest URLs also work when the server permits CORS. Only the six files listed in `pack.json` are aircraft layers. The Rust harness, provenance ledger, previews, and documentation are development resources.

## Validation

CI resolves the engine dependencies from its Git `main` branch. For a local sibling checkout, prepare the ignored path-dependency manifest:

```sh
python3 scripts/local-manifest.py
cargo fmt --all --manifest-path .local-harness/Cargo.toml
buildq run flightcraft "$PWD" -- cargo test --manifest-path .local-harness/Cargo.toml
buildq run flightcraft "$PWD" -- cargo clippy --manifest-path .local-harness/Cargo.toml --workspace --all-targets -- -D warnings
```

Set `FLIGHTCRAFT_ENGINE` before preparing the manifest when the engine is elsewhere. Hosts that need pkg-config metadata can pass their configuration with Cargo's `--config` option. All local compilation goes through the build queue. Optional actual UI captures use `--features previews --test render -- --ignored`; they require the UI's platform libraries.

See [validation](docs/validation.md) for measured results and acceptance conditions, and [panel review](docs/panel-review.md) for the layout comparison. The pack requires FlightCraft main revision `580e2e0` or newer for its radio identity and audio installation, in addition to placed hardware, display composition, backup buses, and private equipment artwork. The review documents separate measured layout accuracy from remaining artistic differences.

## Sources and estimates

Numerical aircraft facts come from **Sling 2 POH Rev 2.8**: sections 1.4, 2.2, 2.7–2.9, 4.2, 5.1–5.4, 6.4–6.5, 7.5, 9.4, 9.4.1, and 9.4.9. Section 5 describes the equal-power baseline engine; section 9.4 explains its performance applicability to the 912 iS. No POH prose, figures, or images are distributed. [Facts](data/poh-facts.json) retain section citations; [numeric provenance](data/sources.json) maps every layer number to its source or estimate.

The [estimate register](docs/estimates.md) covers aerodynamics, inertia, empty CG, dimensional placement, propeller coefficients, reduction ratio, fuel density, electrical and sensor dynamics, recovery dynamics, autopilot settings, panel curves, and default loading. These are simulation assumptions, not measured aircraft characteristics.

The measured hardware arrangement comes from a supplied layout specification. The reference photo remains external to this repository. [Attribution](ATTRIBUTION.md) records data and artwork provenance.

Audio power and both COM receivers share the navigator’s existing electrical load and NAV/COM breaker. There is no separate audio face. Current main has no pack-selectable navigator Audio page; use the toolbar **Radios** window or `comms.audio_panel` commands until the [missing host hook](docs/panel-review.md#navigator-audio-installation) is available. FAA/NASR frequencies come from the engine’s installed region, rather than a pack-specific station list.

Stable installation identifiers and a separate [skin-slot contract](data/skin-slots.json) reserve a path for private artwork without moving equipment. See [private skins](docs/private-skins.md) for registration and private host integration.


## Original exterior (pack format 2)

The installed exterior is the accepted **V8 Blender revision**, generated with **Blender
5.2.0 LTS** from the original source [`scripts/blender-exterior.py`](scripts/blender-exterior.py).
It includes `exterior.glb`, `exterior-lod1.glb`, and `exterior-lod2.glb`, with
**101,452 / 18,583 / 4,204 triangles**. Each GLB embeds its PBR PNG atlas; the six standalone
4096² maps are retained under `textures/exterior/` for review. `pack.json` and `exterior.json`
declare all three LODs and the runtime registration paint surface. The default **N371FC** is
baked on both sides; the host replaces it in the base-color atlas when a user sets a number,
and restores the original on reset. Motion, steering, wheel, propeller, and light bindings
remain named and independent of the simulation geometry.

See [regeneration and integration](docs/blender-exterior.md) for the confined Blender job,
installer, acceptance gates, and seven matched Cycles/engine camera views. Numerical receipts
and camera metadata are in `docs/exterior-blender-validation.json` and
`docs/exterior-cameras.json`. All three LODs passed the 1% POH dimension gate and the
5 mm cross-LOD extremum gate. The remaining chunky edge-on wing root is accepted for now;
a smoother, thinner root fillet is later visual polish.

This exterior requires the host's embedded-PNG/PBR exterior loader, optional LOD2, sorted glass,
and registration-atlas painter. Those engine changes are supplied by the uncommitted
`fc-plane` worktree; flight lead will rebase them onto main `460784d` (Rust 1.98, scenery/city
providers, and web packaging). That main revision by itself does not include this exterior
integration. The six JSON aircraft layers retain format 2.

Dimensions use Sling 2 POH DC-POH-002-X-B-2.8, January 2026, §1.4 SI facts: 9.165 m span,
6.675 m length, 2.45 m height, 11.845 m² wing area, 1.79 m three-blade propeller diameter,
5° dihedral, 1.375 taper ratio, 2.825 m horizontal tail span, and 1.95 m main-wheel track.
The Blender contours, analytic wing section, cabin, paint, registration glyphs, fairings, and
wear are independent original constructions and modeling estimates. The Blender source uses
numerical POH text and written shape observations, without handbook artwork or photographs.
Flaps rotate about their hinges; Fowler translation is not represented.

The unchanged `scripts/generate-exterior.py` remains for reproducing **older pack revisions**:

```sh
python3 scripts/generate-exterior.py --sling-out /path/to/old-revision-output
```

Keep its output separate from the installed V8 assets. Its older untextured geometry and
geometry lettering are not the current exterior. See the attribution ledger for the separate
legacy provenance.
