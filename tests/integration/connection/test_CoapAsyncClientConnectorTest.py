#####
#
# This class is part of the Programming the Internet of Things
# project, and is available via the MIT License, which can be
# found in the LICENSE file at the top level of this repository.
#
# Copyright (c) 2020 - 2025 by Andrew D. King
#

import logging
import unittest

from time import sleep

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.DefaultDataMessageListener import (
    DefaultDataMessageListener,
)
from programmingtheiot.common.ResourceNameEnum import ResourceNameEnum

from programmingtheiot.cda.connection.AsyncCoapClientConnector import (
    AsyncCoapClientConnector,
)

from programmingtheiot.data.DataUtil import DataUtil
from programmingtheiot.data.SensorData import SensorData
from programmingtheiot.data.ActuatorData import ActuatorData
from programmingtheiot.data.SystemPerformanceData import SystemPerformanceData


class CoapAsyncClientConnectorTest(unittest.TestCase):
    """
    Integration tests for AsyncCoapClientConnector using a separately
    running CoAP server (e.g., the GDA's CoAP server).
    """

    @classmethod
    def setUpClass(self):
        logging.basicConfig(
            format="%(asctime)s:%(module)s:%(levelname)s:%(message)s",
            level=logging.INFO,
        )
        logging.info("Testing AsyncCoapClientConnector class...")

        self.dataMsgListener = DefaultDataMessageListener()

        self.pollRate = ConfigUtil().getInteger(
            ConfigConst.CONSTRAINED_DEVICE,
            ConfigConst.POLL_CYCLES_KEY,
            ConfigConst.DEFAULT_POLL_CYCLES,
        )

        self.coapClient = AsyncCoapClientConnector()

    @classmethod
    def tearDownClass(self):
        self.coapClient.disconnectClient()

    def setUp(self):
        self.sensorData = SensorData(
            typeID=ConfigConst.HUMIDITY_SENSOR_TYPE,
            name="FakeHumiditySensor",
        )
        self.sensorData.setValue(60.0)

        self.actuatorData = ActuatorData(
            typeID=ConfigConst.HVAC_ACTUATOR_TYPE,
            name="FakeHvacActuator",
        )
        self.actuatorData.setCommand(ConfigConst.COMMAND_ON)
        self.actuatorData.setValue(21.0)
        self.actuatorData.setStateData("HVAC is ON")

        self.sysPerfData = SystemPerformanceData(
            typeID=ConfigConst.SYSTEM_PERF_TYPE,
            name="FakeSystemPerformance",
        )
        self.sysPerfData.setCpuUtilization(45.2)
        self.sysPerfData.setDiskUtilization(62.8)
        self.sysPerfData.setMemoryUtilization(33.5)

    def tearDown(self):
        pass

    # @unittest.skip("Ignore for now.")
    def testConnectAndDiscover(self):
        self.coapClient.sendDiscoveryRequest(timeout=5)
        sleep(5)

    # @unittest.skip("Ignore for now.")
    def testGetActuatorCommandCon(self):
        self.coapClient.sendGetRequest(
            resource=ResourceNameEnum.CDA_ACTUATOR_CMD_RESOURCE,
            enableCON=True,
            timeout=5,
        )

    # @unittest.skip("Ignore for now.")
    def testGetActuatorCommandNon(self):
        self.coapClient.sendGetRequest(
            resource=ResourceNameEnum.CDA_ACTUATOR_CMD_RESOURCE,
            enableCON=False,
            timeout=5,
        )

    @unittest.skip("Ignore for now.")
    def testDeleteSensorMessageCon(self):
        self.coapClient.sendDeleteRequest(
            resource=ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE,
            enableCON=True,
            timeout=5,
        )

    @unittest.skip("Ignore for now.")
    def testDeleteSensorMessageNon(self):
        self.coapClient.sendDeleteRequest(
            resource=ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE,
            enableCON=False,
            timeout=5,
        )

    # @unittest.skip("Ignore for now.")
    def testPostSensorMessageCon(self):
        data = SensorData()
        jsonData = DataUtil().sensorDataToJson(data=data)

        self.coapClient.sendPostRequest(
            resource=ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE,
            enableCON=True,
            payload=jsonData,
            timeout=5,
        )

    # @unittest.skip("Ignore for now.")
    def testPostSensorMessageNon(self):

        jsonData = DataUtil().sensorDataToJson(data=self.sensorData)

        self.coapClient.sendPostRequest(
            resource=ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE,
            enableCON=False,
            payload=jsonData,
            timeout=5,
        )

    # @unittest.skip("Ignore for now.")
    def testPutSensorMessageCon(self):

        jsonData = DataUtil().sensorDataToJson(data=self.sensorData)

        self.coapClient.sendPutRequest(
            resource=ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE,
            enableCON=True,
            payload=jsonData,
            timeout=5,
        )

    # @unittest.skip("Ignore for now.")
    def testPutSensorMessageNon(self):

        jsonData = DataUtil().sensorDataToJson(data=self.sensorData)

        self.coapClient.sendPutRequest(
            resource=ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE,
            enableCON=False,
            payload=jsonData,
            timeout=5,
        )

    # @unittest.skip("Ignore for now.")
    def testPutSystemPerformanceDataCon(self):
        jsonData = DataUtil().systemPerformanceDataToJson(data=self.sysPerfData)

        self.coapClient.sendPutRequest(
            resource=ResourceNameEnum.CDA_SYSTEM_PERF_MSG_RESOURCE,
            enableCON=True,
            payload=jsonData,
            timeout=5,
        )

    # @unittest.skip("Ignore for now.")
    def testActuatorCommandObserve(self):

        # Step 1: Send a SensorData that exceeds threshold → GDA will create ActuatorData
        #         → triggers this.changed() → observer gets notified
        sensorAboveThreshold = SensorData(
            typeID=ConfigConst.HUMIDITY_SENSOR_TYPE,
            name="FakeHumiditySensor",
        )
        sensorAboveThreshold.setValue(65.0)  # Above threshold to trigger actuator
        jsonData = DataUtil().sensorDataToJson(data=sensorAboveThreshold)

        self.coapClient.sendPutRequest(
            resource=ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE,
            enableCON=True,
            payload=jsonData,
            timeout=5,
        )

        # Step 2: Start observer to listen for ActuatorData changes (e.g., command updates)
        self._startObserver()
        sleep(5)  # Give observer time to register

        sleep(10)  # Wait for GDA to process and push notification

        # Step 3: Send another SensorData to trigger a second notification
        sensorAboveThreshold.setValue(40.0)
        jsonData2 = DataUtil().sensorDataToJson(data=sensorAboveThreshold)

        self.coapClient.sendPutRequest(
            resource=ResourceNameEnum.CDA_SENSOR_MSG_RESOURCE,
            enableCON=True,
            payload=jsonData2,
            timeout=5,
        )

        sleep(15)  # Wait for second notification

        self._stopObserver()

    def _startObserver(self):
        self.coapClient.startObserver(
            resource=ResourceNameEnum.CDA_ACTUATOR_CMD_RESOURCE
        )

    def _stopObserver(self):
        self.coapClient.stopObserver(
            resource=ResourceNameEnum.CDA_ACTUATOR_CMD_RESOURCE
        )


if __name__ == "__main__":
    unittest.main()
