import logging
import socket
import threading
import asyncio
import traceback
from urllib import response

import aiocoap
from aiocoap import Code, Message, Context
from aiocoap.numbers.types import CON, NON

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.ResourceNameEnum import ResourceNameEnum
from programmingtheiot.common.IDataMessageListener import IDataMessageListener
from programmingtheiot.cda.connection.IRequestResponseClient import (
    IRequestResponseClient,
)
from programmingtheiot.data.DataUtil import DataUtil


class AsyncCoapClientConnector(IRequestResponseClient):
    """
    Shell representation of class for student implementation.

    """

    def __init__(self, dataMsgListener: IDataMessageListener = None):

        self.config = ConfigUtil()
        self.dataMsgListener = dataMsgListener
        self.enableConfirmedMsgs = False

        # CoAP client context - used for sending requests and receiving responses.
        self.clientContext = None

        # Event loop
        self._eventLoop = None
        self._eventLoopThread = None

        self.observeRequests = {}
        self.observeTasks = {}

        self.host = self.config.getProperty(
            ConfigConst.COAP_GATEWAY_SERVICE,
            ConfigConst.HOST_KEY,
            ConfigConst.DEFAULT_HOST,
        )
        self.port = self.config.getInteger(
            ConfigConst.COAP_GATEWAY_SERVICE,
            ConfigConst.PORT_KEY,
            ConfigConst.DEFAULT_COAP_PORT,
        )

        self.includeDebugLogDetail = True

        try:
            tmpHost = socket.gethostbyname(self.host)

            if tmpHost:
                self.host = tmpHost
                self.uriPath = f"coap://{self.host}:{self.port}/"
                logging.info(f"CoAP client will connect to: {self.uriPath}")
                self._initEventLoop()
                logging.info("AsyncCoapClientConnector created. URI: %s", self.uriPath)

            else:
                logging.error(f"Can't resolve host: {self.host}")
                raise

        except socket.gaierror:
            logging.error(
                f"Failed to resolve host: {self.host}. Check hostname in config."
            )
            raise

    def _initEventLoop(self):
        if self._eventLoop is not None and self._eventLoop.is_running():
            return
        # Initialize a new event loop and run it in a background thread
        self._eventLoop = asyncio.new_event_loop()
        self._eventLoopThread = threading.Thread(
            target=self._eventLoop.run_forever, daemon=True, name="CoAP-AsyncEventLoop"
        )
        self._eventLoopThread.start()
        logging.info("Async event loop started in background thread.")

        # Connect the CoAP client context in the event loop thread
        self.connectClient()

    def sendDiscoveryRequest(
        self, timeout: int = IRequestResponseClient.DEFAULT_TIMEOUT
    ) -> bool:
        logging.info("Issuing Async DISCOVERY to: /.well-known/core")
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._handleDiscoveryRequest(), self._eventLoop
            )
            return future.result(timeout=timeout)
        except Exception as e:
            logging.warning("Discovery failed: %s", e)
            traceback.print_exc()
            return False

    def setDataMessageListener(self, listener: IDataMessageListener = None) -> bool:
        if listener:
            self.dataMsgListener = listener
            return True

        return False

    def sendDeleteRequest(
        self,
        resource: ResourceNameEnum = None,
        name: str = None,
        enableCON: bool = False,
        timeout: int = IRequestResponseClient.DEFAULT_TIMEOUT,
    ) -> bool:
        resourcePath = self._createResourcePath(resource, name)
        logging.info("Issuing Async DELETE to: %s", resourcePath)
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._handleDeleteRequest(resourcePath, enableCON), self._eventLoop
            )
            return future.result(timeout=timeout)
        except Exception as e:
            logging.warning("DELETE failed: %s", e)
            traceback.print_exc()
            return False

    def sendGetRequest(
        self,
        resource: ResourceNameEnum = None,
        name: str = None,
        enableCON: bool = False,
        timeout: int = IRequestResponseClient.DEFAULT_TIMEOUT,
    ) -> bool:
        resourcePath = self._createResourcePath(resource, name)
        logging.info("Issuing Async GET to: %s", resourcePath)
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._handleGetRequest(resourcePath, enableCON), self._eventLoop
            )
            return future.result(timeout=timeout)
        except Exception as e:
            logging.warning("GET failed: %s", e)
            traceback.print_exc()
            return False

    def sendPostRequest(
        self,
        resource: ResourceNameEnum = None,
        name: str = None,
        enableCON: bool = False,
        payload: str = None,
        timeout: int = IRequestResponseClient.DEFAULT_TIMEOUT,
    ) -> bool:
        resourcePath = self._createResourcePath(resource, name)
        logging.info("Issuing Async POST to: %s", resourcePath)
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._handlePostRequest(resourcePath, enableCON, payload),
                self._eventLoop,
            )
            return future.result(timeout=timeout)
        except Exception as e:
            logging.warning("POST failed: %s", e)
            traceback.print_exc()
            return False

    def sendPutRequest(
        self,
        resource: ResourceNameEnum = None,
        name: str = None,
        enableCON: bool = False,
        payload: str = None,
        timeout: int = IRequestResponseClient.DEFAULT_TIMEOUT,
    ) -> bool:
        resourcePath = self._createResourcePath(resource, name)
        logging.info("Issuing Async PUT to: %s", resourcePath)
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._handlePutRequest(resourcePath, enableCON, payload),
                self._eventLoop,
            )
            return future.result(timeout=timeout)
        except Exception as e:
            logging.warning("PUT failed: %s", e)
            traceback.print_exc()
            return False

    def startObserver(
        self,
        resource: ResourceNameEnum = None,
        name: str = None,
        ttl: int = IRequestResponseClient.DEFAULT_TTL,
    ) -> bool:
        """
        Start observing a resource.
        ttl: observation duration in seconds. Not currently used;
            can be implemented via call_later(ttl, task.cancel) for auto-expiry.
        """
        if resource:
            resourcePath = self._createResourcePath(resource, name)

            # Check if already observing this resource
            if resourcePath in self.observeTasks:
                logging.warning("Observer already active for: %s", resourcePath)
                return False

            logging.info("Starting observer for: %s", resourcePath)

            # Submit to event loop — do not call future.result()
            # because the observer is long-running and should not block
            task = asyncio.run_coroutine_threadsafe(
                self._handleStartObserveRequest(resourcePath), self._eventLoop
            )
            self.observeTasks[resourcePath] = task
            return True
        else:
            logging.warning("Can't start observer - no resource provided.")
            return False

    def connectClient(self):
        """
        Initialize the aiocoap client context by submitting the async
        coroutine to the background event loop and blocking until it
        completes. Called by _initEventLoop() during construction.
        """
        # Submit the async init coroutine to the event loop thread
        future = asyncio.run_coroutine_threadsafe(
            self._initClientContext(), self._eventLoop
        )
        # Block the calling thread until the client context is ready
        try:
            future.result(timeout=5)
            logging.info("CoAP async client connected.")
        except TimeoutError:
            logging.error("Failed to create CoAP client context within 5 seconds.")
            raise
        except Exception as e:
            logging.error("Failed to initialize CoAP client: %s", e)
            raise

    def disconnectClient(self):
        # 1. Cancel all active observers
        for path in list(self.observeTasks.keys()):
            self.stopObserver(resource=None, name=path)

        # 2. Shutdown aiocoap client context
        if self.clientContext:
            future = asyncio.run_coroutine_threadsafe(
                self.clientContext.shutdown(), self._eventLoop
            )
            try:
                future.result(timeout=5)
            except Exception as e:
                logging.warning("Shutdown error: %s", e)

        # 3. Stop the async event loop
        if self._eventLoop and self._eventLoop.is_running():
            self._eventLoop.call_soon_threadsafe(self._eventLoop.stop)

        # 4. Wait for the event loop thread to finish
        if self._eventLoopThread:
            self._eventLoopThread.join(timeout=5)

        logging.info("CoAP async client disconnected.")

    async def _initClientContext(self):
        self.clientContext = await Context.create_client_context()

    # Helper
    def _createResourcePath(self, resource: ResourceNameEnum = None, name: str = None):
        resourcePath = ""
        hasResource = False

        if resource:
            resourcePath = resourcePath + resource.value
            hasResource = True

        if name:
            if hasResource:
                resourcePath = resourcePath + "/"

            resourcePath = resourcePath + name

        return resourcePath

    # Async request methods

    # DiscoveryRequest:
    async def _handleDiscoveryRequest(self) -> bool:
        try:
            uriAndResourcePath = self.uriPath + ".well-known/core"
            msg = Message(mtype=CON, code=Code.GET, uri=uriAndResourcePath)
            responseData = await self.clientContext.request(
                request_message=msg
            ).response
            self._onDiscoveryResponse(responseData)
            return True
        except Exception as e:
            logging.warning("Async DISCOVERY failed: %s", e)
            traceback.print_exc()
            return False

    def _onDiscoveryResponse(self, response):
        if not response:
            logging.warning("Async DISCOVERY response invalid. Ignoring.")
            return
        logging.info("Async DISCOVERY response received.")
        payloadStr = response.payload.decode("utf-8")
        logging.info("Response data received. Payload: %s", payloadStr)

    # DeleteRequest:
    async def _handleDeleteRequest(self, resourcePath: str, enableCON: bool) -> bool:
        try:
            uri = self.uriPath + resourcePath
            mtype = CON if enableCON else NON
            msg = Message(mtype=mtype, code=Code.DELETE, uri=uri)
            response = await self.clientContext.request(msg).response
            self._onDeleteResponse(response, resourcePath)
            return True
        except Exception as e:
            logging.warning("Async DELETE failed: %s", e)
            traceback.print_exc()
            return False

    def _onDeleteResponse(self, response, resourcePath: str):
        if not response:
            logging.warning("Async DELETE response invalid. Ignoring.")
            return
        logging.info(
            "Async DELETE response received for %s. Code: %s",
            resourcePath,
            response.code,
        )
        if self.includeDebugLogDetail:
            logging.debug(
                "DELETE response payload: %s", response.payload.decode("utf-8")
            )

    # GetRequest:
    async def _handleGetRequest(self, resourcePath: str, enableCON: bool) -> bool:
        try:
            uri = self.uriPath + resourcePath

            mtype = CON if enableCON else NON

            msg = Message(mtype=mtype, code=Code.GET, uri=uri)
            response = await self.clientContext.request(msg).response
            self._onGetResponse(response, resourcePath)
            return True

        except Exception as e:
            logging.warning("Async GET failed: %s", e)
            traceback.print_exc()
            return False

    def _onGetResponse(self, response, resourcePath: str):
        """
        Handle the GET response which is an ActuatorCmdMessage payload.
        """
        if not response:
            logging.warning("Async GET response invalid. Ignoring.")
            return
        logging.info(
            "Async GET response received for %s. Code: %s", resourcePath, response.code
        )

        payloadJson = response.payload.decode("utf-8")

        if self.includeDebugLogDetail:
            logging.debug("GET response payload: %s", payloadJson)

        if ConfigConst.ACTUATOR_CMD in resourcePath:
            try:
                actuatorCmdMsg = DataUtil().jsonToActuatorCommandMessage(payloadJson)
                if self.dataMsgListener:
                    self.dataMsgListener.handleActuatorCommandMessage(actuatorCmdMsg)
            except Exception as e:
                logging.warning(
                    "Failed to decode actuator data. Ignoring: : {jsonData} %s", e
                )
                traceback.print_exc()

    # PostRequest:
    async def _handlePostRequest(
        self, resourcePath: str, enableCON: bool, payload: str
    ) -> bool:
        try:
            uri = self.uriPath + resourcePath
            mtype = CON if enableCON else NON
            payloadBytes = payload.encode("utf-8") if payload else b""
            msg = Message(mtype=mtype, code=Code.POST, uri=uri, payload=payloadBytes)
            response = await self.clientContext.request(msg).response
            self._onPostResponse(response, resourcePath)
            return True
        except Exception as e:
            logging.warning("Async POST failed: %s", e)
            traceback.print_exc()
            return False

    def _onPostResponse(self, response, resourcePath: str):
        if not response:
            logging.warning("Async POST response invalid. Ignoring.")
            return
        logging.info(
            "Async POST response received for %s. Code: %s", resourcePath, response.code
        )
        if self.includeDebugLogDetail:
            logging.debug("POST response payload: %s", response.payload.decode("utf-8"))

    # PutRequest:
    async def _handlePutRequest(
        self, resourcePath: str, enableCON: bool, payload: str
    ) -> bool:
        try:
            uri = self.uriPath + resourcePath
            mtype = CON if enableCON else NON
            payloadBytes = payload.encode("utf-8") if payload else b""
            msg = Message(mtype=mtype, code=Code.PUT, uri=uri, payload=payloadBytes)
            response = await self.clientContext.request(msg).response
            self._onPutResponse(response, resourcePath)
            return True
        except Exception as e:
            logging.warning("Async PUT failed: %s", e)
            traceback.print_exc()
            return False

    def _onPutResponse(self, response, resourcePath: str):
        if not response:
            logging.warning("Async PUT response invalid. Ignoring.")
            return
        logging.info(
            "Async PUT response received for %s. Code: %s", resourcePath, response.code
        )
        if self.includeDebugLogDetail:
            logging.debug("PUT response payload: %s", response.payload.decode("utf-8"))

    # ObserveRequest:
    async def _handleStartObserveRequest(self, resourcePath: str = None):
        """
        What is async for?
        - Regular for: for item in list -> synchronous iteration
        - async for: async for item in async_generator -> each iteration may await
        - Here, each iteration waits for the next notification from the server
        """
        uriAndResourcePath = self.uriPath + resourcePath
        msg = Message(code=Code.GET, uri=uriAndResourcePath, observe=0)
        #                                                    ^^^^^^^^
        #                                     observe=0 means "start observing"
        req = self.clientContext.request(msg)

        # Store request reference for cancellation in stopObserver
        self.observeRequests[resourcePath] = req

        try:
            # Wait for initial response
            response = await req.response
            logging.info(
                "Observer initial response for %s: %s",
                resourcePath,
                response.payload.decode("utf-8"),
            )

            # Continuously receive notifications — this loop runs until cancelled
            async for notification in req.observation:
                #                      ^^^^^^^^^^^^^^
                #  aiocoap's observation is an async iterator
                #  Each time the server pushes new data, it yields a notification

                payload_str = notification.payload.decode("utf-8")
                logging.info(
                    "Observer notification for %s: %s", resourcePath, payload_str
                )

                # Notify the DeviceDataManager
                if self.dataMsgListener:
                    self.dataMsgListener.handleIncomingMessage(
                        ResourceNameEnum.CDA_ACTUATOR_CMD_RESOURCE, payload_str
                    )

        except asyncio.CancelledError:
            # Triggered when stopObserver() calls task.cancel()
            logging.info("Observer cancelled for: %s", resourcePath)
        except Exception as e:
            logging.warning("Observer error for %s: %s", resourcePath, e)
            traceback.print_exc()
        finally:
            # Cleanup — runs whether the observer ended normally or was cancelled
            if resourcePath in self.observeRequests:
                del self.observeRequests[resourcePath]

    def stopObserver(
        self,
        resource: ResourceNameEnum = None,
        name: str = None,
        timeout: int = IRequestResponseClient.DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Stop observing a resource.
        Why explicitly stop?
        - CoAP server keeps sending notifications until told to stop
        - Not stopping = wasted network bandwidth + server resources
        """
        resourcePath = self._createResourcePath(resource, name) if resource else name

        if resourcePath and resourcePath in self.observeTasks:
            logging.info("Stopping observer for: %s", resourcePath)

            # Cancel the asyncio task → triggers CancelledError
            task = self.observeTasks[resourcePath]
            task.cancel()

            # Run cleanup coroutine
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._handleStopObserveRequest(resourcePath), self._eventLoop
                )
                future.result(timeout=5)
            except Exception as e:
                logging.warning("Stop observer cleanup error: %s", e)

            # Remove from tracking dict
            if resourcePath in self.observeTasks:
                del self.observeTasks[resourcePath]
            return True
        else:
            logging.warning("No active observer for: %s", resourcePath)
            return False

    async def _handleStopObserveRequest(
        self, resourcePath: str = None, ignoreErr: bool = False
    ):
        """Clean up the observation request."""
        if resourcePath in self.observeRequests:
            req = self.observeRequests[resourcePath]
            try:
                req.observation.cancel()
            except Exception as e:
                if not ignoreErr:
                    logging.warning("Cancel observation error: %s", e)
            if resourcePath in self.observeRequests:
                del self.observeRequests[resourcePath]
