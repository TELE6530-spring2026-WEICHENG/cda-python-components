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
import paho.mqtt.client as mqttClient

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.IDataMessageListener import IDataMessageListener
from programmingtheiot.common.ResourceNameEnum import ResourceNameEnum

from programmingtheiot.cda.connection.IPubSubClient import IPubSubClient


class MqttClientConnector(IPubSubClient):
    """
    Shell representation of class for student implementation.

    """

    def __init__(self, clientID: str = None, cleanSession: bool = None):
        """
        Default constructor. This will set remote broker information and client connection
        information based on the default configuration file contents.

        @param clientID Defaults to None. Can be set by caller. If this is used, it's
        critically important that a unique, non-conflicting name be used so to avoid
        causing the MQTT broker to disconnect any client using the same name. With
        auto-reconnect enabled, this can cause a race condition where each client with
        the same clientID continuously attempts to re-connect, causing the broker to
        disconnect the previous instance
        """
        self.config = ConfigUtil()

        self.dataMsgListener = None
        self.mqttClient = None

        self.host = self.config.getProperty(
            ConfigConst.MQTT_GATEWAY_SERVICE,
            ConfigConst.HOST_KEY,
            ConfigConst.DEFAULT_HOST,
        )

        self.port = self.config.getInteger(
            ConfigConst.MQTT_GATEWAY_SERVICE,
            ConfigConst.PORT_KEY,
            ConfigConst.DEFAULT_MQTT_PORT,
        )

        self.keepAlive = self.config.getInteger(
            ConfigConst.MQTT_GATEWAY_SERVICE,
            ConfigConst.KEEP_ALIVE_KEY,
            ConfigConst.DEFAULT_KEEP_ALIVE,
        )

        self.defaultQos = self.config.getInteger(
            ConfigConst.MQTT_GATEWAY_SERVICE,
            ConfigConst.DEFAULT_QOS_KEY,
            ConfigConst.DEFAULT_QOS,
        )

        defaultCleanSession = self.config.getBoolean(
            ConfigConst.MQTT_GATEWAY_SERVICE,
            ConfigConst.CLEAN_SESSION_KEY,
            ConfigConst.DEFAULT_CLEAN_SESSION,
        )
        self.cleanSession = (
            cleanSession if cleanSession is not None else defaultCleanSession
        )

        self.clientID = self.config.getProperty(
            ConfigConst.CONSTRAINED_DEVICE, ConfigConst.DEVICE_LOCATION_ID_KEY, clientID
        )

        if not clientID:
            self.clientID = "CDAMqttClientID001"
        logging.info(f"MqttClientConnector initialized with clientID: {self.clientID}")
        logging.info(
            f"MqttClientConnector initialized with host: {self.host}, port: {self.port}, keepAlive: {self.keepAlive}, defaultQos: {self.defaultQos}"
        )

    def connectClient(self) -> bool:

        # Initiate the MQTT client and set the callback functions.
        if not self.mqttClient:
            self.mqttClient = mqttClient.Client(
                client_id=self.clientID, clean_session=self.cleanSession
            )
            # Manually set fallback functions for MQTT client callbacks.
            self.mqttClient.on_connect = self.onConnect
            self.mqttClient.on_disconnect = self.onDisconnect
            self.mqttClient.on_message = self.onMessage
            self.mqttClient.on_publish = self.onPublish
            self.mqttClient.on_subscribe = self.onSubscribe

        if not self.mqttClient.is_connected():
            logging.info("MQTT client connecting to broker at host: " + self.host)

            # TCP connection -> 4 time handshake
            self.mqttClient.connect(self.host, self.port, self.keepAlive)
            # Start the network loop in a separate thread to handle incoming and outgoing MQTT messages.
            self.mqttClient.loop_start()

            return True
        else:
            logging.warning(
                "MQTT client is already connected. Ignoring connect request."
            )

            return False

    def disconnectClient(self) -> bool:
        if self.mqttClient.is_connected():
            logging.info("Disconnecting MQTT client from broker: " + self.host)

            # Stop the network loop first before disconnecting to ensure a clean shutdown of the MQTT client.
            self.mqttClient.loop_stop()
            self.mqttClient.disconnect()

            return True
        else:
            logging.warning("MQTT client already disconnected. Ignoring.")

            return False

    # Callback functions
    def onConnect(self, client, userdata, flags, rc):
        logging.info("MQTT client connected to broker: " + str(client))

    def onDisconnect(self, client, userdata, rc):
        logging.info("MQTT client disconnected from broker: " + str(client))

    def onMessage(self, client, userdata, msg):
        payload = msg.payload

        if payload:
            logging.info(
                "MQTT message received with payload: " + str(payload.decode("utf-8"))
            )
        else:
            logging.info("MQTT message received with no payload: " + str(msg))

    def onPublish(self, client, userdata, mid):
        logging.info("MQTT message published: " + str(client))

    def onSubscribe(self, client, userdata, mid, granted_qos):
        logging.info("MQTT client subscribed: " + str(client))

    def onActuatorCommandMessage(self, client, userdata, msg):
        """
        This callback is defined as a convenience, but does not
        need to be used and can be ignored.

        It's simply an example for how you can create your own
        custom callback for incoming messages from a specific
        topic subscription (such as for actuator commands).

        @param client The client reference context.
        @param userdata The user reference context.
        @param msg The message context, including the embedded payload.
        """
        pass

    def publishMessage(
        self,
        resource: ResourceNameEnum = None,
        msg: str = None,
        qos: int = ConfigConst.DEFAULT_QOS,
    ):
        # check validity of resource (topic)
        if not resource:
            logging.warning("No topic specified. Cannot publish message.")
            return False

        # check validity of message
        if not msg:
            logging.warning(
                "No message specified. Cannot publish message to topic: "
                + resource.value
            )
            return False

        # check validity of QoS - set to default if necessary
        if qos < 0 or qos > 2:
            qos = ConfigConst.DEFAULT_QOS

        # publish message, and wait for publish to complete before returning

        # publish() is asynchronous,sending the publish request to background thread that handles network communication.
        msgInfo = self.mqttClient.publish(topic=resource.value, payload=msg, qos=qos)

        # Making sure the publish request is completed before returning from this method.
        try:
            # Handling potential timeout error
            msgInfo.wait_for_publish()
        except Exception as e:
            logging.warning(f"Publish did not complete: {e}")
            return False

        return True

    def subscribeToTopic(
        self,
        resource: ResourceNameEnum = None,
        callback=None,
        qos: int = ConfigConst.DEFAULT_QOS,
    ):

        if not resource:
            logging.warning("No topic specified. Cannot subscribe.")
            return False

        if qos < 0 or qos > 2:
            qos = ConfigConst.DEFAULT_QOS

        # subscribe to topic
        logging.info("Subscribing to topic %s", resource.value)
        self.mqttClient.subscribe(resource.value, qos)

        return True

    def unsubscribeFromTopic(self, resource: ResourceNameEnum = None):
        # check validity of resource (topic)
        if not resource:
            logging.warning("No topic specified. Cannot unsubscribe.")
            return False

        logging.info("Unsubscribing to topic %s", resource.value)
        self.mqttClient.unsubscribe(resource.value)

        return True

    def setDataMessageListener(self, listener: IDataMessageListener = None) -> bool:
        if listener:
            self.dataMsgListener = listener
            return True
        return False
