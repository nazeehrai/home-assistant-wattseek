# WattSeek Home Assistant custom integration

This package was built from the WattSeek web API behavior observed in the supplied portal JavaScript and live API responses.

## Install with HACS

1. In HACS, open the menu and select **Custom repositories**.
2. Add `https://github.com/nazeehrai/home-assistant-wattseek` as an **Integration**.
3. Download WattSeek and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → WattSeek**.

## Manual installation

Copy:

    custom_components/wattseek

into:

    /config/custom_components/wattseek

Then restart Home Assistant.

Go to:

    Settings -> Devices & services -> Add integration -> WattSeek

Enter the same WattSeek username/email and password used by the WattSeek app.

## Polling interval

Default: 30 seconds
Allowed: 10–300 seconds

Change it from:

    Settings -> Devices & services -> WattSeek -> Configure

The coordinator interval changes without editing YAML.

## Exposed telemetry

The integration creates sensors for:
- Grid power/voltage/current/frequency
- PV power and PV1 voltage/current/power
- Battery power/voltage/current/SOC/SOH/temperature
- BMS charge/discharge current limits
- Load/output voltage/current/frequency/active power/apparent power/load %
- Daily/monthly/yearly/total grid import, output energy and PV energy
- Inverter online and grid-connected binary sensors

## Exposed controls

The integration discovers the inverter's WattSeek command protocol dynamically.
- SELECT commands become Home Assistant select entities.
- Two-state OFF/ON or Disable/Enable commands become switches.
- INPUT commands become number entities with ranges derived from WattSeek protocol metadata.

Commands considered risky, such as factory reset / inverter remote-control style commands, are disabled by default in the entity registry when applicable.

## Notes

This is an unofficial custom integration and not affiliated with WattSeek.
WattSeek is a cloud service, so upstream API changes can break the integration.

After a control command succeeds, the integration reads the command value back
from WattSeek before refreshing Home Assistant. This avoids displaying the old
value while the cloud is still processing the write.

Battery power is normalized for Home Assistant energy-flow cards: positive
means charging and negative means discharging.

For the Sunsynk Power Flow Card, map the generated WattSeek sensor entities to the card's corresponding PV, grid, battery and load fields.
