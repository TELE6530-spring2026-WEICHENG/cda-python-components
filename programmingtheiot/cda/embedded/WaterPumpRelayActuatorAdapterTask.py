#####
#
# Drives a water pump through a JQC-3FF relay module.
#
# Adds a safety watchdog: if the pump stays ON for more than
# waterPumpMaxOnSeconds, a background timer forces it OFF. This
# prevents a stuck ON state (crashed gateway, missed OFF command)
# from running the pump dry or flooding the setup.
#

import logging
import threading

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil

from programmingtheiot.cda.sim.BaseActuatorSimTask import BaseActuatorSimTask
from programmingtheiot.cda.embedded import _HardwareIoManager


class WaterPumpRelayActuatorAdapterTask(BaseActuatorSimTask):

    def __init__(self):
        super(WaterPumpRelayActuatorAdapterTask, self).__init__(
            name=ConfigConst.WATER_PUMP_ACTUATOR_NAME,
            typeID=ConfigConst.WATER_PUMP_ACTUATOR_TYPE,
            simpleName="WaterPump",
        )
        cfg = ConfigUtil()
        self._pin = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.PUMP_GPIO_PIN_KEY,
            defaultVal=27,
        )
        self._activeLow = cfg.getBoolean(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.RELAY_ACTIVE_LOW_KEY,
        )
        self._maxOnSeconds = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.PUMP_MAX_ON_SECONDS_KEY,
            defaultVal=30,
        )
        self._safetyTimer = None
        self._device = None
        try:
            self._device = _HardwareIoManager.get_output_device(
                self._pin, active_high=not self._activeLow, initial_value=False,
            )
        except Exception:
            logging.exception("Failed to initialize pump relay on BCM pin %d.", self._pin)

    def _activateActuator(self, val=ConfigConst.DEFAULT_VAL, stateData=None) -> int:
        if self._device is None:
            logging.warning("[PUMP] no device; cannot turn ON.")
            return -1
        try:
            self._device.on()
            logging.info("[PUMP] ON state=%s (auto-off in %ds)", stateData, self._maxOnSeconds)
            self._armSafetyTimer()
            return 0
        except Exception:
            logging.exception("[PUMP] failed to turn ON.")
            return -1

    def _deactivateActuator(self, val=ConfigConst.DEFAULT_VAL, stateData=None) -> int:
        self._cancelSafetyTimer()
        if self._device is None:
            logging.warning("[PUMP] no device; cannot turn OFF.")
            return -1
        try:
            self._device.off()
            logging.info("[PUMP] OFF state=%s", stateData)
            return 0
        except Exception:
            logging.exception("[PUMP] failed to turn OFF.")
            return -1

    def _armSafetyTimer(self):
        self._cancelSafetyTimer()
        if self._maxOnSeconds <= 0:
            return
        self._safetyTimer = threading.Timer(self._maxOnSeconds, self._safetyShutOff)
        self._safetyTimer.daemon = True
        self._safetyTimer.start()

    def _cancelSafetyTimer(self):
        if self._safetyTimer is not None:
            self._safetyTimer.cancel()
            self._safetyTimer = None

    def _safetyShutOff(self):
        logging.warning("[PUMP] safety timer fired; forcing OFF after %ds.", self._maxOnSeconds)
        try:
            if self._device is not None:
                self._device.off()
            self.lastKnownCommand = ConfigConst.COMMAND_OFF
        except Exception:
            logging.exception("[PUMP] safety shut-off failed.")

    def close(self):
        self._cancelSafetyTimer()
        _HardwareIoManager.release_output_device(self._pin)
        self._device = None
