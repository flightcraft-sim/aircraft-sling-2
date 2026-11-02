# Sling 2

A clean-room FlightCraft aircraft pack for the Sling 2 with a Rotax 912 iS and an advanced IFR two-display panel. **Not affiliated with or endorsed by Sling Aircraft.** Original files are Apache-2.0. This is simulation software, not flight-planning or training material.

Both touch displays start on the integrated PFD page, with engine strips, synthetic vision, a lower-left map, and a lower-right terrain inset. A centre navigator, digital autopilot with flight director, electronic standby, electronic engine lanes, independent fuel pumps, key start, breakers, annunciators, and recovery parachute use the engine's existing equipment. The measured panel uses original FlightCraft screen artwork and no manufacturer logos.

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

See [validation](docs/validation.md) for measured results and acceptance conditions, and [panel review](docs/panel-review.md) for the layout comparison. The pack requires FlightCraft main revision `3512ca9` or newer for placed hardware, display composition, backup buses, and private equipment artwork. The review documents separate measured layout accuracy from remaining artistic differences.

## Sources and estimates

Numerical aircraft facts come from **Sling 2 POH Rev 2.8**: sections 1.4, 2.2, 2.7–2.9, 4.2, 5.1–5.4, 6.4–6.5, 7.5, 9.4, 9.4.1, and 9.4.9. Section 5 describes the equal-power baseline engine; section 9.4 explains its performance applicability to the 912 iS. No POH prose, figures, or images are distributed. [Facts](data/poh-facts.json) retain section citations; [numeric provenance](data/sources.json) maps every layer number to its source or estimate.

The [estimate register](docs/estimates.md) covers aerodynamics, inertia, empty CG, dimensional placement, propeller coefficients, reduction ratio, fuel density, electrical and sensor dynamics, recovery dynamics, autopilot settings, panel curves, and default loading. These are simulation assumptions, not measured aircraft characteristics.

The measured hardware arrangement comes from a supplied layout specification. The reference photo remains external to this repository. [Attribution](ATTRIBUTION.md) records data and artwork provenance.

Stable installation identifiers and a separate [skin-slot contract](data/skin-slots.json) reserve a path for private artwork without moving equipment. See [private skins](docs/private-skins.md) for registration and private host integration.
