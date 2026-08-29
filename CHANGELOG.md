# Changelog

## 0.3.0

- Discover plants and allow explicit selection of each inverter while excluding dataloggers.
- Build setting groups, labels, controls, options, units, precision, ranges and linkages dynamically from WattSeek protocol JSON.
- Stage setting edits locally and expose one Submit button plus pending-change sensor per discovered group.
- Submit complete groups atomically, issue WattSeek's inverter-facing group `READ`, then refresh command values and protocol metadata.
- Normalize battery power to negative while charging and positive while discharging, using battery current for direction.
- Migrate existing entries to explicit plant and inverter identifiers without changing entity unique IDs.

## 0.2.0

- Confirm writable command values through bounded cloud readback before refreshing entities.
- Add battery-power support for energy-flow dashboards.
- Add HACS metadata, repository branding, validation and release documentation.

## 0.1.0

- Initial WattSeek cloud integration.

