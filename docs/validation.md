# Validation

The harness loads the distributed manifest and six layer documents through `AircraftCatalog::install_pack`, resolves the aircraft, initializes the engine's `Sim`, and installs its operational systems. It uses public engine APIs and never modifies the engine. Local verification uses engine revision `c581b9d3704ba7157a3fbc0e96651c7962d67381`; CI instead resolves Git `main` on every run.

All performance flights use 700 kg, symmetric occupants and fuel, a valid CG at 1.738071 m aft of datum, standard atmosphere, calm air, and the engine's 120 Hz rigid-body integration. Fuel burn updates mass during flight. The measured results below use the local engine checkout.

| Check | POH target | Measured | Tolerance |
|---|---|---|---|
| Clean stall | 46 KIAS | 45.86 KIAS | ±2 kt |
| Full-flap stall | 42 KIAS | 41.61 KIAS | ±2 kt |
| Vx | 65 KIAS | 65.0 KIAS | ±10% |
| Vy climb, sea level | 700 ft/min | 660.1 ft/min | ±10% |
| Vy climb, 3,000 ft | 500 ft/min | 487.6 ft/min | ±10% |
| Vy climb, 6,000 ft | 420 ft/min | 408.4 ft/min | ±10% |
| Vy climb, 9,000 ft | 330 ft/min | 308.4 ft/min | ±10% |
| Concrete takeoff roll | 140 m | 146.83 m | ±10% |
| Grass takeoff roll | 160 m | 162.45 m | ±10% |
| Concrete landing roll | 90 m | 93.65 m | ±10% |
| Grass landing roll | 90 m | 86.17 m | ±10% |
| Cruise, all 20 settings | Section 5.4 | Every point within 4.8% | ±5% |
| CG longitudinal limits | 1.635–1.808 m aft | Edges accepted; outside rejected | 1e-12 m numerical allowance |
| Maximum takeoff/landing mass | 700 kg | 700 accepted; 700.1 rejected | Exact mass limit |

Stalls are measured during an idle-power deceleration while the pilot holds height, at the first crossing of the model's lift-peak incidence; both flights remain airborne. A full-gross forward-CG stall observation has not been independently established; the coefficients are calibrated to the POH's limiting stall values at the test loading. The underlying engine does not shift the aerodynamic static margin with longitudinal CG.

Climb flights hold 74 KIAS and 5,500 engine RPM using pilot elevator and throttle commands. The lowest start is 30 m above the runway; readings follow 40 simulated seconds, during which altitude changes. Rates therefore represent short climb segments near the stated ISA altitude, not frozen-altitude bench readings. A 55–82 KIAS sweep at seven speeds compares vertical/total speed to locate Vx to approximately 5 kt. The measured IAS must remain within 0.5 kt of the target.

Cruise runs hold altitude with pitch and the specified engine RPM with throttle for 90 simulated seconds. They check speed, RPM, height error, vertical speed, and absence of impact. Targets cover 4,500, 4,800, 5,000, 5,300, and 5,500 RPM at 100, 3,000, 6,000, and 9,000 ft. The POH's KTAS column is the speed comparison; its KIAS facts are retained separately.

Takeoff uses 10° flap, full power, and rotation beginning at the published 40 kt. Roll ends at the first sample with every wheel airborne, with at most two simulation steps of measurement resolution. Landing starts near 15 m on a full-flap final at the published 65 kt threshold speed, flares, applies brakes at first contact, and measures contact-to-stop distance. These are **ground-roll** comparisons; approach path and total 15 m obstacle distance are not acceptance-tested. Concrete and grass use actual engine ground-surface classifications.

Additional tests exercise numeric provenance, stable panel/skin rectangles, CG edges, mass limits, individual and dual lane loss, pump redundancy, breaker interruption, key restart, selector starvation, master warning, and propeller gearing. Existing engine tests cover equipment internals; this harness checks their pack wiring.

## Limits of acceptance

The observed flight targets do not establish a type-accurate aircraft throughout its envelope. Forward-CG stall specificity, 15 m obstacle distances, a full two-compartment baggage model, enforcement of all engine limits, photo-exact hardware, functional backup routing, and private equipment screen skins remain incomplete. See `estimates.md`, `panel-review.md`, and `private-skins.md`. The engine's generic exterior mesh is also used for this unknown aircraft identifier; these previews depict the panel, not a Sling-specific exterior model.

No CI run is claimed until the work is pushed. All local compilation and tests are run through the build queue; formatting runs directly.
