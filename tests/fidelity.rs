#![allow(clippy::indexing_slicing)]
use flightcraft_aero::{coefficients, propulsion};
use flightcraft_sim::{Controls, Readout, Sim, Start};
use sling2_fidelity::*;

fn pitch_control(sim: &mut Sim, pitch: f64, throttle: f64, flaps: f64, brake: f64) {
    let r = sim.readout();
    let [_, q, _] = sim.state().angular_rate_rps;
    let c = coefficients(sim.aircraft(), r.alpha_rad, flaps);
    let gain = if brake > 0. { 0.3 } else { 2.5 };
    let elevator = -c.pitch + gain * (pitch - r.pitch_rad) - 0.8 * q;
    sim.set_controls(Controls {
        elevator,
        throttle,
        flaps,
        brake,
        ..Default::default()
    });
}
fn rpm_throttle(sim: &Sim, rpm: f64) -> f64 {
    let r = sim.readout();
    let rho = flightcraft_world::atmosphere(r.altitude_msl_m).density_kg_m3;
    let mut lo = 0.;
    let mut hi = 1.;
    for _ in 0..32 {
        let t = (lo + hi) * 0.5;
        let n = propulsion(
            sim.aircraft(),
            r.true_airspeed_mps * libm::cos(r.alpha_rad),
            t,
            rho,
        )
        .1 * 2.43;
        if n > rpm {
            hi = t;
        } else {
            lo = t;
        }
    }
    (lo + hi) * 0.5
}
fn cruise(ft: f64, rpm: f64, target: f64) -> Result<Readout, Error> {
    let c = gross_configuration()?;
    let height = ft * 0.3048;
    let mut sim = flight(&c, height, target * KNOT)?;
    // RPM is a measured power-setting proxy for this fixed-pitch installation.
    // The pilot holds height with pitch and adjusts throttle to hold engine RPM.
    let mut vs_integral = 0.;
    for _ in 0..1800 {
        let r = sim.readout();
        let [_, _, down] = sim.state().velocity_mps;
        vs_integral = (vs_integral + (height - r.altitude_msl_m) * 0.05 * 0.001).clamp(-0.03, 0.03);
        let gamma = libm::atan2(-down, r.ground_speed_mps.max(1.));
        let pitch = r.alpha_rad + gamma + 0.012 * (height - r.altitude_msl_m)
            - 0.10 * r.vertical_speed_mps
            + vs_integral;
        let throttle = rpm_throttle(&sim, rpm);
        pitch_control(&mut sim, pitch.clamp(-0.1, 0.35), throttle, 0., 0.);
        sim.step(6);
    }
    Ok(sim.readout())
}
fn climb(ft: f64, ias: f64) -> Result<Readout, Error> {
    let c = gross_configuration()?;
    let height = (ft * 0.3048).max(30.);
    let rho = flightcraft_world::atmosphere(height).density_kg_m3;
    let speed = ias * KNOT / libm::sqrt(rho / 1.225);
    let mut sim = flight(&c, height, speed)?;
    for _ in 0..800 {
        let r = sim.readout();
        let rho = flightcraft_world::atmosphere(r.altitude_msl_m).density_kg_m3;
        let target_speed = ias * KNOT / libm::sqrt(rho / 1.225);
        let mut low = -0.05;
        let mut high = 0.26;
        for _ in 0..30 {
            let alpha = (low + high) * 0.5;
            let c = coefficients(sim.aircraft(), alpha, 0.);
            let n = 5500. / 2.43 / 60.;
            let d = sim.aircraft().propulsion.prop_diameter_m;
            let j = target_speed * libm::cos(alpha) / (n * d);
            let thrust =
                flightcraft_aero::interpolate(&sim.aircraft().propulsion.prop_ct.points, j)
                    * rho
                    * n
                    * n
                    * libm::pow(d, 4.);
            let dynamic =
                0.5 * rho * target_speed * target_speed * sim.aircraft().geometry.wing_area_m2;
            let weight = sim.aircraft().mass.mass_kg * G;
            let gamma = libm::asin(
                ((thrust * libm::cos(alpha) - dynamic * c.drag) / weight).clamp(-0.5, 0.5),
            );
            if dynamic * c.lift + thrust * libm::sin(alpha) > weight * libm::cos(gamma) {
                high = alpha;
            } else {
                low = alpha;
            }
        }
        let alpha = (low + high) * 0.5;
        let coefficient = coefficients(sim.aircraft(), alpha, 0.);
        let throttle = rpm_throttle(&sim, 5500.);
        let thrust = propulsion(
            sim.aircraft(),
            r.true_airspeed_mps * libm::cos(alpha),
            throttle,
            rho,
        )
        .0;
        let dynamic =
            0.5 * rho * target_speed * target_speed * sim.aircraft().geometry.wing_area_m2;
        let gamma = libm::asin(
            ((thrust * libm::cos(alpha) - dynamic * coefficient.drag)
                / (sim.aircraft().mass.mass_kg * G))
                .clamp(-0.5, 0.5),
        );
        let pitch = alpha + gamma + 0.04 * (r.indicated_airspeed_mps - ias * KNOT);
        pitch_control(&mut sim, pitch.clamp(-0.1, 0.4), throttle, 0., 0.);
        sim.step(6);
    }
    Ok(sim.readout())
}

#[test]
fn all_twenty_poh_cruise_settings() -> Result<(), Error> {
    let c = gross_configuration()?;
    assert_eq!(c.weight_balance.mass_kg, 700.);
    for (ft, targets) in [
        (100., [79., 94., 99., 105., 111.]),
        (3000., [73., 90., 102., 107., 111.]),
        (6000., [70., 86., 97., 105., 112.]),
        (9000., [70., 85., 96., 102., 105.]),
    ] {
        for (rpm, target) in [4500., 4800., 5000., 5300., 5500.].into_iter().zip(targets) {
            let r = cruise(ft, rpm, target)?;
            println!(
                "cruise {ft}ft {rpm}rpm: {:.2} vs {target} KTAS, {:.1}% error, height {:.1}, vs {:.3}",
                r.true_airspeed_mps / KNOT,
                100. * (r.true_airspeed_mps / KNOT / target - 1.),
                r.altitude_msl_m,
                r.vertical_speed_mps
            );
            assert!(!r.crashed);
            assert!(
                (r.true_airspeed_mps / KNOT / target - 1.).abs() <= 0.05,
                "cruise tolerance at {ft} ft / {rpm} RPM"
            );
            assert!((r.engine_rpm - rpm).abs() < 15., "RPM setting not achieved");
            assert!(
                (r.altitude_msl_m - ft * 0.3048).abs() < 3.,
                "cruise not level"
            );
            assert!(r.vertical_speed_mps.abs() < 0.1, "cruise not settled");
        }
    }
    Ok(())
}
#[test]
fn vy_climb_and_vx() -> Result<(), Error> {
    for (ft, target) in [(0., 700.), (3000., 500.), (6000., 420.), (9000., 330.)] {
        let r = climb(ft, 74.)?;
        println!(
            "climb {ft}ft IAS {:.1} roc {:.1}fpm alt {:.1}",
            r.indicated_airspeed_mps / KNOT,
            r.vertical_speed_mps / 0.00508,
            r.altitude_msl_m
        );
        assert!(!r.crashed);
        assert!(
            (r.indicated_airspeed_mps / KNOT - 74.).abs() < 0.5,
            "climb pilot failed to hold Vy"
        );
        assert!(
            (r.vertical_speed_mps / 0.00508 / target - 1.).abs() <= 0.1,
            "climb rate tolerance at {ft} ft"
        );
    }
    let mut best = (0., f64::NEG_INFINITY);
    // Rate is measured from the rigid-body trajectory at the commanded IAS.
    for kt in [55., 60., 65., 70., 74., 78., 82.] {
        let r = climb(0., kt)?;
        println!(
            "sweep {kt}kt IAS {:.1} roc {:.1}fpm angle {:.3}",
            r.indicated_airspeed_mps / KNOT,
            r.vertical_speed_mps / 0.00508,
            r.vertical_speed_mps / r.true_airspeed_mps
        );
        let angle = r.vertical_speed_mps / r.true_airspeed_mps;
        if angle > best.1 {
            best = (r.indicated_airspeed_mps / KNOT, angle);
        }
        assert!(!r.crashed);
    }
    assert!(
        (best.0 / 65. - 1.).abs() <= 0.1,
        "Vx measured {} kt",
        best.0
    );
    Ok(())
}
#[test]
fn clean_and_full_flap_stalls() -> Result<(), Error> {
    for flaps in [0., 1.] {
        let c = gross_configuration()?;
        let rho = flightcraft_world::atmosphere(1000.).density_kg_m3;
        let mut sim = flight(&c, 1000., 58. * KNOT / libm::sqrt(rho / 1.225))?;
        let mut found = false;
        for _ in 0..5000 {
            let r = sim.readout();
            let gamma =
                libm::asin((r.vertical_speed_mps / r.true_airspeed_mps.max(1.)).clamp(-0.5, 0.5));
            let pitch = (r.alpha_rad + gamma - 0.06 * r.vertical_speed_mps).clamp(-0.1, 0.45);
            pitch_control(&mut sim, pitch, 0., flaps, 0.);
            sim.step(6);
            if r.alpha_rad
                > if flaps == 0. {
                    16_f64.to_radians()
                } else {
                    15_f64.to_radians()
                }
            {
                println!(
                    "stall flap {flaps} {:.2} KIAS vs {:.2}, height {}",
                    r.indicated_airspeed_mps / KNOT,
                    r.vertical_speed_mps,
                    r.altitude_msl_m
                );
                let target = if flaps == 0. { 46. } else { 42. };
                assert!(
                    (r.indicated_airspeed_mps / KNOT - target).abs() <= 2.,
                    "stall tolerance"
                );
                assert!(!r.crashed);
                found = true;
                break;
            }
            assert!(!r.crashed, "stall flight impacted");
        }
        assert!(found, "stall not reached");
    }
    Ok(())
}
fn takeoff_roll(grass: bool) -> Result<f64, Error> {
    let c = gross_configuration()?;
    let start_kind = Start::RunwayAt {
        threshold_ned_m: [0., if grass { 50. } else { 0. }, 0.],
        heading_rad: 0.,
    };
    let mut sim = Sim::new_with_aircraft(&start_kind, c.aircraft.clone())?;
    sim.configure_systems(&c)?;
    sim.step(360);
    let start = sim.state().position_m[0];
    for _ in 0..2000 {
        let r = sim.readout();
        let pitch = if r.indicated_airspeed_mps > 40. * KNOT {
            0.23
        } else {
            0.
        };
        pitch_control(&mut sim, pitch, 1., 1. / 3., 0.);
        sim.step(2);
        let r = sim.readout();
        assert!(!r.crashed, "takeoff impact");
        if !r.on_ground {
            return Ok(sim.state().position_m[0] - start);
        }
    }
    Err("takeoff failed to become airborne".into())
}
fn landing_roll(grass: bool) -> Result<f64, Error> {
    let c = gross_configuration()?;
    let start = Start::AirAt {
        position_m: [0., if grass { 50. } else { 0. }, -15.],
        airspeed_mps: 65. * KNOT,
        heading_rad: 0.,
    };
    let mut sim = Sim::new_with_aircraft(&start, c.aircraft.clone())?;
    sim.configure_systems(&c)?;
    let mut touchdown = None;
    for _ in 0..5000 {
        let r = sim.readout();
        let target_vs = if r.height_agl_m > 1.5 { -1.5 } else { -0.25 };
        let gamma =
            libm::asin((r.vertical_speed_mps / r.true_airspeed_mps.max(1.)).clamp(-0.5, 0.5));
        let pitch =
            (r.alpha_rad + gamma + 0.05 * (target_vs - r.vertical_speed_mps)).clamp(-0.1, 0.28);
        pitch_control(
            &mut sim,
            if touchdown.is_some() { 0. } else { pitch },
            0.,
            1.,
            if touchdown.is_some() { 1. } else { 0. },
        );
        sim.step(2);
        let r = sim.readout();
        assert!(!r.crashed, "landing impact");
        if r.on_ground && touchdown.is_none() {
            touchdown = Some(sim.state().position_m[0]);
        }
        if let Some(start) = touchdown
            && r.ground_speed_mps < 0.2
        {
            return Ok(sim.state().position_m[0] - start);
        }
    }
    Err("landing did not stop".into())
}
#[test]
fn concrete_and_grass_ground_rolls() -> Result<(), Error> {
    for (grass, target) in [(false, 140.), (true, 160.)] {
        let distance = takeoff_roll(grass)?;
        println!("takeoff grass={grass}: {distance:.2}m (target {target}m)");
        assert!(
            (distance / target - 1.).abs() <= 0.1,
            "takeoff ground-roll tolerance"
        );
        let distance = landing_roll(grass)?;
        println!("landing grass={grass}: {distance:.2}m (target 90m)");
        assert!(
            (distance / 90. - 1.).abs() <= 0.1,
            "landing ground-roll tolerance"
        );
    }
    Ok(())
}

#[test]
fn published_cg_edges_and_mass_limits() -> Result<(), Error> {
    use flightcraft_aero::Load;
    let c = configuration()?;
    let mut v = c.variant;
    // Probe the actual polygon calculation independently of loading-arm combinations.
    for mass in [370., 500., 700.] {
        for (arm, inside) in [
            (1.6349, false),
            (1.635, true),
            (1.72, true),
            (1.808, true),
            (1.8081, false),
        ] {
            v.empty_mass.mass_kg = mass;
            v.empty_mass.cg_m = [-arm, 0., 0.];
            let b = v.weight_balance(&Load::default())?;
            assert_eq!(b.in_limits, inside, "mass {mass}, aft arm {arm}");
        }
    }
    for mass in [369.9, 700.1] {
        v.empty_mass.mass_kg = mass;
        v.empty_mass.cg_m = [-1.72, 0., 0.];
        assert!(!v.weight_balance(&Load::default())?.in_limits);
    }
    Ok(())
}

#[test]
fn every_layer_number_has_provenance() -> Result<(), Error> {
    use serde_json::Value;
    let sources: Value = serde_json::from_str(include_str!("../data/sources.json"))?;
    let documents = [
        ("family.json", include_str!("../family.json")),
        ("variant.json", include_str!("../variant.json")),
        ("engine.json", include_str!("../engine.json")),
        ("systems.json", include_str!("../systems.json")),
        ("panel.json", include_str!("../panel.json")),
        ("aircraft.json", include_str!("../aircraft.json")),
    ];
    fn walk(v: &Value, pointer: &str, ledger: &Value) {
        match v {
            Value::Number(_) => {
                assert_eq!(&ledger[pointer]["value"], v, "stale source at {pointer}");
                assert!(
                    ledger[pointer]["source"]
                        .as_str()
                        .is_some_and(|s| !s.is_empty()),
                    "missing source at {pointer}"
                );
            }
            Value::Object(map) => {
                for (k, v) in map {
                    walk(v, &format!("{pointer}/{k}"), ledger);
                }
            }
            Value::Array(array) => {
                for (i, v) in array.iter().enumerate() {
                    walk(v, &format!("{pointer}/{i}"), ledger);
                }
            }
            _ => {}
        }
    }
    for (file, text) in documents {
        walk(&serde_json::from_str(text)?, "", &sources[file]);
    }
    Ok(())
}

#[test]
fn measured_units_and_skin_slots_stay_fixed() -> Result<(), Error> {
    let c = configuration()?;
    let p = c.panel.equipment.ok_or("missing equipment")?;
    let scale = 0.77;
    for (id, x, y, w, h) in [
        ("left_display", 248., 308., 424., 308.),
        ("right_display", 1062., 308., 424., 308.),
        ("navigator", 745., 382., 235., 98.),
        ("autopilot", 742., 485., 243., 77.),
        ("standby", 798., 238., 132., 137.),
    ] {
        let e = p
            .elements
            .iter()
            .find(|e| e.id == id)
            .ok_or("missing unit")?;
        for (actual, target) in e.position.into_iter().chain(e.size).zip([x, y, w, h]) {
            assert!((actual / scale - target).abs() < 0.01, "{id} moved");
        }
    }
    for id in ["left_display", "right_display"] {
        let display = p
            .elements
            .iter()
            .find(|e| e.id == id)
            .ok_or("display missing")?;
        assert!(matches!(
            display.element,
            flightcraft_aero::modern::PanelElement::TouchDisplay {
                layout: flightcraft_aero::modern::TouchLayout::IntegratedPfd,
                engine_strip: true,
                ..
            }
        ));
        // A pilot in the left seat: PFD on the left, MFD on the right.
        let flightcraft_aero::modern::PanelElement::TouchDisplay { default_page, .. } =
            &display.element
        else {
            return Err("not a touch display".into());
        };
        assert_eq!(
            *default_page,
            (id == "right_display").then_some(flightcraft_aero::modern::TouchLayout::Mfd)
        );
        assert!(display.appearance.synthetic_vision);
        let bezel = display.appearance.bezel.as_ref().ok_or("bezel missing")?;
        assert_eq!(
            bezel.margins,
            [22. * scale, 28. * scale, 22. * scale, 60. * scale]
        );
        assert_eq!(bezel.softkey_count, 4);
    }
    let selector = p
        .elements
        .iter()
        .find(|e| e.id == "fuel_selector")
        .ok_or("selector missing")?;
    assert!(((selector.position[1] + selector.size[1] / 2.) / scale - 770.).abs() < 0.01);
    assert_eq!(
        p.shell
            .as_ref()
            .and_then(|s| s.palette.face.as_ref())
            .map(|c| c.0.as_str()),
        Some("#333333")
    );
    let slots: serde_json::Value = serde_json::from_str(include_str!("../data/skin-slots.json"))?;
    for slot in slots["slots"].as_array().ok_or("slots not array")? {
        let e = p
            .elements
            .iter()
            .find(|e| Some(e.id.as_str()) == slot["id"].as_str())
            .ok_or("slot missing")?;
        assert_eq!(serde_json::to_value(e.position)?, slot["position_mm"]);
        assert_eq!(serde_json::to_value(e.size)?, slot["size_mm"]);
    }
    Ok(())
}

#[test]
fn normal_procedures_follow_the_poh_and_bind_to_the_panel() -> Result<(), Error> {
    let c = configuration()?;
    let set = c
        .installed_systems
        .procedures
        .as_ref()
        .ok_or("the systems layer carries no normal procedures")?;
    set.validate()?;
    assert_eq!(set.version, 1);
    assert!(set.source.contains("Revision 2.8") && set.source.contains("9.4.13"));
    let ids: Vec<_> = set.checklists.iter().map(|l| l.id.as_str()).collect();
    assert_eq!(
        ids,
        [
            "before_start",
            "engine_start",
            "warm_up",
            "run_up",
            "taxi",
            "before_takeoff",
            "shutdown",
            "securing"
        ]
    );
    let list = |id: &str| {
        set.checklists
            .iter()
            .find(|l| l.id == id)
            .ok_or("missing list")
    };
    // POH 4.7.1 has eighteen items.
    assert_eq!(list("before_takeoff")?.items.len(), 18);
    let panel = c.panel.equipment.as_ref().ok_or("missing equipment")?;
    for l in &set.checklists {
        for item in &l.items {
            assert!(
                item.poh_ref.starts_with("POH"),
                "{} lacks a POH reference",
                item.id
            );
            if let Some(control) = &item.control {
                assert!(
                    panel.elements.iter().any(|e| &e.id == control),
                    "{} points at {control}, which is not on the panel",
                    item.id
                );
            }
        }
    }
    // The ignition check is the supplement's: 4,000 rpm, no drop with lane B off, under 180 with lane A off.
    let json = serde_json::to_string(list("run_up")?)?;
    assert!(json.contains("\"lane\":\"b\",\"at_rpm\":4000.0,\"max_drop_rpm\":0.0"));
    assert!(json.contains("\"lane\":\"a\",\"at_rpm\":4000.0,\"max_drop_rpm\":180.0"));
    // Numbers that did not come from the POH say so.
    let unverified: Vec<_> = list("run_up")?
        .items
        .iter()
        .filter(|i| i.unverified.is_some())
        .map(|i| i.id.as_str())
        .collect();
    for id in [
        "lane_b_off",
        "pump_1_alone",
        "pump_2_alone",
        "max_power",
        "efis_battery",
    ] {
        assert!(unverified.contains(&id), "{id} should be marked unverified");
    }
    Ok(())
}

#[test]
fn electronic_engine_pumps_key_breakers_and_selector() -> Result<(), Error> {
    use flightcraft_sim::modern::{KeyPosition, Lane, ModernSetting, Pump};
    use flightcraft_sim::systems::{FuelSelector, SystemSetting};
    let c = configuration()?;
    let mut sim = flight(&c, 1200., 50.)?;
    let action = |sim: &mut Sim, setting| sim.set_systems(SystemSetting::Equipment { setting });
    action(
        &mut sim,
        ModernSetting::Lane {
            lane: Lane::A,
            on: false,
        },
    )?;
    sim.step(1);
    assert!(sim.systems().engine_running);
    // Lane A off leaves lane B alone: a drop (POH 9.4.13 allows under 180 rpm at 4,000 rpm).
    assert!((sim.systems().engine_power_fraction - 0.93).abs() < 1e-9);
    // Lane B off leaves lane A alone: the POH allows no drop at all.
    action(
        &mut sim,
        ModernSetting::Lane {
            lane: Lane::A,
            on: true,
        },
    )?;
    action(
        &mut sim,
        ModernSetting::Lane {
            lane: Lane::B,
            on: false,
        },
    )?;
    sim.step(1);
    assert!((sim.systems().engine_power_fraction - 1.0).abs() < 1e-9);
    action(
        &mut sim,
        ModernSetting::Lane {
            lane: Lane::A,
            on: false,
        },
    )?;
    action(
        &mut sim,
        ModernSetting::Lane {
            lane: Lane::B,
            on: true,
        },
    )?;
    // A seeded weak lane loses further power when it carries the engine alone.
    action(
        &mut sim,
        ModernSetting::Failure {
            component: flightcraft_sim::modern::Component::LaneBWeak,
            failed: true,
        },
    )?;
    sim.step(1);
    assert!((sim.systems().engine_power_fraction - 0.93 * 0.82).abs() < 1e-9);
    action(
        &mut sim,
        ModernSetting::Failure {
            component: flightcraft_sim::modern::Component::LaneBWeak,
            failed: false,
        },
    )?;
    sim.step(1);
    action(
        &mut sim,
        ModernSetting::Lane {
            lane: Lane::B,
            on: false,
        },
    )?;
    sim.step(1);
    assert!(!sim.systems().engine_running);
    for lane in [Lane::A, Lane::B] {
        action(&mut sim, ModernSetting::Lane { lane, on: true })?;
    }
    action(
        &mut sim,
        ModernSetting::Key {
            position: KeyPosition::Start,
        },
    )?;
    sim.step(260);
    action(
        &mut sim,
        ModernSetting::Key {
            position: KeyPosition::On,
        },
    )?;
    assert!(sim.systems().engine_running);
    action(
        &mut sim,
        ModernSetting::Pump {
            pump: Pump::One,
            on: false,
        },
    )?;
    sim.step(1);
    assert!(sim.systems().engine_running);
    sim.set_systems(SystemSetting::Breaker {
        load: "pump_2".into(),
        closed: false,
    })?;
    sim.step(1);
    assert!(!sim.systems().engine_running);
    sim.set_systems(SystemSetting::Breaker {
        load: "pump_2".into(),
        closed: true,
    })?;
    action(
        &mut sim,
        ModernSetting::Key {
            position: KeyPosition::Start,
        },
    )?;
    sim.step(260);
    action(
        &mut sim,
        ModernSetting::Key {
            position: KeyPosition::On,
        },
    )?;
    assert!(sim.systems().engine_running);
    sim.set_systems(SystemSetting::FuelSelector {
        position: FuelSelector::Off,
    })?;
    sim.step(1);
    assert!(!sim.systems().engine_running);
    let modern = sim
        .systems()
        .modern
        .as_ref()
        .ok_or("missing modern controls")?;
    assert!(modern.master_warning);
    assert!((modern.propeller_rpm * 2.43 - sim.readout().engine_rpm).abs() < 1e-6);
    Ok(())
}

#[test]
fn guarded_lanes_backup_buses_and_wigwag_are_connected() -> Result<(), Error> {
    use flightcraft_aero::panel_fidelity::BackupCircuit;
    use flightcraft_sim::{
        modern::ModernSetting,
        systems::{SystemSetting, SystemSwitch},
    };
    let mut sim = flight(&configuration()?, 1200., 50.)?;
    let action = |sim: &mut Sim, setting| sim.set_systems(SystemSetting::Equipment { setting });
    assert!(
        action(
            &mut sim,
            ModernSetting::PanelControl {
                id: "lane_a".into(),
                value: 0.
            }
        )
        .is_err()
    );
    action(
        &mut sim,
        ModernSetting::PanelGuard {
            id: "lane_a".into(),
            open: true,
        },
    )?;
    action(
        &mut sim,
        ModernSetting::PanelControl {
            id: "lane_a".into(),
            value: 0.,
        },
    )?;
    sim.step(1);
    assert!(
        !sim.systems()
            .modern
            .as_ref()
            .ok_or("missing engine equipment")?
            .lane_a
            .on
    );
    action(
        &mut sim,
        ModernSetting::PanelControl {
            id: "lane_a".into(),
            value: 1.,
        },
    )?;
    for circuit in [BackupCircuit::Ems, BackupCircuit::Efis] {
        action(&mut sim, ModernSetting::BackupPower { circuit, on: true })?;
    }
    sim.set_systems(SystemSetting::Switch {
        switch: SystemSwitch::Master,
        on: false,
    })?;
    sim.step(120);
    let powered = |sim: &Sim, id: &str| {
        sim.systems()
            .electrical
            .loads
            .iter()
            .any(|load| load.id == id && load.powered)
    };
    for id in [
        "pump_1",
        "pump_2",
        "touch_left",
        "touch_right",
        "glass_ahrs",
        "navigator",
    ] {
        assert!(powered(&sim, id), "backup feed missing: {id}");
    }
    let modern = sim
        .systems()
        .modern
        .as_ref()
        .ok_or("missing backup equipment")?;
    assert!(
        modern
            .backup_buses
            .iter()
            .all(|b| b.on && b.remaining_ah < 2. && b.remaining_ah > 0.)
    );
    sim.set_systems(SystemSetting::Breaker {
        load: "touch_left".into(),
        closed: false,
    })?;
    sim.step(1);
    assert!(!powered(&sim, "touch_left"));
    assert!(powered(&sim, "touch_right"));
    action(
        &mut sim,
        ModernSetting::BackupPower {
            circuit: BackupCircuit::Ems,
            on: false,
        },
    )?;
    sim.step(1);
    assert!(!powered(&sim, "pump_1"));
    assert!(powered(&sim, "touch_right"));

    let mut lights = flight(&configuration()?, 1200., 50.)?;
    action(&mut lights, ModernSetting::Wigwag { on: true })?;
    lights.step(1);
    let first = (
        powered(&lights, "landing"),
        powered(&lights, "landing_right"),
    );
    lights.step(60);
    let second = (
        powered(&lights, "landing"),
        powered(&lights, "landing_right"),
    );
    assert_ne!(first.0, first.1, "lamps must alternate");
    assert_eq!(second, (first.1, first.0));
    action(&mut lights, ModernSetting::Wigwag { on: false })?;
    lights.step(1);
    assert!(powered(&lights, "landing") && powered(&lights, "landing_right"));
    Ok(())
}

#[test]
fn radio_identity_and_audio_follow_the_navigator_installation() -> Result<(), Error> {
    use flightcraft_aero::modern::PanelElement;
    use flightcraft_control::{Session, read_pack};
    use serde_json::json;

    let config = configuration()?;
    assert_eq!(config.aircraft.identity.registration, "N371FC");
    assert_eq!(config.aircraft.identity.spoken_type, "Sling");
    assert_eq!(config.variant.identity.registration, "N371FC");
    assert_eq!(config.variant.identity.spoken_type, "Sling");
    let panel = config.panel.equipment.as_ref().ok_or("missing equipment")?;
    assert!(
        !panel
            .elements
            .iter()
            .any(|e| matches!(e.element, PanelElement::AudioPanel)),
        "audio controls must not add a separate panel face"
    );
    assert!(panel.elements.iter().any(|e| {
        e.id == "registration"
            && matches!(&e.element, PanelElement::Placard { text, .. } if text == "{registration}")
    }));
    let installation = &config.panel.audio_panel;
    assert_eq!(installation.power_load, "navigator");
    assert_eq!(installation.com1_load, "navigator");
    assert_eq!(installation.com2_load, "navigator");

    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let root = if manifest.join("pack.json").is_file() {
        manifest.to_owned()
    } else {
        manifest.join("..")
    };
    let mut session = Session::new()?;
    session.install_pack(&read_pack(&root)?)?;
    session.execute(
        "aircraft.load",
        json!({"source":{"kind":"installed","id":"sling2"},"reset":true}),
    )?;
    let callsign = session.pilot_callsign();
    assert!(!callsign.overridden);
    assert_eq!(callsign.registration, "N371FC");
    assert_eq!(callsign.spoken_type, "Sling");
    assert_eq!(callsign.full, "Sling Three Seven One Foxtrot Charlie");
    assert_eq!(callsign.current, callsign.full);
    assert!(session.comms_state().powered);
    session.execute(
        "comms.audio_panel",
        json!({"transmit":2,"receive_com2":true,"intercom":false,"volume":0.6}),
    )?;
    let audio = session.comms_state();
    assert_eq!(audio.panel.transmit, 2);
    assert!(audio.panel.receive_com2 && !audio.panel.intercom);
    assert!((audio.panel.volume - 0.6).abs() < f64::EPSILON);
    assert!(audio.com1_powered && audio.com2_powered);
    session.execute(
        "systems.set",
        json!({"setting":{"kind":"breaker","load":"navigator","closed":false}}),
    )?;
    let unpowered = session.comms_state();
    assert!(!unpowered.powered && !unpowered.com1_powered && !unpowered.com2_powered);
    session.execute(
        "systems.set",
        json!({"setting":{"kind":"breaker","load":"navigator","closed":true}}),
    )?;
    assert!(session.comms_state().powered);
    Ok(())
}

#[test]
fn preflight_walkaround_encodes_poh_section_4_4() -> Result<(), Box<dyn std::error::Error>> {
    use flightcraft_aero::preflight::{Action, DefectKind, Preflight, PropKind};
    let systems: serde_json::Value = serde_json::from_str(include_str!("../systems.json"))?;
    let preflight: Preflight = serde_json::from_value(systems["preflight"].clone())?;
    preflight.validate()?;
    let pack: serde_json::Value = serde_json::from_str(include_str!("../pack.json"))?;
    assert_eq!(
        pack["format_version"], 4,
        "a preflight section needs pack format 4"
    );
    // The six stations of POH 4.4, in handbook order, with the handbook's item counts.
    let counts: Vec<_> = preflight
        .stations
        .iter()
        .map(|s| {
            (
                s.id.as_str(),
                preflight.items.iter().filter(|i| i.station == s.id).count(),
            )
        })
        .collect();
    assert_eq!(
        counts,
        [
            ("cabin", 13),
            ("fuselage", 6),
            ("empennage", 6),
            ("right_wing", 13),
            ("nose", 15),
            ("left_wing", 14)
        ]
    );
    assert!(preflight.source.contains("Rev 2.8") && preflight.source.contains("4.4"));
    for item in &preflight.items {
        assert!(
            item.poh_ref.starts_with("4.4 ("),
            "{} has no POH reference",
            item.id
        );
    }
    // Both wings: the POH's fuel warning, the 30 litre cover level, and no fuel sump drain step.
    assert!((preflight.fuel.covers_bottom_l - 30.).abs() < f64::EPSILON);
    for id in ["fuel_level_right", "fuel_level_left"] {
        let item = preflight.item(id).ok_or("missing fuel level item")?;
        assert!(matches!(item.action, Action::FuelCap { .. }));
        assert!(
            item.warning
                .as_deref()
                .is_some_and(|w| w.contains("30 litres"))
        );
    }
    assert!(
        !preflight
            .items
            .iter()
            .any(|i| i.text.to_lowercase().contains("sump"))
    );
    // The pitot cover comes off with the left-wing pitot item; chocks and ropes at the nose.
    let pitot = preflight.item("pitot").ok_or("missing pitot item")?;
    assert_eq!(pitot.station, "left_wing");
    assert_eq!(
        preflight.props_of(pitot).first().map(|p| p.kind),
        Some(PropKind::PitotCover)
    );
    let chocks = preflight
        .item("chocks_ropes")
        .ok_or("missing chocks item")?;
    assert_eq!(chocks.station, "nose");
    assert!(
        preflight
            .props_of(chocks)
            .iter()
            .any(|p| p.kind == PropKind::Chock)
    );
    assert!(
        preflight
            .props_of(chocks)
            .iter()
            .any(|p| p.kind == PropKind::TieDownRope)
    );
    // The palm-of-the-hand caution is on the optional propeller item.
    let prop = preflight
        .item("propeller_turn")
        .ok_or("missing propeller item")?;
    assert!(prop.optional && prop.warning.as_deref().is_some_and(|w| w.contains("palm")));
    // Seedable findings include every kind the lessons use.
    let kinds: std::collections::BTreeSet<_> = preflight
        .items
        .iter()
        .flat_map(|i| i.defects.iter().map(|d| d.kind))
        .collect();
    for kind in [
        DefectKind::LowOil,
        DefectKind::LowFuel,
        DefectKind::LooseCowlFastener,
        DefectKind::AileronHardwareMissing,
        DefectKind::FlapHardwareMissing,
        DefectKind::DamagedTyre,
        DefectKind::WheelFairingCrack,
    ] {
        assert!(kinds.contains(&kind), "{kind:?} cannot be seeded");
    }
    // Every hand-moved control is a real moving part of the exterior.
    let exterior: serde_json::Value = serde_json::from_str(include_str!("../exterior.json"))?;
    let nodes: Vec<_> = exterior["moving_parts"]
        .as_array()
        .ok_or("no moving parts")?
        .iter()
        .filter_map(|p| p["node"].as_str())
        .collect();
    for part in preflight.driven_parts() {
        assert!(nodes.contains(&part), "{part} is not a moving part");
    }
    // Filler caps sit on the two tanks of the systems definition.
    let tanks: Vec<_> = systems["definition"]["tanks"]
        .as_array()
        .ok_or("no tanks")?
        .iter()
        .filter_map(|t| t["id"].as_str())
        .collect();
    for cap in &preflight.fuel.caps {
        assert!(tanks.contains(&cap.tank.as_str()));
    }
    Ok(())
}
