#!/usr/bin/env python3
"""Write the `preflight` section of systems.json from the Sling 2 POH Rev 2.8 section 4.4 list.

Every handbook item becomes one entry with its reference. Wording is a terse restatement of the
checklist line (facts, not the handbook's prose). Positions are body-frame metres (x forward,
y right, z down) taken from the exterior model: wing and tail extents, the pitot mount, the gear,
and the wing tie-down nodes. Run from the pack root; it rewrites systems.json in place.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
POH = "Sling 2 POH Rev 2.8 (DC-POH-002-X-B-2.8) section 4.4 Pre-flight check"


def mir(p, s):
    """Mirror a point across the centreline: s is +1 right, -1 left."""
    return [p[0], p[1] * s, p[2]]


KEEPOUTS = [
    ("fuselage", [-6.0, -0.55], [0.33, 0.55]),
    ("wing_left", [-2.5, -4.6], [-1.05, -0.55]),
    ("wing_right", [-2.5, 0.55], [-1.05, 4.6]),
    ("tailplane", [-5.8, -1.42], [-4.95, 1.42]),
    ("propeller_disc", [0.3, -0.9], [0.7, 0.9]),
]

# Closed loop around the aircraft, nose first, down the right side, round the tail, up the left.
ROUTE = [
    ("nose", [1.25, 0.0]),
    ("nose_right", [1.0, 1.3]),
    ("right_cowl", [0.05, 1.3]),
    ("right_nose_gear", [-0.55, 0.85]),
    ("right_wing_front_in", [-0.6, 1.9]),
    ("right_wing_front_mid", [-0.6, 3.0]),
    ("right_wing_front_out", [-0.7, 4.0]),
    ("right_tip_front", [-0.7, 4.95]),
    ("right_tip", [-1.8, 4.95]),
    ("right_tip_aft", [-2.95, 4.95]),
    ("right_aileron", [-2.95, 3.6]),
    ("right_flap", [-2.95, 2.0]),
    ("right_gear", [-2.78, 1.3]),
    ("right_aft", [-3.2, 1.0]),
    ("right_fuselage", [-4.2, 1.0]),
    ("tail_right_front", [-4.6, 1.9]),
    ("tail_right", [-6.3, 1.9]),
    ("tail_right_mid", [-6.3, 0.9]),
    ("tail", [-6.3, 0.0]),
    ("tail_left_mid", [-6.3, -0.9]),
    ("tail_left", [-6.3, -1.9]),
    ("tail_left_front", [-4.6, -1.9]),
    ("left_fuselage", [-4.2, -1.0]),
    ("left_cabin", [-3.2, -1.0]),
    ("left_gear", [-2.78, -1.3]),
    ("left_flap", [-2.95, -2.0]),
    ("left_aileron", [-2.95, -3.6]),
    ("left_tip_aft", [-2.95, -4.95]),
    ("left_tip", [-1.8, -4.95]),
    ("left_tip_front", [-0.7, -4.95]),
    ("left_wing_front_out", [-0.7, -4.0]),
    ("left_wing_front_mid", [-0.6, -3.0]),
    ("left_wing_front_in", [-0.6, -1.9]),
    ("left_nose_gear", [-0.55, -0.85]),
    ("left_cowl", [0.05, -1.3]),
    ("nose_left", [1.0, -1.3]),
]

# (id, name, node, ref, camera target, camera eye offset)
STATIONS = [
    ("cabin", "Cabin", "left_cabin", "4.4 (1) Cabin", [-2.3, -0.2, -0.2], [-1.6, -3.4, -1.9]),
    ("fuselage", "Fuselage", "left_fuselage", "4.4 (2) Fuselage", [-3.0, -0.5, -0.2], [-1.5, -4.4, -1.9]),
    ("empennage", "Empennage", "tail", "4.4 (3) Empennage", [-5.6, 0.0, -0.3], [-3.4, -3.0, -1.7]),
    ("right_wing", "Right wing and main gear", "right_gear", "4.4 (4) Right wing and main gear",
     [-1.9, 2.4, 0.3], [2.4, 3.4, -1.8]),
    ("nose", "Nose section and nose gear", "nose", "4.4 (5) Nose section and nose gear",
     [0.1, 0.0, 0.2], [2.6, -2.3, -1.5]),
    ("left_wing", "Left wing", "left_gear", "4.4 (6) Left wing", [-1.9, -2.4, 0.3], [2.4, -3.4, -1.8]),
]

LOOK, TOUCH = False, True
ITEMS = []


def add(station, iid, text, ref, action, node=None, defects=None, optional=False, warning=None):
    item = {"id": iid, "station": station, "text": text, "poh_ref": ref, "action": action}
    if node:
        item["node"] = node
    if optional:
        item["optional"] = True
    if warning:
        item["warning"] = warning
    if defects:
        item["defects"] = defects
    ITEMS.append(item)


def inspect(target, crouch=False, touch=False):
    return {"kind": "inspect", "target_m": target, "stance": "crouch" if crouch else "stand", "touch": touch}


def cabin(effect, target):
    return {"kind": "cabin", "effect": effect, "target_m": target}


def defect(kind, description, severity, cue):
    return {"kind": kind, "description": description, "severity": severity, "cue_m": cue}


# 1. Cabin ---------------------------------------------------------------------------------------
C = "4.4 (1) Cabin"
add("cabin", "ignition_off", "Magnetos / ignition: off", C, cabin("ignition_off", [-1.85, 0.0, -0.08]))
add("cabin", "master_on", "Master switch: on", C, cabin("master_on", [-1.85, 0.1, -0.05]))
add("cabin", "fuel_indicator", "Fuel level indicator: verify fuel quantity", C, cabin("fuel_indicator", [-1.79, -0.175, -0.15]))
add("cabin", "flaps_full", "Flaps: move to full down position", C, cabin("flaps_full", [-2.04, 0.0, -0.04]))
add("cabin", "master_off", "Master switch: off", C, cabin("master_off", [-1.85, 0.1, -0.05]))
add("cabin", "avionics", "Avionics: verify condition", C, cabin("none", [-1.79, 0.0, -0.15]))
add("cabin", "control_system", "Control system: visual inspection, free movement up to the stops, verify function", C,
    cabin("none", [-1.98, -0.205, -0.25]))
add("cabin", "harnesses", "Safety harnesses: condition, security of attachment, operation of buckles", C,
    cabin("none", [-2.4, -0.205, -0.1]))
add("cabin", "seats", "Seats: security of attachment, adjustment mechanism operates and locks after adjustment", C,
    cabin("none", [-2.28, -0.205, 0.0]))
add("cabin", "canopy", "Canopy: attachment, condition, clean", C, cabin("none", [-2.0, -0.55, -0.45]))
add("cabin", "cockpit", "Cockpit: check for loose objects", C, cabin("none", [-2.2, 0.0, 0.1]))
add("cabin", "fire_extinguisher", "Fire extinguisher: verify present and valid", C, cabin("none", [-2.5, 0.25, 0.05]))
add("cabin", "documentation", "Documentation: verify present and valid", C, cabin("none", [-2.4, 0.3, -0.05]))

# 2. Fuselage ------------------------------------------------------------------------------------
F = "4.4 (2) Fuselage"
add("fuselage", "fuselage_surface", "Surface condition: check", F, inspect([-3.4, -0.5, -0.05]), node="left_cabin")
add("fuselage", "fuselage_cowling", "Cowling attachment: check", F, inspect([0.0, -0.5, -0.08], touch=TOUCH),
    node="left_cowl",
    defects=[defect("loose_cowl_fastener", "A cowling fastener is loose and the cowl lifts at that corner.",
                    "caution", [0.0, -0.5, -0.08])])
add("fuselage", "wing_fuselage_fairings", "Wing/fuselage fairings: check", F, inspect([-2.05, -0.62, 0.0]), node="left_gear")
add("fuselage", "empennage_fairings", "Empennage fairings: check", F, inspect([-4.8, -0.45, -0.15]), node="left_fuselage")
add("fuselage", "antennas", "Antenna/e: check condition and security", F, inspect([-3.78, 0.0, -0.5], touch=LOOK),
    node="left_fuselage")
add("fuselage", "luggage_door", "Luggage compartment door: closed and locked", F, inspect([-2.9, -0.5, -0.15], touch=TOUCH),
    node="left_cabin")

# 3. Empennage -----------------------------------------------------------------------------------
E = "4.4 (3) Empennage"
add("empennage", "tail_rope", "Tie-down rope: removed", E, {"kind": "remove", "props": ["rope_tail"]})
add("empennage", "stabilizers", "Horizontal and vertical stabilizers: check condition", E, inspect([-5.2, 1.3, -0.15]),
    node="tail_right_front")
add("empennage", "elevator", "Elevator and tab: condition and movement", E,
    {"kind": "move_control", "parts": ["elevator_left", "elevator_right"], "target_m": [-5.78, 0.9, -0.14], "amplitude": 0.8},
    node="tail_right_mid")
add("empennage", "rudder", "Rudder: condition and movement", E,
    {"kind": "move_control", "parts": ["rudder"], "target_m": [-5.92, 0.0, -0.7], "amplitude": 0.8})
add("empennage", "empennage_hinges", "Hinges, control horns, bolts, pushrod: condition and secure", E,
    inspect([-5.5, 0.0, -0.15], touch=TOUCH))
add("empennage", "tail_strobe", "Strobe light: condition", E, inspect([-5.93, 0.0, -0.15]))


# 4 and 6. Wings ---------------------------------------------------------------------------------
def wing(station, s, ref, side):
    p = f"{side}_"
    n = side
    gear_y = 0.975 * s
    add(station, f"wheel_fairing_{n}", "Wheel fairing: security, cracks", ref, inspect(mir([-1.96, 1.03, 0.42], s), crouch=True, touch=TOUCH),
        node=f"{n}_gear",
        defects=[defect("wheel_fairing_crack", "A crack runs across the wheel fairing near its lower edge.", "caution",
                        mir([-1.9, 1.05, 0.5], s))])
    add(station, f"wheel_brakes_{n}", "Wheel and brakes: fluid leaks, security, general condition, tyre condition, inflation and wear",
        ref, inspect(mir([-2.0, 1.05, 0.66], s), crouch=True, touch=TOUCH), node=f"{n}_gear",
        defects=[defect("damaged_tyre", "The tyre has a cut through the tread and the cord is showing.", "no_go",
                        mir([-1.96, 1.05, 0.75], s))])
    add(station, f"wheel_strut_{n}", "Wheel strut: condition, cracks", ref, inspect(mir([-1.9, 0.92, 0.3], s), crouch=True, touch=TOUCH),
        node=f"{n}_gear")
    add(station, f"leading_edge_{n}", "Leading edge: check condition", ref, inspect(mir([-1.05, 2.2, 0.1], s), touch=TOUCH),
        node=f"{n}_wing_front_in")
    add(station, f"lights_{n}", "Taxi / landing lights and lens: check for cracks and condition", ref,
        inspect(mir([-1.1, 2.8, 0.03], s)), node=f"{n}_wing_front_mid")
    add(station, f"fuel_vent_{n}", "Fuel vent (underside of wing): unobstructed", ref,
        inspect(mir([-1.5, 2.0, 0.17], s), crouch=True), node=f"{n}_wing_front_in")
    add(station, f"trailing_edge_{n}", "Wing trailing edge: check condition", ref, inspect(mir([-2.4, 3.0, 0.05], s), touch=TOUCH),
        node=f"{n}_aileron")
    add(station, f"aileron_{n}", "Aileron: freedom of movement, attachment, surface condition", ref,
        {"kind": "move_control", "parts": [f"aileron_{'right' if s > 0 else 'left'}"],
         "target_m": mir([-2.39, 3.6, 0.0], s), "amplitude": 0.8}, node=f"{n}_aileron")
    add(station, f"aileron_hinges_{n}", "Aileron hinges, control horn, bolts, pushrod: secure, condition", ref,
        inspect(mir([-2.1, 3.6, 0.1], s), crouch=True, touch=TOUCH), node=f"{n}_aileron",
        defects=[defect("aileron_hardware_missing", "An aileron hinge bolt is missing; the hinge has no retaining hardware.",
                        "no_go", mir([-2.1, 3.6, 0.1], s))])
    add(station, f"flap_hinges_{n}", "Flap hinges, control horn, bolts, pushrod: secure, condition", ref,
        {"kind": "move_control", "parts": [f"flaps_{'right' if s > 0 else 'left'}"],
         "target_m": mir([-2.48, 1.7, 0.22], s), "amplitude": 0.5}, node=f"{n}_flap",
        defects=[defect("flap_hardware_missing", "A flap hinge nut is missing and the hinge pin is working out.",
                        "no_go", mir([-2.3, 1.7, 0.2], s))])
    add(station, f"wing_tip_{n}", "Wing tip: check condition", ref, inspect(mir([-1.65, 4.5, -0.1], s), touch=TOUCH),
        node=f"{n}_tip")
    add(station, f"nav_lights_{n}", "Strobe / nav light and lens: check for cracks and condition", ref,
        inspect(mir([-1.35, 4.53, -0.2], s)), node=f"{n}_tip")
    if station == "left_wing":
        add(station, "pitot", "Pitot tube: security, unobstructed, remove cover", ref,
            {"kind": "remove", "props": ["pitot_cover"]}, node="left_wing_front_in")
    warn = ("Verify the fuel level physically before each take-off for the planned flight. Fuel can just be seen "
            "covering the whole bottom of the tank, through the filler cap, with 30 litres present.")
    add(station, f"fuel_level_{n}", "Fuel level: verify physically before each take-off (warning)", ref + " warning",
        {"kind": "fuel_cap", "tank": n}, node=f"{n}_wing_front_in", warning=warn,
        defects=[defect("low_fuel", "The tank holds only about 30 litres: fuel just covers the bottom of the tank.",
                        "no_go", mir([-1.45, 1.9, 0.02], s))])


wing("right_wing", 1, "4.4 (4) Right wing and main gear", "right")

# 5. Nose ----------------------------------------------------------------------------------------
N = "4.4 (5) Nose section and nose gear"
add("nose", "nose_cowling", "Engine cowling condition: check", N, inspect([0.2, 0.0, -0.05], touch=TOUCH),
    defects=[defect("loose_cowl_fastener", "A cowling fastener is loose and the cowl lifts at that corner.", "caution",
                    [0.15, 0.2, -0.12])])
add("nose", "propeller_spinner", "Propeller and spinner condition: check", N, inspect([0.55, 0.0, -0.06]))
add("nose", "air_intakes", "Air intakes: check", N, inspect([0.19, 0.3, -0.08]), node="right_cowl")
add("nose", "radiators", "Radiators: check", N, inspect([0.1, -0.3, 0.1]), node="left_cowl")
add("nose", "engine_mount_exhaust", "Engine mount and exhaust manifold condition: check", N, inspect([-0.4, -0.4, 0.3], crouch=True),
    node="left_cowl")
add("nose", "oil_coolant", "Oil and coolant quantity check", N, {"kind": "oil_check", "target_m": [0.0, 0.4, -0.25]},
    node="right_cowl",
    defects=[defect("low_oil", "The oil level is below the MIN mark on the dipstick.", "no_go", [0.0, 0.4, -0.25])])
add("nose", "fuel_electrical", "Visual inspection of fuel and electrical system: check", N, inspect([-0.1, 0.4, -0.05]),
    node="right_cowl")
add("nose", "engine_checks", "Engine checks as per the Rotax manual: complete", N, inspect([0.0, 0.4, -0.1]),
    node="right_cowl")
add("nose", "engine_manual", "Other actions according to the engine manual", N, inspect([0.0, 0.4, -0.1]),
    node="right_cowl", optional=True)
add("nose", "parachute_cover", "Parachute cover, if fitted: check sealed and secure", N, inspect([-3.0, 0.0, -0.45]),
    node="left_cabin", optional=True)
add("nose", "nose_tyre", "Tyre: condition, inflation, wear", N, inspect([-0.46, 0.15, 0.72], crouch=True, touch=TOUCH),
    node="right_nose_gear",
    defects=[defect("damaged_tyre", "The tyre is worn through on one shoulder; the cord is showing.", "no_go",
                    [-0.46, 0.17, 0.74])])
add("nose", "nose_wheel", "Wheels: security, general condition", N, inspect([-0.46, 0.15, 0.62], crouch=True, touch=TOUCH),
    node="right_nose_gear")
add("nose", "chocks_ropes", "Chocks and tie-down ropes: remove", N,
    {"kind": "remove", "props": ["chock_nose_fore", "chock_nose_aft", "rope_wing_right", "chock_main_right",
                                 "rope_wing_left", "chock_main_left"]})
add("nose", "suspension", "Suspension and undercarriage: check and test", N, inspect([-0.46, 0.0, 0.3], crouch=True, touch=TOUCH),
    node="right_nose_gear")
add("nose", "propeller_turn",
    "Long-term parking: turn the engine over several times by hand on the propeller, ignition off, palm on the blade",
    N + " caution", {"kind": "palm_prop", "target_m": [0.4, 0.72, -0.06]}, node="right_cowl", optional=True,
    warning="Ignition and magnetos off. Handle the blade area with the palm of the hand, never only the fingertips on the blade edge.")

wing("left_wing", -1, "4.4 (6) Left wing", "left")

# Props ------------------------------------------------------------------------------------------
PROPS = [
    ("rope_tail", "tie_down_rope", [-5.85, 0.0, 0.3], 0.0, "tail"),
    ("pitot_cover", "pitot_cover", [-1.3, -2.45, 0.16], 0.0, "left_wing_front_in"),
    ("chock_nose_fore", "chock", [-0.13, 0.0, 0.8], 0.0, "right_nose_gear"),
    ("chock_nose_aft", "chock", [-0.8, 0.0, 0.8], 0.0, "right_nose_gear"),
    ("rope_wing_right", "tie_down_rope", [-2.1, 2.97, 0.45], 0.0, "right_aileron"),
    ("chock_main_right", "chock", [-2.3, 0.975, 0.8], 0.0, "right_gear"),
    ("rope_wing_left", "tie_down_rope", [-2.1, -2.97, 0.45], 0.0, "left_aileron"),
    ("chock_main_left", "chock", [-2.3, -0.975, 0.8], 0.0, "left_gear"),
]

doc = {
    "version": 1,
    "source": POH,
    "pace_mps": 1.3,
    "seat_m": [-2.3, -0.205, -0.05],
    "keepouts": [{"id": i, "min_m": a, "max_m": b} for i, a, b in KEEPOUTS],
    "route": [{"id": i, "position_m": p} for i, p in ROUTE],
    "stations": [
        {"id": i, "name": nm, "node": nd, "poh_ref": r, "camera": {"target_m": t, "eye_offset_m": o}}
        for i, nm, nd, r, t, o in STATIONS
    ],
    "items": ITEMS,
    "props": [
        {"id": i, "kind": k, "position_m": p, "yaw_rad": y, "node": nd, "present_at_start": True}
        for i, k, p, y, nd in PROPS
    ],
    "fuel": {
        "density_kg_per_l": 0.72,
        "covers_bottom_l": 30.0,
        "caps": [
            {"tank": "left", "cap_m": [-1.45, -1.9, 0.02]},
            {"tank": "right", "cap_m": [-1.45, 1.9, 0.02]},
        ],
    },
}

path = ROOT / "systems.json"
systems = json.loads(path.read_text())
systems["preflight"] = doc
path.write_text(json.dumps(systems, indent=2) + "\n")
print(f"{len(ITEMS)} items, {len(PROPS)} props, {len(ROUTE)} route nodes")
