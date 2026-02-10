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

from decimal import Decimal
from json import JSONEncoder
import json
import logging

from programmingtheiot.data.ActuatorData import ActuatorData
from programmingtheiot.data.SensorData import SensorData
from programmingtheiot.data.SystemPerformanceData import SystemPerformanceData


class DataUtil:
    """
    Shell representation of class for student implementation.

    """

    def __init__(self, encodeToUtf8=False):
        self.encodeToUtf8 = encodeToUtf8

        logging.info("Created DataUtil instance.")

    # Outbound conversions
    def actuatorDataToJson(
        self, data: ActuatorData = None, useDecForFloat: bool = False
    ):
        if not data:
            logging.debug("ActuatorData is null. Returning empty string.")
            return ""

        jsonData = self._generateJsonData(obj=data, useDecForFloat=False)
        return jsonData

    def sensorDataToJson(self, data: SensorData = None, useDecForFloat: bool = False):
        if not data:
            logging.debug("SensorData is null. Returning empty string.")
            return ""

        jsonData = self._generateJsonData(obj=data, useDecForFloat=False)
        return jsonData

    def systemPerformanceDataToJson(
        self, data: SystemPerformanceData = None, useDecForFloat: bool = False
    ):
        if not data:
            logging.debug("SystemPerformanceData is null. Returning empty string.")
            return ""

        jsonData = self._generateJsonData(obj=data, useDecForFloat=False)
        return jsonData

    # Inbound conversions
    def jsonToActuatorData(self, jsonData: str = None, useDecForFloat: bool = False):
        if not jsonData:
            logging.warning("JSON data is empty or null. Returning null.")
            return None

        # Clean up JSON string and load into dict
        jsonStruct = self._formatDataAndLoadDictionary(jsonData, useDecForFloat)

        # Create ActuatorData object and update with JSON data
        actuatorData = ActuatorData()
        self._updateIotData(jsonStruct, actuatorData)
        return actuatorData

    def jsonToSensorData(self, jsonData: str = None, useDecForFloat: bool = False):
        if not jsonData:
            logging.warning("JSON data is empty or null. Returning null.")
            return None

        jsonStruct = self._formatDataAndLoadDictionary(jsonData, useDecForFloat)

        sensorData = SensorData()
        self._updateIotData(jsonStruct, sensorData)
        return sensorData

    def jsonToSystemPerformanceData(
        self, jsonData: str = None, useDecForFloat: bool = False
    ):
        if not jsonData:
            logging.warning("JSON data is empty or null. Returning null.")
            return None

        jsonStruct = self._formatDataAndLoadDictionary(jsonData, useDecForFloat)

        sysPerfData = SystemPerformanceData()
        self._updateIotData(jsonStruct, sysPerfData)
        return sysPerfData

    # Helper methods
    def _generateJsonData(self, obj, useDecForFloat: bool = False):
        jsonData = None

        if self.encodeToUtf8:
            jsonData = json.dumps(obj, cls=JsonDataEncoder).encode("utf-8")
        else:
            jsonData = json.dumps(obj, cls=JsonDataEncoder)

        if jsonData:
            jsonData = (
                jsonData.replace("'", '"')
                .replace("False", "false")
                .replace("True", "true")
            )

        return jsonData

    def _updateIotData(self, jsonStruct, obj):
        varStruct = vars(obj)
        logging.debug("Object vars: " + str(varStruct))

        for key in jsonStruct:
            if key in varStruct:
                setattr(
                    obj, key, jsonStruct[key]
                )  # (target object, attribute name, value)
            else:
                logging.warning(
                    "JSON data contains key not mappable to object: %s", key
                )

    def _formatDataAndLoadDictionary(
        self, jsonData: str, useDecForFloat: bool = False
    ) -> dict:

        jsonData = (
            jsonData.replace("'", '"').replace("False", "false").replace("True", "true")
        )

        jsonStruct = None

        if useDecForFloat:
            jsonStruct = json.loads(jsonData, parse_float=Decimal)
        else:
            jsonStruct = json.loads(jsonData)

        return jsonStruct


class JsonDataEncoder(JSONEncoder):
    """
    Convenience class to facilitate JSON encoding of an object that
    can be converted to a dict.

    """

    def default(self, o):
        return o.__dict__
