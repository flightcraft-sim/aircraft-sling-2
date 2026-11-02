#!/usr/bin/env python3
"""Record provenance for every numeric leaf in the distributed engine layers."""
import json
from pathlib import Path
root = Path(__file__).resolve().parent.parent

def poh(section):
    return 'Sling 2 POH Rev 2.8, section ' + section

rules = {
    'family.json': {
        '/geometry/wing_area_m2': poh('1.4'), '/geometry/span_m': poh('1.4'),
        '/geometry/chord_m': poh('1.4'),
    },
    'variant.json': {
        '/empty_mass/mass_kg': poh('1.4'), '/max_mass_kg': poh('2.8'),
        '/cg_envelope': poh('2.9') + '; negative body x is aft; lower mass bound is an estimate.',
        '/flap_stages': poh('7.5') + '; normalized 0/10/20/30 degree detents; speed limit from section 2.2.',
        '/fuel_capacity_kg': poh('1.4') + '; estimate: 0.72 kg/l.',
        '/v_speeds': poh('2.2') + '; climb and liftoff speeds from section 4.2. The engine vr field uses 48 kt liftoff because 40 kt rotation violates its speed ordering.',
    },
    'engine.json': {
        '/propulsion/max_power_w': poh('9.4.1'),
        '/propulsion/prop_diameter_m': poh('1.4') + '; selected 1.79 m fixed-pitch option.',
        '/propulsion/max_rpm': poh('9.4.1') + '; estimate: divide engine RPM by 2.43 reduction ratio.',
        '/propulsion/min_rps': poh('9.4.1') + '; estimate: divide idle RPM by 2.43 and 60.',
        '/control/fuel_pressure_pa': poh('9.4.1') + '; midpoint of 2.8 to 3.2 bar.',
    },
    'systems.json': {},
    'panel.json': {'/equipment': 'Supplied measured panel layout; original curve interpolation, decorative details, and display composition estimates.'},
    'aircraft.json': {},
}
for index in range(4):
    rules['variant.json'][f'/stations/{index}/position_m/0'] = poh('6.5') + '; aft arms negated for body x forward.'
rules['variant.json']['/stations/4/position_m/0'] = poh('6.5') + '; aft fuel arm negated for body x forward.'
rules['variant.json']['/stations/2/max_mass_kg'] = poh('2.8') + '; forward baggage compartment only.'
for index in [3, 4]:
    rules['variant.json'][f'/stations/{index}/max_mass_kg'] = poh('1.4') + '; estimate: 75 l at 0.72 kg/l.'
for index in [0, 1]:
    rules['systems.json'][f'/definition/tanks/{index}/capacity_kg'] = poh('1.4') + '; estimate: 75 l at 0.72 kg/l.'
    rules['systems.json'][f'/definition/tanks/{index}/unusable_kg'] = poh('1.4') + '; estimate: 2 l per tank at 0.72 kg/l.'
for index, note in [(1, poh('9.4.1') + '; minimum fuel pressure.'), (3, poh('9.4.1') + '; maximum coolant temperature.')]:
    rules['systems.json'][f'/definition/modern/annunciations/{index}/threshold'] = note
system = json.loads((root / 'systems.json').read_text())
measured_breakers = {element['element']['load'] for element in json.loads((root / 'panel.json').read_text())['equipment']['elements'] if element['element']['kind'] == 'breaker'}
for index, load in enumerate(system['definition']['electrical']['loads']):
    if load['id'] in measured_breakers:
        rules['systems.json'][f'/definition/electrical/loads/{index}/breaker_amps'] = 'Supplied measured panel layout; push-pull breaker amp rating.'
for index in range(3):
    rules['family.json'][f'/geometry/gear/{index}/point_m/0'] = poh('6.4') + '; aft wheel arms negated for body x forward.'
    if index < 2:
        rules['family.json'][f'/geometry/gear/{index}/point_m/1'] = poh('1.4') + '; half of wheel track, with body-right sign.'
rules['family.json']['/aerodynamics/cl_max'] = poh('2.2') + '; estimate: CLmax derived from 700 kg, 46 kt, wing area, and ISA sea-level density.'
rules['variant.json']['/cg_envelope'] = poh('2.9') + '; body x forward; 1e-12 m numerical edge allowance; lower mass bound is an estimate.'
ledger = {}
for file, overrides in rules.items():
    document = json.loads((root / file).read_text())
    leaves = {}
    def walk(value, pointer='', inherited='estimate: original engineering or installation assumption; see docs/estimates.md'):
        source = overrides.get(pointer, inherited)
        if pointer == '/format_version':
            source = 'FlightCraft aircraft schema version.'
        if isinstance(value, dict):
            source = value.get('source', source)
            for key, child in value.items():
                walk(child, pointer + '/' + key, source)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, pointer + '/' + str(index), source)
        elif isinstance(value, (float, int)) and not isinstance(value, bool):
            leaves[pointer] = {'value': value, 'source': source}
    walk(document)
    ledger[file] = leaves
(root / 'data/sources.json').write_text(json.dumps(ledger, indent=2) + '\n')
print('Numeric provenance ledger updated.')
