//! Loading and flight-measurement helpers for the public Sling 2 data pack.
use flightcraft_aero::{AircraftCatalog, PackManifest, ResolvedAircraft};
use std::collections::BTreeMap;

pub type Error = Box<dyn std::error::Error>;
pub const KNOT: f64 = 1852.0 / 3600.0;
pub const G: f64 = 9.80665;

/// Feed precisely the distributed documents through the engine's pack validator.
pub fn catalog() -> Result<AircraftCatalog, Error> {
    let manifest = PackManifest::from_json(include_str!("../pack.json"))?;
    let documents = [
        ("family.json", include_str!("../family.json")),
        ("variant.json", include_str!("../variant.json")),
        ("engine.json", include_str!("../engine.json")),
        ("systems.json", include_str!("../systems.json")),
        ("panel.json", include_str!("../panel.json")),
        ("aircraft.json", include_str!("../aircraft.json")),
    ]
    .into_iter()
    .map(|(name, text)| (name.to_owned(), text.to_owned()))
    .collect::<BTreeMap<_, _>>();
    let mut catalog = AircraftCatalog::builtins()?;
    catalog.install_pack(&manifest, &documents)?;
    Ok(catalog)
}

pub fn configuration() -> Result<ResolvedAircraft, Error> {
    Ok(catalog()?.resolve_aircraft("sling2")?)
}

/// A symmetric, full-gross performance loading, within the published CG limits.
pub fn gross_configuration() -> Result<ResolvedAircraft, Error> {
    let mut config = configuration()?;
    for station in &mut config.load.stations {
        station.mass_kg = if station.station == "pilot" || station.station == "passenger" {
            120.
        } else {
            45.
        };
    }
    config.weight_balance = config.variant.weight_balance(&config.load)?;
    config.aircraft.mass = config.variant.loaded_mass(&config.load)?;
    if !config.weight_balance.in_limits {
        return Err("performance loading outside envelope".into());
    }
    Ok(config)
}

pub fn flight(
    config: &ResolvedAircraft,
    altitude_m: f64,
    speed_mps: f64,
) -> Result<flightcraft_sim::Sim, Error> {
    let mut sim = flightcraft_sim::Sim::new_with_aircraft(
        &flightcraft_sim::Start::Air {
            height_m: altitude_m,
            airspeed_mps: speed_mps,
            heading_rad: 0.,
        },
        config.aircraft.clone(),
    )?;
    sim.configure_systems(config)?;
    Ok(sim)
}
