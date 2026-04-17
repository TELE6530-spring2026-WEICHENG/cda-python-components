#####
#
# Reads a capacitive soil moisture sensor via an ADS1115 I2C ADC.
# Capacitive sensors produce HIGHER raw values when dry, lower when wet,
# so the mapping from raw -> % is inverted against the dry/wet calibration
# points configured in PiotConfig.props.
#

import logging

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil

from programmingtheiot.data.SensorData import SensorData
from programmingtheiot.cda.embedded import _HardwareIoManager


class SoilMoistureI2cSensorAdapterTask():

    def __init__(self):
        self.name = ConfigConst.SOIL_MOISTURE_SENSOR_NAME
        self.typeID = ConfigConst.SOIL_MOISTURE_SENSOR_TYPE

        cfg = ConfigUtil()
        self._channel = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.SOIL_ADC_CHANNEL_KEY,
            defaultVal=0,
        )
        self._dryRaw = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.SOIL_DRY_RAW_KEY,
            defaultVal=26000,
        )
        self._wetRaw = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.SOIL_WET_RAW_KEY,
            defaultVal=11000,
        )

        self._lastValue = ConfigConst.DEFAULT_VAL
        self._chan = None
        try:
            self._chan = _HardwareIoManager.get_ads1115_channel(self._channel)
        except Exception:
            logging.exception("Failed to initialize ADS1115 for soil moisture task.")

    def generateTelemetry(self) -> SensorData:
        value = self.getTelemetryValue()
        data = SensorData(typeID=self.typeID, name=self.name)
        data.setValue(value)
        return data

    def getTelemetryValue(self) -> float:
        if self._chan is None:
            try:
                self._chan = _HardwareIoManager.get_ads1115_channel(self._channel)
            except Exception:
                logging.warning("ADS1115 still unavailable; returning cached soil value.")
                return self._lastValue
        try:
            raw = self._chan.value
            self._lastValue = self._rawToPercent(raw)
        except Exception:
            logging.warning("Failed to read ADS1115; returning cached soil value.", exc_info=True)
        return self._lastValue

    def _rawToPercent(self, raw: int) -> float:
        dry = float(self._dryRaw)
        wet = float(self._wetRaw)
        if dry == wet:
            return 0.0
        pct = (dry - float(raw)) / (dry - wet) * 100.0
        if pct < 0.0:
            pct = 0.0
        elif pct > 100.0:
            pct = 100.0
        return pct
