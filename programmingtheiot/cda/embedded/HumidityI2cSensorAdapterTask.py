#####
#
# Reads relative humidity from an AHT20 sensor on the I2C bus.
#

import logging

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.data.SensorData import SensorData
from programmingtheiot.cda.embedded import _HardwareIoManager


class HumidityI2cSensorAdapterTask():

    def __init__(self):
        self.name = ConfigConst.HUMIDITY_SENSOR_NAME
        self.typeID = ConfigConst.HUMIDITY_SENSOR_TYPE
        self._lastValue = ConfigConst.DEFAULT_VAL
        self._sensor = None
        try:
            self._sensor = _HardwareIoManager.get_aht20()
        except Exception:
            logging.exception("Failed to initialize AHT20 for humidity task.")

    def generateTelemetry(self) -> SensorData:
        value = self.getTelemetryValue()
        data = SensorData(typeID=self.typeID, name=self.name)
        data.setValue(value)
        return data

    def getTelemetryValue(self) -> float:
        if self._sensor is None:
            try:
                self._sensor = _HardwareIoManager.get_aht20()
            except Exception:
                logging.warning("AHT20 still unavailable; returning cached humidity value.")
                return self._lastValue
        try:
            self._lastValue = float(self._sensor.relative_humidity)
        except Exception:
            logging.warning("Failed to read AHT20 humidity; returning cached value.", exc_info=True)
        return self._lastValue
