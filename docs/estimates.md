# Estimate register

Numbers absent from the cited POH sections are estimates. `data/sources.json` covers every numerical leaf, including otherwise implicit zeros, positions, and time constants.

| Group | Assumptions |
|---|---|
| Mass | Empty mass is the POH's generic 370 kg. Empty CG at 1.65 m aft, height, and diagonal inertia (430, 610, 900 kg m²) are estimates. Inertia follows a dimensional mass-distribution approximation, not a weighing or pendulum test. |
| Payload | Occupant limits of 130 kg, lateral seat arms ±0.27 m, vertical arms, fuel lateral arms ±1.7 m, and default occupant/fuel masses are estimates. Published longitudinal arms are negated to match body x forward. The minimum mass is the generic empty mass, not a published operating minimum. |
| Baggage | The active variant models the forward 35 kg compartment. The aft 25 kg compartment and its 2.896 m arm are retained as facts but are not simultaneously installed: the engine cannot enforce the shared 35 kg baggage limit across stations. |
| Aerodynamics | Finite-wing lift slope near 5/rad; lift offsets, stall angles, post-stall ordinates, profile drag, induced drag, flap drag and moment, all stability/control/rate derivatives, and high-incidence blending. CL maxima are calibrated to 46/42 kt at 700 kg using L = ½ρV²SCL. The induced factor is a near-elliptic lifting-line estimate. Propeller and drag coefficients are calibrated together; matching selected observations does not establish off-design accuracy. |
| Gear and contact | Heights, suspension stiffness and damping, static fractions, steering travel, gear travel, touchdown/contact limits, hard points, and friction. POH wheel track and section 6.4 longitudinal wheel arms inform the layout. Section 1.4's 1.41 m wheelbase differs from the 1.495 m difference between weighing arms; the latter is used. |
| Propeller | Original fixed-pitch CT/CP curves, minimum-speed solver behaviour, windmill drag area, windmill advance ratio, idle shaft power, density lapse, and 2.43 reduction ratio. The POH supplies the selected 1.79 m diameter and engine power/RPM limits; it does not supply these coefficient tables. Thrust coefficients are fitted to section 5 performance. |
| Fuel | Density 0.72 kg/l converts 150 l total and 4 l unusable into mass. Idle flow and interpolation are estimates; the three non-idle consumption observations are from section 9.4.9. Tanks and sender lag/bias are lumped estimates. |
| Electrical | Battery capacity, voltages, alternator curve, current demands, lane/pump backup capacities, independent bus allocation, and breaker trip dynamics. The pumps have no internal batteries; lane and standby backups are lumped estimates. Breaker ratings visible on the panel are from the supplied measured layout, not the POH. The switched EMS and EFIS backup buses each have an estimated 2 Ah at 12 V. EMS feeds both lanes and pumps; EFIS feeds the two displays, both AHRS loads, air data, navigator, and the EFIS backup load. Their recharge-on-reset model is the host approximation. The landing lights split the estimated 5 A demand into two 2.5 A loads, with an estimated 0.5 s wigwag half-period. The two simulated lamp loads have individual breaker state; the single visible LAND breaker operates the left load. This is not a full dual-generator or shared-breaker wiring simulation. MAIN and BKUP BUS are individual loads rather than aggregate bus contactors. The integrated audio installation and both logical COM receivers share the existing estimated 2 A navigator demand and NAV/COM breaker; this adds no electrical load. They are not modeled as separate physical radio units. The radio service also requires the master and avionics switches, even if the navigator load receives EFIS backup power. |
| Engine operation | Single-lane power fraction, starter time/current, thermal lag/equilibrium, manifold-pressure fraction, and placeholder carburettor parameters unused by injection. Fuel pressure is the midpoint of the published range. The host does not enforce the five-minute takeoff limit, all thermal limits, or the engine negative-g time limit. The default engine-gauge bands are host estimates, not all POH limits. |
| Sensors | Ideal calibrated static position error, alternate-static error, VSI lag, standby backup endurance, and AHRS power allocation. Host sensor noise and alignment use its existing models. |
| Recovery | Hold, deployment delay, inflation, descent speed, and hanging pitch are unmeasured simulation parameters. No POH recovery performance is claimed. |
| Autopilot | Authority, slew, bank/rate/load limits, stability protection, speed protection, and trim behaviour use original host-compatible estimates. No real avionics mode logic is reproduced. |
| Artwork | Uniform reference-frame scale, shell/glare/console interpolation, screw sizes, label sizes, native hardware styles, bezel margins and controls, placed autopilot hit regions, and FlightCraft display composition. The floor selector and console length follow the owner-authorized photo correction. This is original geometry made from measurements, not a traced photograph. |
| Pre-flight walkaround | The inspection list is POH 4.4, with the 30 litre fuel-level warning. Every position (route loop, keep-out rectangles, item targets, prop positions, the camera framings) is read from the exterior model's wing, tail, gear, pitot, and tie-down geometry or is an approximation; the filler cap positions (about 1.9 m out on each wing, 1.45 m aft of the datum), the tail tie-down point, the parachute cover, the fire extinguisher, and the documents are not measured. Walking pace (1.3 m/s) and the seat hip point are simulation choices. The Rotax dipstick method (level between MIN and MAX) is referenced from POH 4.4 (5) and not reproduced from the engine manual. Defect severities (no-go versus caution) are simulator choices; the POH lists none. |
| Preview scenery | The procedural height field, grass surface, runway, and geographic origin in the render harness are invented review scenery. They exercise the real synthetic-vision renderer and do not affect the fidelity flights or describe an actual location. |

The engine's V-speed ordering requires `vs <= vr`. The POH lists rotation at 40 kt, below the clean 46 kt stall. Consequently `variant.v_speeds.vr_mps` contains the published 48 kt **liftoff** speed. The authoritative facts retain both 40 and 48 kt, and the takeoff pilot begins rotation at 40 kt. A separate rotation/liftoff API is needed to display both correctly.

## V9 sliding canopy

POH Rev 2.8 §7.7 establishes a sliding mechanism, access from either side, the inside latch at the top centre of the fixed roll-over bar, and the exterior latch at canopy centre. The levelling reference places sliders on cockpit side skins. Before-takeoff item 16 requires closed and latched; securing item 6 requires closing and locking as necessary. No POH travel dimension is given.

The 1.10 m aft translation, -1.95 m windshield seam, -2.82 m fixed hoop station, rail spacing, bow contours, handles, and 45 mm shell/deck offset are original modelling estimates. Fully open, the front bow reaches -3.05 m, behind seat backs near -2.55 m, permitting entry from either side. Actual exported triangles must pass a continuous full-travel canopy/turtledeck separation bound (>3 mm) at every LOD. This conservative bound includes the whole moving shell and its rear edge, rather than just eight sampled poses.

Opening guards (ground speed ≤2 m/s and airspeed ≤5 m/s), instantaneous command motion, door-open drag/noise mapping, and the original canopy-unlatched advisory procedure text are simulator estimates, not POH limitations or an approved emergency checklist. Its best glide speed (72 KIAS) and glide ratio (10:1) are POH 3.2.

The other emergency entries transcribe POH Section 3 (and supplements 9.2.2 and 9.4.10); every entry carries the POH best glide speed and glide ratio because the pack format requires them, even for ground events. The speed tolerance (5 m/s) is a simulator estimate. The pack format has no emergency checklist phase, so these procedures are `emergencies` entries only, not checklist panel lists.

## V10 crown and attached latch

The single longitudinal cubic Bezier meridian (rear to front, x/half-width/height in metres) is
`[[-3.04,.460,.400],[-2.82,.580,.860],[-1.48,.610,.820],[-1.12,.080,.008]]`.
It replaces the clamped height interpolation and shares both position and tangent through the
windshield/sliding split at x=-1.95 m. These crown and frame contours are original visual estimates.
The 1.10 m aft travel remains unchanged.

The flush U-shaped outside handle is at the sliding shell's longitudinal centre and lateral
centre-top, connected to a slim crown frame strip. Every vertex of the complete outside handle,
crown strip, moving bows/sills and windshield frame is fitted to the actual glazing triangles
at each LOD and must be within 3 mm in the exported GLB. This checks tips and edges as well as
mounts. The handle rests 2.5 mm above the shell; frame strips rest 1 mm above it. These are
modelling estimates, not published latch dimensions. Rails/runners are mechanism hardware;
the fixed inside latch mounts to the roll-over bar, so these are not classified as glass-mounted
hardware. All other moving hardware is required to participate in the distance check.
The continuous canopy/turtledeck sweep and resource/dimension limits remain in force.

## V11 pilot-seat interior estimates (queued)

Pilot eye (-2.30, -0.205, -0.72) m in body axes is an original seating estimate, not a POH dimension.
Side trim, armrests, pedal positions, curved dash and coaming, upholstery weave, and material roughness
are independent visual estimates. Existing V10 canopy seam, 1.10 m travel, and clearance gates stay
in force. V11 has not been run or accepted by the cockpit lane.

## Cockpit flight controls (master, flaps, trim, throttle, brakes)

What the POH (Rev 2.8) fixes, and where each control is. Positions are millimetres on the panel layer.

| Control (element id) | POH | Placement in the pack | Status |
|---|---|---|---|
| Master switch (`master_switch`, rocker) | 7.2 electrical switch table and 7.10 key item 1 "Master switch and starter"; 9.4.7 for the 912 iS (the master only connects the battery to the main bus; the ignition key only runs the starter) | (68, 335), left of the ignition key, at the lower left of the dash | Estimate: the POH figure gives the zone, not a coordinate. |
| Flap selector (`flap_selector`) | 7.2 "four-position rotary knob ... on the instrument panel", positions 0/1/2/3 = 0/10/20/32 degrees; 7.10 item 20; 7.11 | (579, 478), lower dash left of the ballistic chute handle (item 20 sits between the electrical switches and the fuel selector) | Estimate for the coordinate. Detents are the four `flap_stages` of the variant layer. |
| Throttle (`throttle`) | 7.9 item 7 and 7.15: hand lever on the cabin centre console, forward for more power | (552, 740), 46 x 176, the pilot's (left) side of the console top, a fore-and-aft slot with full power at the front | Estimate: the POH does not say where on the console, or the order of the three console controls. Left of the brake lever so it is under the left-seat pilot's left hand. |
| Hand brake lever (`brake_lever`) | 7.4 and 7.9 item 4: hydraulic brake actuated by a lever on the cabin centre console (absent if differential foot brakes are fitted) | (638, 790), 54 x 92, centre of the console top | Estimate for position. |
| Park-brake valve (`park_brake`) | 7.4 and 7.9 item 6: an intercept valve acts as a parking brake by stopping pressure relief | (712, 740), 46 x 70, forward right of the brake lever | Estimate for position. |
| Trim (`pilot_stick`, buttons 1 and 3) | 7.2: dual control sticks; elevator trim is electric, by buttons on the control stick; button 1 is trim down, button 3 trim up, 2 autopilot, 4 not allocated, 5 push to talk (also 7.9 item 3, PTT on the front of the handle); 7.11 | (430, 788), 54 x 70, on the cabin floor left of the console, in front of the pilot's seat | Estimate for position. Buttons 2, 4 and 5 are drawn as in the POH figure but are not wired to the dash. |
| Passenger's stick (`copilot_stick`) | 7.2: dual control sticks | (846, 788), the mirror of the pilot's | Estimate for position. It is the same control as the pilot's (the POH has the trim buttons on "the control stick(s)"), so its trim buttons run the same trim. |
| Centre console and floor (`shell.centre_console`, `shell.floor`) | 7.4 "cabin centre console"; 7.9 cockpit layout figure; 7.2 fuel selector "front of centre console" | The measured console front (to the fuel selector, y = 658) is unchanged. Aft of it the console top widens to x 548 to 782 and runs to y = 930; the floor, 396 to 934 by 646 to 952, carries the two sticks. | Estimate: the POH figure shows the arrangement, not dimensions, and the photograph ends at the console front. Console width and length are about what a 1.2 times photo scale gives for a 1.1 m cabin; they are not measured. The panel layer grew from 745 to 960 mm tall to hold them; no element above y = 658 moved. |

Modelling choices that are not from the POH:

- **Flap and trim indicators are on the PFD, not in the panel.** The POH describes neither as dash hardware (the flap selector is a detented knob and the trim buttons have no gauge, sections 7.2, 7.10 and 7.11), but the G3X Touch can show both on the PFD when the installer configures them (pilot's guide 190-01754-00 Rev. Y, printed page 81). The engine draws them on any landscape touch EFIS whose host supplies the pilot's controls; whether this aircraft's installer enabled them is not stated in the POH, so they are on. The flap scale is labelled 0 to 32 degrees from `deflection_deg` on the variant's `flap_stages`. A hover on the stick still shows the trim value.
- **Park brake.** The valve model is "closed holds full brake pressure with the lever released"; the real valve holds whatever pressure the lever last built. The POH gives no pressure figures.
- **Trim authority and rate.** The engine's trim range of +/-0.3 elevator-equivalent is symmetric; the POH's trim tab travel (8 degrees up, 20 degrees down, +/-5) is not mapped to it. Holding a stick button runs trim at 0.15 of that range per second, as the keyboard binding does.
- **Console region.** Earlier the throttle, brake, valve and stick sat in a row below the measured console outline because there was no room. The console now continues aft of the measured front as a drawn region of the panel, so each control stands on drawn artwork in its POH location (see the table). The measured part of the console, the fuel selector and the dash did not move. The window that shows the region is a plan view with the nose up the page, which is also how the stick's five buttons are drawn from the POH figure.
- **Flap detents.** `variant.json` normalises the stages to 0, 1/3, 2/3 and 1 although the POH's 32 degree last stage would be 0.3125, 0.625, 1; that earlier estimate is unchanged. The indicator is labelled from the POH's degrees (0, 10, 20, 32), not from the normalised positions, so its pointer reads 20 degrees at the third detent and the flight model's flap deflection at that detent is the earlier estimate.
- **COM2 and NAV2.** None. The POH lists one GTR 200 COM radio (6.1, 7.10 item 9) and no second radio or navigation receiver, so the touch displays' radio windows address radio 1 only. The pack's audio-panel installation still lists a second logical COM load (see the panel review); that is a lumped electrical assumption, not a second radio.
