#####
#
# This class is part of the Programming the Internet of Things
# project, and is available via the MIT License, which can be
# found in the LICENSE file at the top level of this repository.
#
# You may find it more helpful to your design to adjust the
# functionality, constants and interfaces (if there are any)
# provided within in order to meet the needs of your specific
# Programming the Internet of Things project.
#

import logging

from importlib import import_module

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.IDataMessageListener import IDataMessageListener

from programmingtheiot.data.ActuatorData import ActuatorData

from programmingtheiot.cda.sim.actuator.HvacActuatorSimTask import HvacActuatorSimTask
from programmingtheiot.cda.sim.actuator.HumidifierActuatorSimTask import (
    HumidifierActuatorSimTask,
)


class ActuatorAdapterManager(object):
    """
    Shell representation of class for student implementation.

    """

    def __init__(self, dataMsgListener: IDataMessageListener = None):

        self.dataMsgListener = dataMsgListener
        self.configUtil = ConfigUtil()

        # Get the configuration settings
        self.useSimulator = self.configUtil.getBoolean(
            section=ConfigConst.CONSTRAINED_DEVICE, key=ConfigConst.ENABLE_SIMULATOR_KEY
        )

        self.useEmulator = self.configUtil.getBoolean(
            section=ConfigConst.CONSTRAINED_DEVICE, key=ConfigConst.ENABLE_EMULATOR_KEY
        )

        self.useEmbeddedHw = self.configUtil.getBoolean(
            section=ConfigConst.CONSTRAINED_DEVICE, key=ConfigConst.ENABLE_EMBEDDED_HW_KEY
        )

        self.deviceID = self.configUtil.getProperty(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.DEVICE_LOCATION_ID_KEY,
            defaultVal=ConfigConst.NOT_SET,
        )

        self.locationID = self.configUtil.getProperty(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.DEVICE_LOCATION_ID_KEY,
            defaultVal=ConfigConst.NOT_SET,
        )

        # Actuator references
        self.humidifierActuator = None
        self.hvacActuator = None
        self.ledDisplayActuator = None
        self.fanActuator = None
        self.waterPumpActuator = None

        self._initEnvironmentalActuationTasks()

    def sendActuatorCommand(self, data: ActuatorData) -> ActuatorData:
        # Making sure incoming actuation events are not response messages
        if data and not data.isResponseFlagEnabled():
            # first check if the actuation event is destined for this device
            if data.getLocationID() == self.locationID:
                logging.info(
                    "Actuator command received for location ID %s. Processing...",
                    str(data.getLocationID()),
                )

                aType = data.getTypeID()
                responseData = None

                # Pass corresponding actuation data to the appropriate actuator adapter based on the type ID
                if (
                    aType == ConfigConst.HUMIDIFIER_ACTUATOR_TYPE
                    and self.humidifierActuator
                ):
                    responseData = self.humidifierActuator.updateActuator(data)
                elif aType == ConfigConst.HVAC_ACTUATOR_TYPE and self.hvacActuator:
                    responseData = self.hvacActuator.updateActuator(data)
                elif (
                    aType == ConfigConst.LED_DISPLAY_ACTUATOR_TYPE
                    and self.ledDisplayActuator
                ):
                    responseData = self.ledDisplayActuator.updateActuator(data)
                elif aType == ConfigConst.FAN_ACTUATOR_TYPE and self.fanActuator:
                    responseData = self.fanActuator.updateActuator(data)
                elif (
                    aType == ConfigConst.WATER_PUMP_ACTUATOR_TYPE
                    and self.waterPumpActuator
                ):
                    responseData = self.waterPumpActuator.updateActuator(data)
                else:
                    logging.warning(
                        "No valid actuator type. Ignoring actuation for type: %s",
                        data.getTypeID(),
                    )

                if responseData and self.dataMsgListener:
                    self.dataMsgListener.handleActuatorCommandResponse(responseData)

                return responseData
            else:
                logging.warning(
                    "Location ID doesn't match. Ignoring actuation: (me) %s != (you) %s",
                    str(self.locationID),
                    str(data.getLocationID()),
                )
        else:
            logging.warning(
                "Actuator request received. Message is empty or response. Ignoring."
            )

        return None

    def setDataMessageListener(self, listener: IDataMessageListener) -> bool:
        if listener and isinstance(listener, IDataMessageListener):
            self.dataMsgListener = listener
            return True
        else:
            logging.warning("Invalid data message listener provided.")
            return False

    def _initEnvironmentalActuationTasks(self):
        if self.useEmbeddedHw:
            self._initEmbeddedHardwareActuators()
        elif self.useEmulator:
            self._initEmulatorActuators()
        else:
            self._initSimActuators()

    def _initSimActuators(self):
        if self.useSimulator:
            self.humidifierActuator = HumidifierActuatorSimTask()
            self.hvacActuator = HvacActuatorSimTask()

    def _initEmulatorActuators(self):
        hueModule = import_module(
            "programmingtheiot.cda.emulated.actuator.HumidifierEmulatorTask",
            "HumidifierEmulatorTask",
        )
        hueClazz = getattr(hueModule, "HumidifierEmulatorTask")
        self.humidifierActuator = hueClazz()

        hveModule = import_module(
            "programmingtheiot.cda.emulated.actuator.HvacEmulatorTask",
            "HvacEmulatorTask",
        )
        hveClazz = getattr(hveModule, "HvacEmulatorTask")
        self.hvacActuator = hveClazz()

        leDisplayModule = import_module(
            "programmingtheiot.cda.emulated.LedDisplayEmulatorTask",
            "LedDisplayEmulatorTask",
        )
        leClazz = getattr(leDisplayModule, "LedDisplayEmulatorTask")
        self.ledDisplayActuator = leClazz()

    def _initEmbeddedHardwareActuators(self):
        try:
            from programmingtheiot.cda.embedded.FanRelayActuatorAdapterTask import (
                FanRelayActuatorAdapterTask,
            )
            self.fanActuator = FanRelayActuatorAdapterTask()
        except Exception:
            logging.exception("Failed to init fan relay actuator.")
            self.fanActuator = None

        try:
            from programmingtheiot.cda.embedded.WaterPumpRelayActuatorAdapterTask import (
                WaterPumpRelayActuatorAdapterTask,
            )
            self.waterPumpActuator = WaterPumpRelayActuatorAdapterTask()
        except Exception:
            logging.exception("Failed to init water pump relay actuator.")
            self.waterPumpActuator = None

        enableLed = self.configUtil.getBoolean(
            section=ConfigConst.CONSTRAINED_DEVICE,
            key=ConfigConst.ENABLE_LED_ACTUATOR_KEY,
        )
        if enableLed:
            try:
                from programmingtheiot.cda.embedded.LedActuatorAdapterTask import (
                    LedActuatorAdapterTask,
                )
                self.ledDisplayActuator = LedActuatorAdapterTask()
            except Exception:
                logging.exception("Failed to init LED actuator.")
                self.ledDisplayActuator = None

        # HVAC / humidifier are sim-only fallbacks on this board
        self.humidifierActuator = HumidifierActuatorSimTask()
        self.hvacActuator = HvacActuatorSimTask()
