#![allow(clippy::unwrap_used, clippy::expect_used, clippy::indexing_slicing)]
use eframe::egui::{self, ColorImage, TextureId, epaint::Primitive};
use flightcraft_control::Session;
use flightcraft_ui::instruments::{InstrumentInput, InstrumentPanel};
use image::{Rgba, RgbaImage};
use std::{collections::BTreeMap, path::PathBuf};

fn root() -> PathBuf {
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    if p.join("pack.json").exists() {
        p
    } else {
        p.join("..")
    }
}

// Barycentric sampling of the actual egui output, including its live font atlas.
// This test-only renderer does not construct an alternative panel illustration.
fn capture(mut paint: impl FnMut(&mut egui::Ui)) -> RgbaImage {
    let ctx = egui::Context::default();
    flightcraft_ui::theme::install(&ctx);
    ctx.set_pixels_per_point(1.);
    let mut textures = BTreeMap::<TextureId, ColorImage>::new();
    let mut frame = None;
    for _ in 0..3 {
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(1728., 968.),
                )),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::new().fill(flightcraft_ui::theme::BACKGROUND))
                    .show(ctx, |ui| paint(ui));
            },
        );
        for (id, delta) in &output.textures_delta.set {
            let egui::ImageData::Color(data) = &delta.image;
            if let Some([x, y]) = delta.pos {
                let dst = textures.get_mut(id).unwrap();
                for row in 0..data.size[1] {
                    for col in 0..data.size[0] {
                        dst.pixels[(y + row) * dst.size[0] + x + col] =
                            data.pixels[row * data.size[0] + col];
                    }
                }
            } else {
                textures.insert(*id, (**data).clone());
            }
        }
        frame = Some(output);
    }
    let output = frame.unwrap();
    let mut image = RgbaImage::from_pixel(
        1728,
        968,
        Rgba(flightcraft_ui::theme::BACKGROUND.to_array()),
    );
    let area = |a: egui::Pos2, b: egui::Pos2, c: egui::Pos2| {
        (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
    };
    for item in ctx.tessellate(output.shapes, 1.) {
        let Primitive::Mesh(mesh) = item.primitive else {
            continue;
        };
        let Some(texture) = textures.get(&mesh.texture_id) else {
            continue;
        };
        for triangle in mesh.indices.as_chunks::<3>().0 {
            let [a, b, c] = [
                mesh.vertices[triangle[0] as usize],
                mesh.vertices[triangle[1] as usize],
                mesh.vertices[triangle[2] as usize],
            ];
            let total = area(a.pos, b.pos, c.pos);
            if total.abs() < 1e-6 {
                continue;
            }
            let lo = a
                .pos
                .min(b.pos)
                .min(c.pos)
                .max(item.clip_rect.min)
                .max(egui::Pos2::ZERO);
            let hi = a
                .pos
                .max(b.pos)
                .max(c.pos)
                .min(item.clip_rect.max)
                .min(egui::pos2(1728., 968.));
            for y in (lo.y.floor() as u32)..(hi.y.ceil() as u32) {
                for x in (lo.x.floor() as u32)..(hi.x.ceil() as u32) {
                    let p = egui::pos2(x as f32 + 0.5, y as f32 + 0.5);
                    let weights = [
                        area(p, b.pos, c.pos) / total,
                        area(p, c.pos, a.pos) / total,
                        area(p, a.pos, b.pos) / total,
                    ];
                    if weights.iter().any(|v| *v < -1e-5) {
                        continue;
                    }
                    let uv = a.uv.to_vec2() * weights[0]
                        + b.uv.to_vec2() * weights[1]
                        + c.uv.to_vec2() * weights[2];
                    let tx = ((uv.x * texture.size[0] as f32) as usize).min(texture.size[0] - 1);
                    let ty = ((uv.y * texture.size[1] as f32) as usize).min(texture.size[1] - 1);
                    let tex = texture.pixels[ty * texture.size[0] + tx].to_array();
                    let colors = [a.color.to_array(), b.color.to_array(), c.color.to_array()];
                    let mut src = [0_f32; 4];
                    for channel in 0..4 {
                        for vertex in 0..3 {
                            src[channel] += weights[vertex]
                                * f32::from(colors[vertex][channel])
                                * f32::from(tex[channel])
                                / 255.;
                        }
                    }
                    if let Some(dst) = image.get_pixel_mut_checked(x, y) {
                        for channel in 0..3 {
                            dst.0[channel] = (src[channel]
                                + f32::from(dst.0[channel]) * (1. - src[3] / 255.))
                                .clamp(0., 255.) as u8;
                        }
                        dst.0[3] = 255;
                    }
                }
            }
        }
    }
    image
}

#[test]
#[ignore = "writes panel previews from actual engine UI meshes"]
fn render_panel_previews() -> Result<(), sling2_fidelity::Error> {
    let mut session = Session::new()?;
    session.install_pack(&flightcraft_control::read_pack(&root())?)?;
    let engine = std::env::var_os("FLIGHTCRAFT_ENGINE")
        .map(PathBuf::from)
        .unwrap_or_else(|| root().join("../flightcraft"));
    let region = engine.join("assets/terrain/new-york");
    if region.exists() {
        session.install_region(flightcraft_control::read_region(&region)?)?;
    }
    session.execute(
        "aircraft.load",
        serde_json::json!({"source":{"kind":"installed","id":"sling2"},"reset":true}),
    )?;
    std::fs::create_dir_all(root().join("previews"))?;
    for (name, airborne) in [("panel", false), ("in-flight-panel", true)] {
        if airborne {
            session.execute("sim.reset",serde_json::json!({"world":"new-york","start":{"kind":"air","height_m":1200.,"airspeed_mps":50.,"heading_rad":0.}}))?;
            session.execute(
                "assist.set",
                serde_json::json!({"altitude_m":1200.,"airspeed_mps":50.,"heading_rad":0.}),
            )?;
            session.execute("sim.step", serde_json::json!({"steps":5600}))?;
        }
        if airborne {
            session.execute("avionics.set",serde_json::json!({"setting":{"kind":"glass","setting":{"kind":"direct_to","airport":"KMMU"}}}))?;
            session.execute("avionics.set",serde_json::json!({"setting":{"kind":"autopilot","setting":{"kind":"flight_director","on":true}}}))?;
            session.execute("sim.step", serde_json::json!({"steps":1}))?;
        }
        let configuration = session
            .aircraft_configuration()
            .ok_or("missing aircraft")?
            .clone();
        let glass = session.glass_state();
        let mut runtime = InstrumentPanel::default();
        let image = capture(|ui| {
            runtime
                .show(
                    ui,
                    &configuration.panel,
                    InstrumentInput::new(session.sim().systems(), session.sim().readout().time_s)
                        .with_aircraft(&configuration)
                        .with_glass(&glass)
                        .with_autopilot(session.sim().installed_autopilot()),
                    session.flight_generation(),
                )
                .unwrap();
            runtime.show_shared_hosts(ui, &mut session);
        });
        image.save(root().join("previews").join(format!("{name}.png")))?;
        if airborne {
            for (id, x) in [("pfd", 248), ("mfd", 1062)] {
                image::imageops::crop_imm(&image, x, 308, 424, 308)
                    .to_image()
                    .save(root().join("previews").join(format!("in-flight-{id}.png")))?;
            }
        }
    }
    Ok(())
}
