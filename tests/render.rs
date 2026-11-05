use flightcraft_control::Session;
use flightcraft_ui::{
    instruments::{InstrumentInput, InstrumentPanel},
    panel_preview::render_equipment_panel,
};
use flightcraft_world::{HeightTile, Region, RegionOrigin, Surface, World};
use sling2_fidelity::Error;
use std::path::PathBuf;

#[path = "support/gpu_capture.rs"]
mod gpu_capture;

fn root() -> PathBuf {
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    if p.join("pack.json").exists() {
        p
    } else {
        p.join("..")
    }
}

// Original procedural review scenery; the capture does not depend on downloaded tiles.
fn scenery() -> Result<World, Error> {
    let mut samples = Vec::new();
    for east in 0..129 {
        for north in 0..129 {
            let n = f64::from(north) * 500. - 32000.;
            let e = f64::from(east) * 500. - 32000.;
            let ridge = 1700. * libm::exp(-libm::pow((n - 7500.) / 4300., 2.));
            samples.push((180. + ridge + 90. * libm::sin(e / 2400.) * libm::sin(n / 5000.)) as f32);
        }
    }
    let tile = HeightTile::new(
        [-32000., -32000.],
        500.,
        129,
        samples,
        vec![Surface::Grass; 128 * 128],
    )?;
    let region = Region {
        id: "sling2-review".into(),
        name: "Original panel review terrain".into(),
        origin: RegionOrigin {
            latitude_deg: 41.,
            longitude_deg: -74.,
            field_elevation_m: 0.,
            runway_heading_deg: 0.,
            runway_length_m: 900.,
            runway_width_m: 23.,
        },
        southwest_m: [-32000., -32000.],
        tiles_north: 1,
        tiles_east: 1,
        spacing_m: 500.,
        tile_size: 129,
        runway_blend_m: 100.,
        source: "Original procedural terrain estimate for panel review".into(),
        licence: "Apache-2.0".into(),
        attribution: "FlightCraft contributors".into(),
        tiles: vec!["000.fcht".into()],
        airports: None,
    };
    Ok(World::from_region(region, vec![tile])?)
}

#[test]
#[ignore = "writes actual GPU panel previews, including synthetic vision"]
fn render_panel_previews() -> Result<(), Error> {
    let mut session = Session::new()?;
    session.install_pack(&flightcraft_control::read_pack(&root())?)?;
    session.install_region(scenery()?)?;
    session.execute(
        "aircraft.load",
        serde_json::json!({"source":{"kind":"installed","id":"sling2"},"reset":true}),
    )?;
    let output = root().join("previews");
    std::fs::create_dir_all(&output)?;
    render_equipment_panel(&mut session, 1728, 968)?.save(output.join("panel.png"))?;
    session.execute("sim.reset",serde_json::json!({"world":"sling2-review","start":{"kind":"air","height_m":1200.,"airspeed_mps":50.,"heading_rad":0.}}))?;
    session.execute(
        "assist.set",
        serde_json::json!({"altitude_m":1200.,"airspeed_mps":50.,"heading_rad":0.}),
    )?;
    session.execute("sim.step", serde_json::json!({"steps":6000}))?;
    session.execute("map.set", serde_json::json!({"range_nm":4.,"night":false}))?;
    session.execute("avionics.set",serde_json::json!({"setting":{"kind":"glass","setting":{"kind":"direct_to_waypoint","waypoint":{"ident":"REVIEW","kind":"coordinate","position":{"latitude_deg":41.1,"longitude_deg":-73.9}}}}}))?;
    session.execute("assist.off", serde_json::json!({}))?;
    for setting in [
        serde_json::json!({"kind":"flight_director","on":true}),
        serde_json::json!({"kind":"engage","on":true}),
        serde_json::json!({"kind":"lateral","mode":"rol"}),
        serde_json::json!({"kind":"vertical","mode":"pit"}),
    ] {
        session.execute(
            "avionics.set",
            serde_json::json!({"setting":{"kind":"autopilot","setting":setting}}),
        )?;
    }
    session.execute("sim.step", serde_json::json!({"steps":1}))?;
    let config = session
        .aircraft_configuration()
        .ok_or("missing aircraft")?
        .clone();
    let glass = session.glass_state();
    assert!(
        glass
            .touch
            .displays
            .iter()
            .all(|d| d.synthetic_vision && d.powered)
    );
    let world = session.sim().world().clone();
    let state = *session.sim().state();
    let mut panel = InstrumentPanel::default();
    let image = gpu_capture::capture(|ui| {
        panel
            .show(
                ui,
                &config.panel,
                InstrumentInput::new(session.sim().systems(), state.time_s)
                    .with_aircraft(&config)
                    .with_glass(&glass)
                    .with_vision(&world, &state)
                    .with_autopilot(session.sim().installed_autopilot()),
                session.flight_generation(),
            )
            .map_err(std::io::Error::other)?;
        panel.show_shared_hosts(ui, &mut session);
        Ok(())
    })?;
    image.save(output.join("in-flight-panel.png"))?;
    // The panel layer now holds the centre console and floor below the dash, so the whole panel is
    // fitted into the frame at its own scale; crops follow the engine's transform rather than the
    // reference photograph's frame.
    let equipment = config.panel.equipment.as_ref().ok_or("missing equipment")?;
    let [left, top, scale] =
        flightcraft_ui::panel_preview::equipment_transform(equipment, 1728, 968)?;
    for (name, id, pad) in [
        ("pfd", "left_display", 0.),
        ("mfd", "right_display", 0.),
        ("navigator", "navigator", 0.),
        ("autopilot", "autopilot", 0.),
    ] {
        let e = equipment
            .elements
            .iter()
            .find(|e| e.id == id)
            .ok_or("missing unit")?;
        let x = (left + e.position[0] * scale - pad).max(0.).round() as u32;
        let y = (top + e.position[1] * scale - pad).max(0.).round() as u32;
        let w = ((e.size[0] * scale + 2. * pad).round() as u32).min(1728 - x);
        let h = ((e.size[1] * scale + 2. * pad).round() as u32).min(968 - y);
        image::imageops::crop_imm(&image, x, y, w, h)
            .to_image()
            .save(output.join(format!("in-flight-{name}.png")))?;
    }
    Ok(())
}
