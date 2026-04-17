#####
#
# End-to-end liveness LED driven by GDA ActuatorCmd (typeID=2001).
# Watchdog turns the LED off if no command arrives within the timeout,
# giving a visible signal when the GDA->MQTT->CDA path is broken.
#
# LED boots OFF and only lights on an explicit COMMAND_ON from the GDA.
#

import logging
import threading

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil

from programmingtheiot.cda.sim.BaseActuatorSimTask import BaseActuatorSimTask
from programmingtheiot.cda.embedded import _HardwareIoManager

from programmingtheiot.data.ActuatorData import ActuatorData


class LedActuatorAdapterTask(BaseActuatorSimTask):

    def __init__(self):
        super(LedActuatorAdapterTask, self).__init__(
            name=ConfigConst.LED_ACTUATOR_NAME,
            typeID=ConfigConst.LED_DISPLAY_ACTUATOR_TYPE,
            simpleName="Led",
        )
        cfg = ConfigUtil()
        self._pin = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.LED_GPIO_PIN_KEY,
            defaultVal=22,
        )
        self._timeoutSecs = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.LED_WATCHDOG_TIMEOUT_SECS_KEY,
            defaultVal=ConfigConst.DEFAULT_LED_WATCHDOG_TIMEOUT_SECS,
        )
        self._watchdog = None
        self._watchdogLock = threading.Lock()

        self._device = None
        try:
            self._device = _HardwareIoManager.get_output_device(
                self._pin, active_high=True, initial_value=False,
            )
        except Exception:
            logging.exception("Failed to initialize LED on BCM pin %d.", self._pin)

    def updateActuator(self, data: ActuatorData) -> ActuatorData:
        # Reset watchdog on every typeID=2001 command, even if the base class
        # suppresses it as a repeat - the repeat itself is the liveness signal.
        if data and data.getTypeID() == self.typeID and not data.isResponseFlagEnabled():
            self._reset_watchdog()
        return super(LedActuatorAdapterTask, self).updateActuator(data)

    def _activateActuator(self, val=ConfigConst.DEFAULT_VAL, stateData=None) -> int:
        if self._device is None:
            logging.warning("[LED] no device; cannot turn ON.")
            return -1
        try:
            self._device.on()
            logging.info("[LED] ON state=%s", stateData)
            return 0
        except Exception:
            logging.exception("[LED] failed to turn ON.")
            return -1

    def _deactivateActuator(self, val=ConfigConst.DEFAULT_VAL, stateData=None) -> int:
        self._cancel_watchdog()
        if self._device is None:
            logging.warning("[LED] no device; cannot turn OFF.")
            return -1
        try:
            self._device.off()
            logging.info("[LED] OFF state=%s", stateData)
            return 0
        except Exception:
            logging.exception("[LED] failed to turn OFF.")
            return -1

    def _reset_watchdog(self):
        with self._watchdogLock:
            if self._watchdog is not None:
                self._watchdog.cancel()
            self._watchdog = threading.Timer(self._timeoutSecs, self._on_timeout)
            self._watchdog.daemon = True
            self._watchdog.start()

    def _cancel_watchdog(self):
        with self._watchdogLock:
            if self._watchdog is not None:
                self._watchdog.cancel()
                self._watchdog = None

    def _on_timeout(self):
        logging.warning(
            "[LED] watchdog timeout after %ds - E2E path from GDA may be broken; turning LED off.",
            self._timeoutSecs,
        )
        if self._device is not None:
            try:
                self._device.off()
            except Exception:
                logging.exception("[LED] failed to turn OFF on watchdog timeout.")

    def close(self):
        self._cancel_watchdog()
        _HardwareIoManager.release_output_device(self._pin)
        self._device = None
