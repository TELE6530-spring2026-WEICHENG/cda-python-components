#####
#
# Drives a fan through a JQC-3FF relay module using gpiozero on a
# single BCM pin. Extends BaseActuatorSimTask so the ON/OFF state
# machine, repeat suppression and ActuatorData response building all
# come from the existing base implementation - we only override the
# two hooks that touch physical hardware.
#

import logging

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil

from programmingtheiot.cda.sim.BaseActuatorSimTask import BaseActuatorSimTask
from programmingtheiot.cda.embedded import _HardwareIoManager


class FanRelayActuatorAdapterTask(BaseActuatorSimTask):

    def __init__(self):
        super(FanRelayActuatorAdapterTask, self).__init__(
            name=ConfigConst.FAN_ACTUATOR_NAME,
            typeID=ConfigConst.FAN_ACTUATOR_TYPE,
            simpleName="Fan",
        )
        cfg = ConfigUtil()
        self._pin = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.FAN_GPIO_PIN_KEY,
            defaultVal=17,
        )
        self._activeLow = cfg.getBoolean(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.RELAY_ACTIVE_LOW_KEY,
        )
        self._device = None
        try:
            self._device = _HardwareIoManager.get_output_device(
                self._pin, active_high=not self._activeLow, initial_value=False,
            )
        except Exception:
            logging.exception("Failed to initialize fan relay on BCM pin %d.", self._pin)

    def _activateActuator(self, val=ConfigConst.DEFAULT_VAL, stateData=None) -> int:
        if self._device is None:
            logging.warning("[FAN] no device; cannot turn ON.")
            return -1
        try:
            self._device.on()
            logging.info("[FAN] ON state=%s", stateData)
            return 0
        except Exception:
            logging.exception("[FAN] failed to turn ON.")
            return -1

    def _deactivateActuator(self, val=ConfigConst.DEFAULT_VAL, stateData=None) -> int:
        if self._device is None:
            logging.warning("[FAN] no device; cannot turn OFF.")
            return -1
        try:
            self._device.off()
            logging.info("[FAN] OFF state=%s", stateData)
            return 0
        except Exception:
            logging.exception("[FAN] failed to turn OFF.")
            return -1

    def close(self):
        _HardwareIoManager.release_output_device(self._pin)
        self._device = None
