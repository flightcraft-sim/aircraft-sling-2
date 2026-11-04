# Private artwork boundary

The public panel uses original FlightCraft screens and plain labels. A separate private repository can supply alternative equipment artwork without moving any installation. The stable installation ids and rectangles are recorded in `data/skin-slots.json`.

FlightCraft main revision `3512ca9` adds the equipment artwork hook used here. A private host implements `instruments::EquipmentSkin` and registers each painter using `Registry::register_equipment_skin`. At startup, `Registry::set_equipment_skin` can assign that registered painter to `left_display`, `right_display`, `navigator`, `standby`, or `autopilot`. Host assignment takes precedence over the public panel's default artwork. Alternatively, a private derivative panel can select a registered painter through its installation's `appearance.skin` field. Register the painters before loading that panel; an unknown selected id is an error.

The painter receives the actual installation rectangle and a read-only equipment snapshot. Display pages, navigation, sensor validity, power, autopilot modes, and engine indications must come from that snapshot. The host retains input regions, guards, knob behaviour, starter releases, and the recovery-handle hold. A skin must not implement its own simulation, receiver, or flight-control logic.

A private derivative uses a unique panel id and aircraft selection referencing `sling2-912is`, loads after the public pack, and preserves the existing installation ids and coordinates. Packs cannot replace another installed definition under the same id. Logos and any replica screen artwork belong exclusively to the private resources. None are included in this repository.

## Skin packs for the landscape touch display

Both touch displays use the engine's `landscape_touch_efis` display model, which a skin pack can dress without any code: a directory with a `skin.json` manifest, a palette, short key labels, and an open-licensed font. This pack recommends the public `landscape-touch-efis` skin pack by id (`recommended_skin` in each display's appearance). The reference is soft: if that pack is not installed, the engine's built-in skin shows and nothing fails. A pilot can choose any installed skin per display in Settings.

A private skin goes in a folder outside every repository and is loaded with the `FLIGHTCRAFT_SKINS_DIR` environment variable; it needs `"display_model": "landscape_touch_efis"` and can be recommended by this pack's displays by id in a private derivative panel. Skin packs change appearance only; the display's pages, knobs, and menus are the engine's. A skin that reproduces a manufacturer's screens exactly is never published.
