# Private artwork boundary

This public pack contains only original FlightCraft display artwork and plain labels. Private artwork must live in a separate private repository. The base pack's installation identifiers, hardware rectangles, and screen roles are stable; `data/skin-slots.json` records that contract in millimetres.

The private repository should depend on this pack, create a uniquely named panel layer, retain every existing installation's position and size, and create a uniquely named aircraft selection referencing `sling2-912is`. Packs cannot replace an installed definition under its existing identifier. Load the public pack first, then the private derivative. Logos belong exclusively to that derivative's resources.

The engine's conventional instruments support `Registry::register_skin`, `Registry::register_pack_skin`, and host-side registration before selecting the panel. Its declarative equipment panel currently bypasses that registry: `touch_display`, `navigator`, `standby`, and `autopilot` equipment elements have no `skin` field. Therefore **replacing these equipment screen skins requires a host equipment-skin hook**. Adding an unknown `skin` field to this pack will fail validation. The slot contract is a prepared extension boundary, not a claim that an ordinary private JSON pack can already replace those screens.

A future host should resolve artwork by panel installation id, pass the existing read-only equipment snapshot to the selected painter, retain command hit regions and shared navigation, and default to the existing original skin. Private artwork must not implement flight, receiver, or autopilot behaviour. No change to public layout coordinates is necessary for that hook.
