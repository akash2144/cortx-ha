#!/usr/bin/env python3

# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

import json
from typing import Callable
from threading import Thread, Event
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.log import Log
from cortx.utils.message_bus import MessageBusAdmin
from cortx.utils.message_bus import MessageProducer
from cortx.utils.message_bus import MessageConsumer
from cortx.utils.message_bus import MessageBus as utils_message_bus
from ha import const

class MessageBusProducer:
    PRODUCER_METHOD = "sync"

    def __init__(self, producer_id: str, message_type: str, partitions: int):
        """
        Register message types with message bus.
        Args:
            producer_id (str): producer id.
            message_types (str): Message type.
            partitions (int, optional): No. of partitions. Defaults to 1.
        Raises:
            MessageBusError: Message bus error.
        """
        self.producer = MessageProducer(producer_id=producer_id, message_type=message_type, method=MessageBusProducer.PRODUCER_METHOD)

    def publish(self, message: any):
        """
        Produce message to message bus.
        Args:
            message (any): Message.
            If msg is dict it will be dumped as json.
            If msg is string then it will be send directly.
            If message is list, it should have all string element, all items will be published.
        """
        if isinstance(message, dict):
            self.producer.send([json.dumps(message)])
        elif isinstance(message, str):
            self.producer.send([message])
        elif isinstance(message, list):
            self.producer.send(message)
        else:
            raise Exception(f"Invalid type of message {message}")

class CONSUMER_STATUS:
    SUCCESS = "success"
    FAILED = "failed"
    FAILED_STOP = "failed_stop"
    SUCCESS_STOP = "success_stop"

class MessageBusConsumer:

    def __init__(self, consumer_id: int, consumer_group: str, message_type: str,
                callback: Callable, auto_ack: bool, offset: str, timeout: int):
        """
        Initalize consumer.
        Args:
            consumer_id (int): Consumer ID.
            consumer_group (str): Consumer Group.
            message_type (list): Message Type.
            callback (Callable): function to get message.
            auto_ack (bool, optional): Check auto ack. Defaults to False.
            offset (str, optional): Offset for messages. Defaults to "earliest".
        """
        self.callback = callback
        self._stop = Event()
        self.flush_on_exit = False
        self.consumer_id = consumer_id
        self.consumer_group = consumer_group
        self.message_type = message_type
        self.name = message_type+"-consumer-thread"
        self.auto_ack = auto_ack
        self.offset = offset
        self.timeout = timeout
        self.consumer_thread = None

    def run(self):
        """
        Overloaded of Thread.
        Note: Please properly handle failure cases to avoid stuck in loop

        1. Caller received and processed message		                            SUCCESS
        2. Caller received but not able to process need retry			            FAILED
        3. Caller received but message is irrelevant to caller					    SUCCESS
        4. Caller received	message but failed to process and not want to retry		FAILED_STOP
        5. Caller received message and want to sop listen to message				SUCCESS_STOP
        6. If nothing is passed it will be case 2						            FAILED
        7. Exception will be swallowed and ack.
        8. Closing main thread will close this thread as it is running as deamon.

        As self.consumer.receive(timeout) is block call t1.join() will not stop thread.
        Stop thread by completing work as per above cases.
        """
        retry = False
        while not self._stop.is_set():
            try:
                if not retry:
                    # setting some default timeout as 0 will block the call for indefinite time
                    message = self.consumer.receive(timeout=const.CORTX_HA_WAIT_TIMEOUT)
                    # if no message is received and the timeout occurs then message will be set None
                    # so lets continue wait again on message bus.
                    if message is None:
                        continue
                try:
                    status = self.callback(message)
                except Exception as e:
                    Log.error(f"Caught exception from caller: {e}. retry again ...")
                    retry = True
                    continue
                if status == CONSUMER_STATUS.SUCCESS:
                    self.consumer.ack()
                elif status == CONSUMER_STATUS.FAILED_STOP:
                    # TODO: check if can be handled internally, currently message will get ack by message bus api
                    break
                elif status == CONSUMER_STATUS.SUCCESS_STOP:
                    self.consumer.ack()
                    break
                else:
                    retry = True
                    continue
                retry = False
            except Exception as e:
                Log.error(f"Supressing exception from message bus {e}")
                retry = False
        if self.flush_on_exit:
            # we do not expect any messages to be present in the message bus at this point
            # since previously received cluster stop would have ensured that message bus is empty
            # here we are makeing sure that messages in message bus are flushed,
            # so when next time consumer starts it will not read stale messages.
            Log.info(f"flush pending messages of type {self.message_type}.")
            while True:
                # needs to set minimum feasible timeout but,
                # setting 0 will block the call for indefinite time,
                # hence setting to 1.
                message = self.consumer.receive(timeout=1)
                if message is None:
                    break
                else:
                    Log.info(f"flushing message: {message}.")
                    self.consumer.ack()

    def start(self):
        """
        Start the consumer
        """
        Log.info(f"Starting the daemon for {self.name}...")
        self.consumer = MessageConsumer(consumer_id=str(self.consumer_id),
                        consumer_group=self.consumer_group,
                        message_types=[self.message_type],
                        auto_ack=self.auto_ack, offset=self.offset)
        self.consumer_thread = Thread(target=self.run, name=self.name)
        self.consumer_thread.setDaemon(True)
        self.consumer_thread.start()
        Log.info(f"The daemon {self.name} started successfully.")

    def stop(self, flush=False):
        """
        Set the stop event so consumer thread will stop
        """
        Log.info(f"Stopping the daemon {self.name}...")
        self.flush_on_exit = flush
        self._stop.set()

    def join(self):
        """
        Blocking call, it calls join function of message bus consumer thread
        """
        if self.consumer_thread is not None:
            Log.info(f"waiting for {self.name} to exit...")
            # wait to stop consumer thread
            self.consumer_thread.join()
            Log.info(f"The daemon {self.name} is stopped successfully.")

class MessageBus:
    ADMIN_ID = "ha_admin"

    @staticmethod
    def init():
        """
        Initialize utils MessageBus Library with kafka endpoints once per service. In future utils will throw error if
        init done multiple times. If any new service will come which uses MessageBus then init should be done there.
        """
        message_server_endpoints = Conf.get(const.HA_GLOBAL_INDEX, f"kafka_config{const._DELIM}endpoints")
        utils_message_bus.init(message_server_endpoints)

    @staticmethod
    def get_consumer(consumer_id: int, consumer_group: str, message_type: str,
                callback: Callable, auto_ack: bool = False, offset: str = "earliest", timeout: int = 0) -> MessageBusConsumer:
        """
        Get consumer.
        Args:
            consumer_id (int): Consumer ID.
            consumer_group (str): Consumer Group.
            message_type (str): Message Type.
            callback (Callable): callback function to process message.
            auto_ack (bool, optional): Check auto ack. Defaults to False.
            offset (str, optional): Offset for messages. Defaults to "earliest".
            timeout (int, optional): Max wait time for thread to wait for a message. Default: timeout is 0 and so call is blocking
        """
        return MessageBusConsumer(consumer_id, consumer_group, message_type, callback, auto_ack, offset, timeout)

    @staticmethod
    def get_producer(producer_id: str, message_type: str, partitions: int = 1) -> MessageBusProducer:
        """
        Register message types with message bus. and get Producer.
        Args:
            producer_id (str): producer id.
            message_types (str): Message type.
            partitions (int, optional): No. of partitions. Defaults to 1.
        Raises:
            MessageBusError: Message bus error.
        """
        MessageBus.register(message_type, partitions)
        return MessageBusProducer(producer_id, message_type, partitions)

    @staticmethod
    def register(message_type: str, partitions: int = 1):
        """
        Register message type to message bus.
        Args:
            message_type (str): Message type.
            partitions (int): Number of partition.
        """
        admin = MessageBusAdmin(admin_id=MessageBus.ADMIN_ID)
        try:
            if message_type not in admin.list_message_types():
                admin.register_message_type(message_types=[message_type], partitions=partitions)
        except Exception as e:
            if "TOPIC_ALREADY_EXISTS" not in str(e):
                raise(e)

    @staticmethod
    def deregister(message_type: str):
        """
        Deregister message type to message bus.
        Args:
            message_type (str): Message type.
        """
        admin = MessageBusAdmin(admin_id=MessageBus.ADMIN_ID)
        if message_type in admin.list_message_types():
            admin.deregister_message_type(message_types=[message_type])
