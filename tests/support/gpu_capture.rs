use eframe::egui;
use sling2_fidelity::Error;
use std::sync::{Arc, mpsc};

// Offscreen application rendering: callbacks, font atlas, and meshes share one GPU target.
pub fn capture(
    mut paint: impl FnMut(&mut egui::Ui) -> Result<(), Error>,
) -> Result<image::RgbaImage, Error> {
    let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
        backends: wgpu::Backends::VULKAN | wgpu::Backends::GL,
        ..Default::default()
    });
    let adapter =
        pollster::block_on(instance.request_adapter(&wgpu::RequestAdapterOptions::default()))?;
    let (device, queue) = pollster::block_on(adapter.request_device(&wgpu::DeviceDescriptor {
        required_limits: wgpu::Limits::downlevel_defaults(),
        ..Default::default()
    }))?;
    let format = wgpu::TextureFormat::Rgba8Unorm;
    let renderer = egui_wgpu::Renderer::new(&device, format, Default::default());
    let gpu = egui_wgpu::RenderState {
        adapter,
        available_adapters: Vec::new(),
        device,
        queue,
        target_format: format,
        renderer: Arc::new(egui::mutex::RwLock::new(renderer)),
    };
    let context = egui::Context::default();
    flightcraft_ui::theme::install(&context);
    flightcraft_render::initialize(&gpu, flightcraft_ui::theme::scene());
    flightcraft_render::initialize_synthetic_vision(&gpu, &context);
    context.set_pixels_per_point(1.);
    let texture = gpu.device.create_texture(&wgpu::TextureDescriptor {
        label: Some("Panel review"),
        size: wgpu::Extent3d {
            width: 1728,
            height: 968,
            depth_or_array_layers: 1,
        },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
        view_formats: &[],
    });
    gpu.device.push_error_scope(wgpu::ErrorFilter::Validation);
    for frame in 0..4 {
        let mut error = None;
        let output = context.run(
            egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(1728., 968.),
                )),
                time: Some(f64::from(frame) / 120.),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::new().fill(flightcraft_ui::theme::BACKGROUND))
                    .show(ctx, |ui| {
                        if let Err(e) = paint(ui) {
                            error = Some(e);
                        }
                    });
            },
        );
        if let Some(e) = error {
            return Err(e);
        }
        let jobs = context.tessellate(output.shapes, output.pixels_per_point);
        let screen = egui_wgpu::ScreenDescriptor {
            size_in_pixels: [1728, 968],
            pixels_per_point: output.pixels_per_point,
        };
        let mut renderer = gpu.renderer.write();
        for (id, delta) in &output.textures_delta.set {
            renderer.update_texture(&gpu.device, &gpu.queue, *id, delta);
        }
        let mut encoder = gpu.device.create_command_encoder(&Default::default());
        let commands =
            renderer.update_buffers(&gpu.device, &gpu.queue, &mut encoder, &jobs, &screen);
        let view = texture.create_view(&Default::default());
        {
            let attachment = wgpu::RenderPassColorAttachment {
                view: &view,
                resolve_target: None,
                depth_slice: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(wgpu::Color::BLACK),
                    store: wgpu::StoreOp::Store,
                },
            };
            let mut pass = encoder
                .begin_render_pass(&wgpu::RenderPassDescriptor {
                    color_attachments: &[Some(attachment)],
                    ..Default::default()
                })
                .forget_lifetime();
            renderer.render(&mut pass, &jobs, &screen);
        }
        gpu.queue
            .submit(commands.into_iter().chain([encoder.finish()]));
        for id in &output.textures_delta.free {
            renderer.free_texture(id);
        }
        gpu.device.poll(wgpu::PollType::wait_indefinitely())?;
    }
    assert!(
        flightcraft_render::synthetic_vision_stats(&gpu).terrain_passes > 0,
        "synthetic terrain did not render"
    );
    let stride = (1728_u32 * 4).div_ceil(256) * 256;
    let buffer = gpu.device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Panel pixels"),
        size: u64::from(stride) * 968,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });
    let mut encoder = gpu.device.create_command_encoder(&Default::default());
    encoder.copy_texture_to_buffer(
        texture.as_image_copy(),
        wgpu::TexelCopyBufferInfo {
            buffer: &buffer,
            layout: wgpu::TexelCopyBufferLayout {
                offset: 0,
                bytes_per_row: Some(stride),
                rows_per_image: Some(968),
            },
        },
        wgpu::Extent3d {
            width: 1728,
            height: 968,
            depth_or_array_layers: 1,
        },
    );
    gpu.queue.submit([encoder.finish()]);
    let (send, receive) = mpsc::channel();
    buffer
        .slice(..)
        .map_async(wgpu::MapMode::Read, move |result| {
            let _ = send.send(result);
        });
    gpu.device.poll(wgpu::PollType::wait_indefinitely())?;
    receive.recv()??;
    let mapped = buffer.slice(..).get_mapped_range();
    let mut pixels = Vec::with_capacity(1728 * 968 * 4);
    for row in mapped.chunks(stride as usize) {
        pixels.extend_from_slice(row.get(..1728 * 4).ok_or("short readback row")?);
    }
    let image = image::RgbaImage::from_raw(1728, 968, pixels).ok_or("invalid readback image")?;
    drop(mapped);
    buffer.unmap();
    if let Some(error) = pollster::block_on(gpu.device.pop_error_scope()) {
        return Err(error.into());
    }
    Ok(image)
}
