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
                else:
                    logging.warning(
                        "No valid actuator type. Ignoring actuation for type: %s",
                        data.getTypeID(),
                    )

                # TODO: in a later lab module, the responseData instance will be
                # passed to a callback function implemented in DeviceDataManager
                # via IDataMessageListener

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
        if not self.useEmulator:
            if self.useSimulator:
                self.humidifierActuator = HumidifierActuatorSimTask()
                self.hvacActuator = HvacActuatorSimTask()
