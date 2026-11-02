//! Local review artifacts from actual rendered pixels. Reference-derived files never enter the pack.
use image::{GrayImage, Luma, Rgba, RgbaImage};
use serde_json::json;
use sling2_fidelity::Error;
use std::{
    path::PathBuf,
    process::{Command, Stdio},
};

fn edges(image: &RgbaImage) -> GrayImage {
    let gray = image::DynamicImage::ImageRgba8(image.clone()).to_luma8();
    let mut out = GrayImage::new(image.width(), image.height());
    for (x, y, pixel) in out.enumerate_pixels_mut() {
        if x == 0 || y == 0 || x + 1 == image.width() || y + 1 == image.height() {
            continue;
        }
        let mut dx = 0_i32;
        let mut dy = 0_i32;
        for row in -1_i32..=1 {
            for column in -1_i32..=1 {
                let intensity = i32::from(
                    gray.get_pixel((x as i32 + column) as u32, (y as i32 + row) as u32)
                        .0[0],
                );
                dx += column * if row == 0 { 2 } else { 1 } * intensity;
                dy += row * if column == 0 { 2 } else { 1 } * intensity;
            }
        }
        *pixel = Luma([if dx.abs() + dy.abs() > 160 { 255 } else { 0 }]);
    }
    out
}
fn score(a: &GrayImage, b: &GrayImage, [x, y, w, h]: [u32; 4]) -> f64 {
    let mut total = 0_u64;
    let mut matched = 0_u64;
    for (source, target) in [(a, b), (b, a)] {
        for sy in y..(y + h).min(source.height()) {
            for sx in x..(x + w).min(source.width()) {
                if source.get_pixel(sx, sy).0[0] == 0 {
                    continue;
                }
                total += 1;
                let near = (sy.saturating_sub(4).max(y)
                    ..=(sy + 4).min(y + h - 1).min(source.height() - 1))
                    .any(|yy| {
                        (sx.saturating_sub(4).max(x)
                            ..=(sx + 4).min(x + w - 1).min(source.width() - 1))
                            .any(|xx| target.get_pixel(xx, yy).0[0] != 0)
                    });
                if near {
                    matched += 1;
                }
            }
        }
    }
    if total == 0 {
        0.
    } else {
        matched as f64 / total as f64
    }
}

pub fn write(
    render: &RgbaImage,
    panel: &flightcraft_aero::modern::EquipmentPanel,
) -> Result<(), Error> {
    let Some(reference) = std::env::var_os("SLING2_REFERENCE_PANEL") else {
        return Ok(());
    };
    let output = PathBuf::from(
        std::env::var_os("SLING2_COMPARE_OUTPUT")
            .ok_or("comparison output required with reference")?,
    );
    std::fs::create_dir_all(&output)?;
    let output = output.canonicalize()?;
    // Ask Git about the checkout, rather than treating an empty marker directory as a repository.
    let inside = Command::new("git")
        .arg("-C")
        .arg(&output)
        .args(["rev-parse", "--show-toplevel"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()?;
    if inside.success() {
        return Err("comparison output is inside a Git checkout".into());
    }
    let reference = PathBuf::from(reference).canonicalize()?;
    for name in [
        "render.png",
        "side-by-side.png",
        "overlay.png",
        "edge-difference.png",
        "alignment.json",
    ] {
        let dest = output.join(name);
        if std::fs::symlink_metadata(&dest).is_ok_and(|m| m.file_type().is_symlink())
            || dest == reference
        {
            return Err("unsafe comparison output file".into());
        }
    }
    let mut reader = image::ImageReader::open(reference)?.with_guessed_format()?;
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(8192);
    limits.max_image_height = Some(8192);
    limits.max_alloc = Some(128 * 1024 * 1024);
    reader.limits(limits);
    let reference = reader.decode()?.to_rgba8();
    if reference.dimensions() != render.dimensions() {
        return Err("comparison dimensions differ".into());
    }
    let (w, h) = render.dimensions();
    let mut side = RgbaImage::new(w * 2, h);
    image::imageops::replace(&mut side, &reference, 0, 0);
    image::imageops::replace(&mut side, render, i64::from(w), 0);
    let mut overlay = render.clone();
    let mut difference = render.clone();
    let a = edges(&reference);
    let b = edges(render);
    for (x, y, p) in overlay.enumerate_pixels_mut() {
        for (dst, src) in p.0.iter_mut().zip(reference.get_pixel(x, y).0) {
            *dst = ((u16::from(*dst) + u16::from(src)) / 2) as u8;
        }
        let [av] = a.get_pixel(x, y).0;
        let [bv] = b.get_pixel(x, y).0;
        difference.put_pixel(x, y, Rgba([av, bv, av.abs_diff(bv), 255]));
    }
    let [pw, ph] = panel.size;
    let scale = (f64::from(w) / pw).min(f64::from(h) / ph);
    let left = (f64::from(w) - pw * scale) / 2.;
    let top = (f64::from(h) - ph * scale) / 2.;
    let installations: Vec<_> = panel
        .elements
        .iter()
        .map(|e| {
            let [x, y] = e.position;
            let [w, h] = e.size;
            let rect = [
                (left + x * scale).round() as u32,
                (top + y * scale).round() as u32,
                (w * scale).round() as u32,
                (h * scale).round() as u32,
            ];
            json!({"installation":e.id,"rect_px":rect,"edge_alignment":score(&a,&b,rect)})
        })
        .collect();
    let report = json!({"method":"Symmetric Sobel-edge proximity within four pixels; appearance-sensitive, including different public display artwork.","engine_panel_compare_completed":false,"engine_tool_error":"Output guard treats empty Git marker directories as repositories.","render":"Actual in-flight GPU panel, including synthetic terrain.","installations":installations,"face_sample":{"pixel":[730,275],"reference_rgba":reference.get_pixel(730,275).0,"render_rgba":render.get_pixel(730,275).0}});
    std::fs::write(
        output.join("alignment.json"),
        serde_json::to_string_pretty(&report)?,
    )?;
    render.save(output.join("render.png"))?;
    side.save(output.join("side-by-side.png"))?;
    overlay.save(output.join("overlay.png"))?;
    difference.save(output.join("edge-difference.png"))?;
    Ok(())
}
