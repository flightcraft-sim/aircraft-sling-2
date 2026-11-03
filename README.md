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

The pack now includes `exterior.glb` and `exterior-lod1.glb`, produced by the checked-in
`scripts/generate-exterior.py` using Python's standard library. Rebuild with:

```sh
python3 scripts/generate-exterior.py --sling-out .
```

This requires a FlightCraft host supporting pack manifest format 2 and the material-color GLB
profile. The six JSON layers retain aircraft format 2. Desktop and browser transports load both
GLBs directly from the manifest. The original white, navy, and teal livery carries **N371FC** in
geometry lettering on both fuselage sides, with no manufacturer logos. The model has roughly
22,100 triangles at LOD0 and 3,700 at LOD1, with independent hinged surfaces, steering and rolling
wheels, spring travel, a three-blade propeller and blur disc, and named lighting fixtures.

Dimensions come from Sling 2 POH DC-POH-002-X-B-2.8, January 2026, Section 1.4: span 9.165 m,
overall length 6.675 m, overall height 2.45 m, wing area 11.845 m², and the 1.79 m three-blade
fixed-pitch propeller option. Other numeric facts used are 5° dihedral, 1.375 taper ratio,
2.825 m horizontal tail span, and 1.95 m main-wheel track. Section 7 describes a conventional
elevator, semi-slotted Fowler flaps, and a sliding canopy. The fuselage shares the family's datum;
the host applies the loaded CG offset.

The original analytic shapes were revised after visually inspecting the POH Section 1.3 three-view
figures on pages 1-5 and 1-6: tall swept conventional fin and separate full-height rudder, low wing
with curved tips, sliding canopy rails and rear quarter windows, wheel pants, pitot tube, and
raked dorsal antenna. This is independent modeling from the figures and dimensional facts, with
no copied source artwork. Fine contours and section thickness remain modeling estimates. The
analytic wing is an original approximation, not a digitized NACA 4415 profile. Flaps currently
rotate about their hinges; Fowler translation is not represented. No POH prose, PDF, image, or
manufacturer artwork is included.

Engine tests accept `FLIGHTCRAFT_SLING_PACK=/path/to/this/pack` to add Sling bounds, both LODs,
all moving nodes, and the five offscreen exterior captures. Captures are written to the engine's
`out/exterior-after/`. Flight lead should also take packaged-build cockpit-takeoff, wing-climb,
flyby-cruise, tower-final, and night-lights shots, and review registration from both sides.
