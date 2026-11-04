# Attribution

| Resource | Origin | Use and licence |
|---|---|---|
| Aircraft numerical facts | Sling 2 Pilot Operating Handbook, Rev 2.8; sections listed in `data/poh-facts.json` | Facts only, transcribed into original data structures; no handbook prose, figures, or images redistributed. The handbook remains its publisher's work. |
| Measured hardware arrangement | Supplied dimensional layout specification | Original declarative coordinates and curve construction; Apache-2.0. Reference photography is neither distributed nor embedded. |
| Aerodynamic, mechanical, and operational models | Original dimensional, lifting-line, tail-volume, and energy-balance estimates | Apache-2.0; assumptions listed in `docs/estimates.md`. |
| Panel previews | Rendered from this pack using FlightCraft's original equipment and display artwork | Apache-2.0. No reference-image pixels or manufacturer logos. |
| Preview terrain | Original procedural height field in `tests/render.rs` | Apache-2.0. Invented review scenery; no geographic accuracy is claimed. |
| Engine dependencies and bundled UI font | FlightCraft and its dependency declarations | Permissive upstream licences; these resources are not vendored into this pack. |
| Legacy exterior GLBs, LODs, livery, and registration (older pack revisions) | Original analytic geometry in the retained `scripts/generate-exterior.py` | Apache-2.0; no downloaded mesh, traced image, manufacturer logo, or font asset. Current installed V8 assets come from the Blender source below. |
| Exterior dimensions and construction facts | Sling 2 POH DC-POH-002-X-B-2.8, January 2026, §§1.3–1.4, 7.1, 7.7, 7.11 | Numerical facts; no source artwork distributed. Span, overall length/height, wing area, propeller option, gear track, tail span, dihedral, and taper. Section 1.3 figures visually reviewed in the local PDF; independently constructed contours remain modeling estimates. |
| Blender exterior source, original paint masks, vector registration, interior, wing-walk wear, bake detail, and procedural sky/apron | `scripts/blender-exterior.py`, original parameterized Blender construction, stroke/arc outlines, and coverage rasterizer; Blender's built-in multiple-scattering sky | Apache-2.0 for original construction, masks, and generated assets. No imported mesh, photograph, tracing, logo, font, HDRI, or texture. Installed V8 was generated in confined Blender 5.2.0 LTS, accepted for integration, and passed all seven Cycles views, three LODs, containment, and bounds gates. 101,452 / 18,583 / 4,204 triangles; six 4096² PNG maps. Original saddle fillets, analytic wing sections, broad gear fairings, and surface treatments. |
| Cabin/baggage arrangement | Sling 2 POH DC-POH-002-X-B-2.8 §§7.6, 7.9, text only | Layout facts: baggage immediately behind seats, with a front retaining wall. Cabin stations and contours are independent modeling estimates; no handbook prose or figures redistributed. |
| Blender exterior dimensional constraints | Sling 2 POH DC-POH-002-X-B-2.8 §1.4, SI numerical text only | 9.165 m span, 6.675 m length, 2.45 m height, 11.845 m² area, 1.95 m track, 2.825 m horizontal tail span, 1.47 m vertical span, 5° dihedral, 1.375 taper, and the listed 1.79 m three-blade propeller option. Contours, blade sections, cabin detail, and wear remain independent estimates. No handbook figures used by this generator. |
| Blender exterior shape observations | Flight lead’s written observations relaying Ray’s review, 2026-11-03 | General layout facts only. Original rounded-rectangle stations, profiles, fairings, and canopy construction; no reference photograph was given to this lane, traced, or committed. |

Not affiliated with or endorsed by Sling Aircraft or any engine or avionics manufacturer.

| V9 sliding canopy, fixed windshield/roll-over bar, rails, bows, handles and open-pose proofs | Original procedural artwork; factual mechanism and latch locations from local Sling 2 POH Rev 2.8 §7.7, levelling reference and normal checklists; dimensions in estimate register | Apache-2.0 (original artwork); POH facts only, no source pages distributed |

| V10 continuous canopy crown, conforming frame strips and flush outside latch | Original procedural Bezier and surface-fitted geometry, derived from original V9; dimensions are modelling estimates in docs/estimates.md | Apache-2.0 |

| V11 pilot-seat eye, woven seat material, matte panel coating, anodized controls, side trim, armrests, pedals, and curved dash and coaming (queued source) | Original procedural artwork and modeling estimates; no external images or meshes | Apache-2.0 |
| Shared exterior PNGs | Lossless extraction of original accepted V10 atlas bytes; original bake channels retained only in confined output | Apache-2.0 |
