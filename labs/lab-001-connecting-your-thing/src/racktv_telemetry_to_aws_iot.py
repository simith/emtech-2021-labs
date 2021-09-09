# Copyright 2010-2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#  http://aws.amazon.com/apache2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

from __future__ import absolute_import
import argparse
from awscrt import auth, http, io, mqtt
from awsiot import iotjobs
from awsiot import mqtt_connection_builder
from concurrent.futures import Future
import sys
import threading
import time
import traceback
import logging
import uuid
import time, threading,datetime
import argparse
import json
import colorama
from colorama import Fore, Back, Style
import queue
from threading import Thread
import pyfiglet
import sys,signal
import os

class RackTv:


    def __init__(self):

        self.rootCAPath = "../../../config/AmazonRootCA1.pem"
        self.privateKeyPath = "../scripts/privatekey.pem"
        self.certificatePath = "../scripts/cert.pem"

        self.mqtt_port = 8883
        self.mqtt_connection = None
        self.jobs_client = None
        self.event_queue = queue.Queue()
        self.serial_number = "ADFD4D576C"

        self.mac_address = "ADFD4D576C"
        self.product = "racktv"
        self.state = "ON"
        self.endpoint_address = "alzg8fuyb9yn5-ats.iot.ap-southeast-1.amazonaws.com"
        self.timer = 30
        self.exit_simulator = False
        self.uc_subscription_done = False
        self.all_done = threading.Event()
        
    def get_product_name(self):
        return self.product

    def get_serial_number(self):
        return self.serial_number
    
    def get_iot_endpoint(self):
        return self.endpoint_address
        
    def get_tv_state(self):
        return self.state


    def printColor(self,color,msg):
        now = datetime.datetime.now()
        print( color + now.strftime("%Y-%m-%d %H:%M") + ": "  + msg )
    
    def banner(self,banner="Device Simulator"):
        ascii_banner = pyfiglet.figlet_format(banner)
        print(ascii_banner)

    def start(self):

        io.init_logging(getattr(io.LogLevel, "Info"), 'stderr')
        #self.connect(self.get_serial_number(),self.get_iot_endpoint())

  
    def connect(self,client_id,host):
         # Spin up resources
        print(f'Entering connect with {self.certificatePath}, {self.privateKeyPath} ')
        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

        self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=host,
            cert_filepath=self.certificatePath,
            pri_key_filepath=self.privateKeyPath,
            client_bootstrap=client_bootstrap,
            ca_filepath= self.rootCAPath,
            client_id=client_id,
            clean_session=False,
            keep_alive_secs=6)

        print("Connecting to {} with client ID '{}'...".format(
        self.endpoint_address, self.serial_number))

        connected_future = self.mqtt_connection.connect()

        self.jobs_client = iotjobs.IotJobsClient(self.mqtt_connection)

        # Wait for connection to be fully established.
        # Note that it's not necessary to wait, commands issued to the
        # mqtt_connection before its fully connected will simply be queued.
        # But this sample waits here so it's obvious when a connection
        # fails or succeeds.
        connected_future.result()
        print("Connected!")  
        
    def publish_mqtt_message(self,topic,msg):
        message_json = json.dumps(msg, indent=4)
        print("======================[{}]====================================".format(msg['msg_id']))
        print("Publishing message to topic '{}'".format(topic))
        print("Message:\n {}".format(message_json))
        self.mqtt_connection.publish(
            topic=topic,
            payload=message_json,
            qos=mqtt.QoS.AT_MOST_ONCE)
        print("==============================================================\n")
        
    
if __name__== "__main__":

    bannerText = "RackTv"
    tv = RackTv()
    tv.banner(bannerText)
    tv.start()
    iot_endpoint = "alzg8fuyb9yn5-ats.iot.ap-southeast-1.amazonaws.com"
    iot_region = "ap-southeast-1"
    
   
    print(f"IOT_ENDPOINT fetched from environment variable: {iot_endpoint}")
    print(f"IOT_REGION fetched from environment variable: {iot_region}")
    
    try:
        
        tv.connect(tv.get_serial_number(),tv.get_iot_endpoint())
        topic = 'app/racktv/'+ tv.get_serial_number() + '/telemetry'
        msg_id = 1
        while msg_id < 30:
            msg = {'msg_id': msg_id, \
                   'serial_no': tv.get_serial_number(), \
                   "ts": time.time(), \
                   "product": tv.get_product_name(), \
                   "data": {
                       "state": tv.get_tv_state(), \
                       "uptime": time.time() - 166149
                       
                   }}
            tv.publish_mqtt_message(topic,msg)
            msg_id = msg_id + 1
            time.sleep(3)
    except :
        print("Exception hit")
        
        
  

