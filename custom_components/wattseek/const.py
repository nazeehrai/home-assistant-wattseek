DOMAIN = "wattseek"
PLATFORMS = ["sensor", "binary_sensor", "select", "number", "switch"]

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 30
MIN_UPDATE_INTERVAL = 10
MAX_UPDATE_INTERVAL = 300

BASE_URL = "https://solar.wattseek.com"
API_PREFIX = "/apis/common/proxy/sysApiCommon"

DANGEROUS_COMMAND_NAMES = {
    "Remote control",
    "Recover default setting",
    "Equalizing enable instantly",
}

FLOW_SENSOR_MAP = {
    "gridPower": ("Grid Power", "W", "power"),
    "pvPower": ("PV Power", "W", "power"),
    "loadPower": ("Load Power", "W", "power"),
    "batteryPower": ("Battery Power", "W", "power"),
    "realTimeSOC": ("Battery SOC", "%", "battery"),
}

DETAIL_SENSOR_NAMES = {
    "Grid voltage": ("Grid Voltage", "V", "voltage"),
    "Grid current": ("Grid Current", "A", "current"),
    "Grid frequency": ("Grid Frequency", "Hz", "frequency"),
    "PV1 voltage": ("PV1 Voltage", "V", "voltage"),
    "PV1 current": ("PV1 Current", "A", "current"),
    "PV1 power": ("PV1 Power", "W", "power"),
    "Battery voltage": ("Battery Voltage", "V", "voltage"),
    "Battery current": ("Battery Current", "A", "current"),
    "Battery capacity(Percentage)": ("Battery Capacity", "%", "battery"),
    "BMS-Real time SOC": ("BMS SOC", "%", "battery"),
    "BMS-Average SOH": ("Battery SOH", "%", None),
    "BMS-Single core maximum temperature": ("Battery Max Temperature", "°C", "temperature"),
    "BMS-Maximum charging current": ("BMS Maximum Charging Current", "A", "current"),
    "BMS-Maximum discharge current": ("BMS Maximum Discharge Current", "A", "current"),
    "Output voltage": ("Output Voltage", "V", "voltage"),
    "Output current": ("Output Current", "A", "current"),
    "Output frequency": ("Output Frequency", "Hz", "frequency"),
    "Output active power": ("Output Active Power", "W", "power"),
    "Output apparent power": ("Output Apparent Power", "VA", "apparent_power"),
    "Output percentage": ("Output Percentage", "%", None),
    "Electricity purchased of the day": ("Grid Import Today", "kWh", "energy"),
    "Electricity purchased of the month": ("Grid Import Month", "kWh", "energy"),
    "Electricity purchased of the year": ("Grid Import Year", "kWh", "energy"),
    "Total electricity purchased": ("Grid Import Total", "kWh", "energy"),
    "Electricity outputed of the day": ("Output Energy Today", "kWh", "energy"),
    "Electricity outputed of the month": ("Output Energy Month", "kWh", "energy"),
    "Electricity outputed of the year": ("Output Energy Year", "kWh", "energy"),
    "Total electricity outputed": ("Output Energy Total", "kWh", "energy"),
    "PV power generation of the day": ("PV Energy Today", "kWh", "energy"),
    "PV power generation of the month": ("PV Energy Month", "kWh", "energy"),
    "PV power generation of the year": ("PV Energy Year", "kWh", "energy"),
    "Total PV power generation": ("PV Energy Total", "kWh", "energy"),
}
