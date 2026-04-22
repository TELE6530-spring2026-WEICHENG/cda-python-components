#####
#
# Drives a water pump through a JQC-3FF relay module with a CDA-autonomous
# irrigation session: short pulses + settle time + soil-moisture readback,
# repeated until the target moisture is reached or a safety cap trips.
#
# Responses are emitted in four phases via ActuatorData.stateData (JSON):
#   OPENED     — session accepted, first pulse about to start
#   PROGRESS   — after each pulse + settle, with latest moisture reading
#   COMPLETED  — target moisture reached
#   ABORTED    — cancelled, timed out, or hit max-pulse cap (see "reason")
#
# Safety watchdog still re-arms on every pulse so a crashed session thread
# can't leave the pump latched on.
#

import json
import logging
import threading
import time
import uuid

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil

from programmingtheiot.data.ActuatorData import ActuatorData

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
        self._pulseOn = cfg.getFloat(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.PUMP_PULSE_ON_SECONDS_KEY,
            defaultVal=ConfigConst.DEFAULT_PUMP_PULSE_ON_SECONDS,
        )
        self._settle = cfg.getFloat(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.PUMP_SETTLE_SECONDS_KEY,
            defaultVal=ConfigConst.DEFAULT_PUMP_SETTLE_SECONDS,
        )
        self._maxPulses = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.PUMP_MAX_PULSES_KEY,
            defaultVal=ConfigConst.DEFAULT_PUMP_MAX_PULSES,
        )
        self._maxSessionSeconds = cfg.getInteger(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.PUMP_MAX_SESSION_SECONDS_KEY,
            defaultVal=ConfigConst.DEFAULT_PUMP_MAX_SESSION_SECONDS,
        )

        self._safetyTimer = None
        self._device = None
        try:
            self._device = _HardwareIoManager.get_output_device(
                self._pin, active_high=not self._activeLow, initial_value=False,
            )
        except Exception:
            logging.exception("Failed to initialize pump relay on BCM pin %d.", self._pin)

        self._soilSensor = None
        self._responseCallback = None

        self._sessionLock = threading.RLock()
        self._sessionId = None
        self._sessionThread = None
        self._cancelEvent = None

    def setSoilSensor(self, sensor):
        self._soilSensor = sensor

    def setResponseCallback(self, cb):
        self._responseCallback = cb

    def updateActuator(self, data: ActuatorData) -> ActuatorData:
        if not data or data.getTypeID() != self.typeID:
            return None

        target = float(data.getValue() or 0.0)
        sessionId, _action = self._parseCommandState(data.getStateData())
        curCommand = data.getCommand()

        with self._sessionLock:
            if curCommand == ConfigConst.COMMAND_OFF:
                self._cancelRunningSession()
                return None

            if curCommand != ConfigConst.COMMAND_ON:
                logging.warning("[PUMP] unknown command %s; ignoring.", curCommand)
                return None

            if (
                sessionId
                and self._sessionId == sessionId
                and self._sessionThread
                and self._sessionThread.is_alive()
            ):
                logging.debug("[PUMP] duplicate START for session %s; ignoring.", sessionId)
                return None

            if self._sessionThread and self._sessionThread.is_alive():
                self._cancelRunningSession()

            sid = sessionId or uuid.uuid4().hex[:8]
            current = self._readMoisture()

            if current >= target:
                logging.info(
                    "[PUMP] already at target (%.1f%% >= %.1f%%); skipping session %s.",
                    current, target, sid,
                )
                return self._buildResponse(
                    statusCode=0, phase="COMPLETED", sessionId=sid,
                    pulseCount=0, currentMoisture=current,
                    targetMoisture=target, command=ConfigConst.COMMAND_OFF,
                )

            self._sessionId = sid
            self._cancelEvent = threading.Event()
            self._sessionThread = threading.Thread(
                target=self._runSession,
                args=(sid, target, self._cancelEvent),
                daemon=True,
                name="WaterPumpSession",
            )
            self._sessionThread.start()

            logging.info(
                "[PUMP] session %s started: target=%.1f%%, current=%.1f%%.",
                sid, target, current,
            )
            return self._buildResponse(
                statusCode=0, phase="OPENED", sessionId=sid,
                pulseCount=0, currentMoisture=current,
                targetMoisture=target, command=ConfigConst.COMMAND_ON,
            )

    def _runSession(self, sid: str, target: float, cancel: threading.Event):
        start = time.monotonic()
        pulseCount = 0
        current = self._readMoisture()

        try:
            while not cancel.is_set():
                elapsed = time.monotonic() - start
                if elapsed >= self._maxSessionSeconds:
                    self._emitAsync(self._buildResponse(
                        statusCode=-1, phase="ABORTED", sessionId=sid,
                        pulseCount=pulseCount, currentMoisture=current,
                        targetMoisture=target, reason="MAX_SESSION_TIME",
                        command=ConfigConst.COMMAND_OFF,
                    ))
                    return

                if pulseCount >= self._maxPulses:
                    self._emitAsync(self._buildResponse(
                        statusCode=-1, phase="ABORTED", sessionId=sid,
                        pulseCount=pulseCount, currentMoisture=current,
                        targetMoisture=target, reason="MAX_PULSES",
                        command=ConfigConst.COMMAND_OFF,
                    ))
                    return

                current = self._readMoisture()
                if current >= target:
                    self._emitAsync(self._buildResponse(
                        statusCode=0, phase="COMPLETED", sessionId=sid,
                        pulseCount=pulseCount, currentMoisture=current,
                        targetMoisture=target,
                        command=ConfigConst.COMMAND_OFF,
                    ))
                    return

                self._pumpOn()
                cancelledMidPulse = cancel.wait(self._pulseOn)
                self._pumpOff()
                pulseCount += 1

                if cancelledMidPulse:
                    break

                current = self._readMoisture()
                self._emitAsync(self._buildResponse(
                    statusCode=0, phase="PROGRESS", sessionId=sid,
                    pulseCount=pulseCount, currentMoisture=current,
                    targetMoisture=target,
                    command=ConfigConst.COMMAND_ON,
                ))

                if cancel.wait(self._settle):
                    break

            self._emitAsync(self._buildResponse(
                statusCode=-1, phase="ABORTED", sessionId=sid,
                pulseCount=pulseCount, currentMoisture=current,
                targetMoisture=target, reason="CANCELLED",
                command=ConfigConst.COMMAND_OFF,
            ))
        except Exception:
            logging.exception("[PUMP] session %s crashed.", sid)
            try:
                self._emitAsync(self._buildResponse(
                    statusCode=-1, phase="ABORTED", sessionId=sid,
                    pulseCount=pulseCount, currentMoisture=current,
                    targetMoisture=target, reason="INTERNAL_ERROR",
                    command=ConfigConst.COMMAND_OFF,
                ))
            except Exception:
                pass
        finally:
            self._pumpOff()

    def _cancelRunningSession(self):
        # caller holds self._sessionLock
        if self._cancelEvent:
            self._cancelEvent.set()
        t = self._sessionThread
        if t and t.is_alive():
            # Thread cleanup does not require the lock, so join here is safe.
            t.join(timeout=self._pulseOn + 2.0)
        self._sessionId = None
        self._sessionThread = None
        self._cancelEvent = None
        self._pumpOff()

    def _parseCommandState(self, stateData):
        if not stateData:
            return None, None
        try:
            obj = json.loads(stateData)
            if not isinstance(obj, dict):
                return None, None
            return obj.get("sessionId"), obj.get("action")
        except Exception:
            return None, None

    def _readMoisture(self) -> float:
        if self._soilSensor is None:
            return 0.0
        try:
            return float(self._soilSensor.getTelemetryValue())
        except Exception:
            logging.warning("[PUMP] failed to read soil moisture.", exc_info=True)
            return 0.0

    def _buildResponse(self, statusCode, phase, sessionId, pulseCount,
                       currentMoisture, targetMoisture, command, reason=None):
        payload = {
            "phase": phase,
            "sessionId": sessionId,
            "pulseCount": pulseCount,
            "currentMoisture": round(float(currentMoisture), 2),
            "targetMoisture": round(float(targetMoisture), 2),
            "reason": reason,
        }
        resp = ActuatorData(typeID=self.typeID, name=self.name)
        resp.setCommand(command)
        resp.setValue(float(targetMoisture))
        resp.setStateData(json.dumps(payload))
        resp.setStatusCode(statusCode)
        resp.setAsResponse()
        self.latestActuatorResponse.updateData(resp)
        return resp

    def _emitAsync(self, response: ActuatorData):
        if self._responseCallback:
            try:
                self._responseCallback(response)
            except Exception:
                logging.exception("[PUMP] response callback failed.")
        else:
            logging.warning(
                "[PUMP] no response callback wired; dropping async response: %s",
                response.getStateData(),
            )

    def _pumpOn(self):
        if self._device is None:
            logging.warning("[PUMP] no device; cannot turn ON.")
            return
        try:
            self._device.on()
            self._armSafetyTimer()
        except Exception:
            logging.exception("[PUMP] failed to turn ON.")

    def _pumpOff(self):
        self._cancelSafetyTimer()
        if self._device is None:
            return
        try:
            self._device.off()
        except Exception:
            logging.exception("[PUMP] failed to turn OFF.")

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
        except Exception:
            logging.exception("[PUMP] safety shut-off failed.")

    def close(self):
        with self._sessionLock:
            self._cancelRunningSession()
        try:
            _HardwareIoManager.release_output_device(self._pin)
        except Exception:
            pass
        self._device = None
