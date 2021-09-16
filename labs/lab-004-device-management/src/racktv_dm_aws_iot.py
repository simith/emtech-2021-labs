# Copyright 2021 Rackspace Technology

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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


class LockedData:
    def __init__(self):
        self.lock = threading.Lock()
        self.disconnect_called = False
        self.is_working_on_job = False
        self.is_next_job_waiting = False


class RackTv:

    def __init__(self):

        self.rootCAPath = "../../../config/AmazonRootCA1.pem"
        self.privateKeyPath = "../../lab-001-connecting-your-thing/scripts/privatekey.pem"
        self.certificatePath = "../../lab-001-connecting-your-thing/scripts/cert.pem"

        self.mqtt_port = 8883
        self.mqtt_connection = None
        self.jobs_client = None
        self.event_queue = queue.Queue()
        self.serial_number = "42DC4BDD14"
        self.product = "racktv"
        self.state = "ON"
        self.endpoint_address = "a3ixr4lgf65v25-ats.iot.ap-southeast-1.amazonaws.com"
        self.timer = 30
        self.exit_simulator = False
        self.uc_subscription_done = False
        self.all_done = threading.Event()
        self.jobs_client = None
        self.locked_data = LockedData()
        
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
    
    def banner(self,banner="RackTV"):
        ascii_banner = pyfiglet.figlet_format(banner)
        print(ascii_banner)

    def start(self):

        io.init_logging(getattr(io.LogLevel, "Error"), 'stderr')
        #self.connect(self.get_serial_number(),self.get_iot_endpoint())

  
    def connect(self,client_id,host):
         # Spin up resources
        print('Entering connect with {}, {}'.format(self.certificatePath,self.privateKeyPath))
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

       

        # Wait for connection to be fully established.
        # Note that it's not necessary to wait, commands issued to the
        # mqtt_connection before its fully connected will simply be queued.
        # But this sample waits here so it's obvious when a connection
        # fails or succeeds.
        connected_future.result()
        print("Connected!")  
        self.jobs_client = iotjobs.IotJobsClient(self.mqtt_connection)
       

        
    def on_next_job_execution_changed(self,event):
        # type: (iotjobs.NextJobExecutionChangedEvent) -> None
        try:
            execution = event.execution
            if execution:
                print("Received Next Job Execution Changed event. job_id:{} job_document:{}".format(
                    execution.job_id, execution.job_document))
    
                # Start job now, or remember to start it when current job is done
                start_job_now = False
                with self.locked_data.lock:
                    if self.locked_data.is_working_on_job:
                        print("We are already working on a Job....")
                        self.locked_data.is_next_job_waiting = True
                    else:
                        start_job_now = True
    
                if start_job_now:
                    self.try_start_next_job()
    
            else:
                print("Received Next Job Execution Changed event: None. Waiting for further jobs...")
    
        except Exception as e:
            exit(e)
        
        
    def try_start_next_job(self):
        print("Trying to start the next job...{}".format( self.locked_data.is_working_on_job))
        with self.locked_data.lock:
            if self.locked_data.is_working_on_job:
                print("Nevermind, already working on a job.")
                return
    
            if self.locked_data.disconnect_called:
                print("Nevermind, sample is disconnecting.")
                return
    
            self.locked_data.is_working_on_job = True
            self.locked_data.is_next_job_waiting = False
    
        print("Publishing request to start next job...")
        request = iotjobs.StartNextPendingJobExecutionRequest(thing_name=self.serial_number)
        publish_future = self.jobs_client.publish_start_next_pending_job_execution(request, mqtt.QoS.AT_LEAST_ONCE)
        publish_future.add_done_callback(self.on_publish_start_next_pending_job_execution)
        
    def on_publish_start_next_pending_job_execution(self,future):
        # type: (Future) -> None
        try:
            future.result() # raises exception if publish failed
            print("Published request to start the next job.")
    
        except Exception as e:
            exit(e)
            
            
    def on_start_next_pending_job_execution_accepted(self,response):
    # type: (iotjobs.StartNextJobExecutionResponse) -> None
        print("Entering on_start_next_pending_job_execution_accepted with {}".format(response))
        try:
            if response.execution:
                execution = response.execution
                print("Request to start next job was accepted. job_id:{} job_document:{}".format(
                    execution.job_id, execution.job_document))
                # To emulate working on a job, spawn a thread that sleeps for a few seconds
                job_thread = threading.Thread(
                    target=lambda: self.job_thread_fn(execution.job_id, execution.job_document),
                    name='job_thread')
                job_thread.start()
            else:
                print("Request to start next job was accepted, but there are no jobs to be done. Waiting for further jobs...")
                

        except Exception as e:
            exit(e)       
            
    def on_start_next_pending_job_execution_rejected(self,rejected):
        # type: (iotjobs.RejectedError) -> None
        exit("Request to start next pending job rejected with code:'{}' message:'{}'".format(
            rejected.code, rejected.message))

    def job_thread_fn(self,job_id, job_document):
        try:
            print("Starting local work on job...")
            for i in range(6):
                 time.sleep(1)
                 print("Resetting RackTV in {}".format(5-i),end="\r")
                 
            os.system("clear")
            print("Starting up RackTv, please wait...")
            time.sleep(4)
            os.system("clear")
            self.banner()
                
               
            print("Done working on job. {}".format(job_document))
    
            print("Publishing request to update job status to SUCCEEDED...")
            request = iotjobs.UpdateJobExecutionRequest(
                thing_name=self.serial_number,
                job_id=job_id,
                status=iotjobs.JobStatus.SUCCEEDED)
            publish_future = self.jobs_client.publish_update_job_execution(request, mqtt.QoS.AT_LEAST_ONCE)
            publish_future.add_done_callback(self.on_publish_update_job_execution)

        except Exception as e:
            exit(e)
    
    
    def on_publish_update_job_execution(self,future):
        # type: (Future) -> None
        try:
            future.result() # raises exception if publish failed
            print("Published request to update job.")
    
        except Exception as e:
            exit(e)
            
    def on_update_job_execution_accepted(self,response):
    # type: (iotjobs.UpdateJobExecutionResponse) -> None
        try:
            print("Request to update job was accepted.")
            self.done_working_on_job()
        except Exception as e:
            exit(e)  
            
    def on_update_job_execution_rejected(self,rejected):
        # type: (iotjobs.RejectedError) -> None
        exit("Request to update job status was rejected. code:'{}' message:'{}'.".format(
            rejected.code, rejected.message))
    
   
    def done_working_on_job(self):
        print("Done working on job, let us check whether we have any mode jobs now...")
        with self.locked_data.lock:
            self.locked_data.is_working_on_job = False
            try_again = self.locked_data.is_next_job_waiting
    
        if try_again:
            self.try_start_next_job()
        
    
    def listen_for_jobs(self):
        try:
        # Subscribe to necessary topics.
        # Note that is **is** important to wait for "accepted/rejected" subscriptions
        # to succeed before publishing the corresponding "request".
            print("Subscribing to Next Changed events...")
            changed_subscription_request = iotjobs.NextJobExecutionChangedSubscriptionRequest(
                thing_name=self.serial_number)
            subscribed_future, _ = self.jobs_client.subscribe_to_next_job_execution_changed_events(
            request=changed_subscription_request,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_next_job_execution_changed)

            # Wait for subscription to succeed
            subscribed_future.result()
            print("Subscribing to Start responses...")
            start_subscription_request = iotjobs.StartNextPendingJobExecutionSubscriptionRequest(
                thing_name=self.serial_number)
            subscribed_accepted_future, _ = self.jobs_client.subscribe_to_start_next_pending_job_execution_accepted(
                request=start_subscription_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_start_next_pending_job_execution_accepted)
    
            subscribed_rejected_future, _ = self.jobs_client.subscribe_to_start_next_pending_job_execution_rejected(
                request=start_subscription_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_start_next_pending_job_execution_rejected)
    
            # Wait for subscriptions to succeed
            subscribed_accepted_future.result()
            subscribed_rejected_future.result()
    
            print("Subscribing to Update responses...")
            # Note that we subscribe to "+", the MQTT wildcard, to receive
            # responses about any job-ID.
            update_subscription_request = iotjobs.UpdateJobExecutionSubscriptionRequest(
                    thing_name=self.serial_number,
                    job_id='+')
    
            subscribed_accepted_future, _ = self.jobs_client.subscribe_to_update_job_execution_accepted(
                request=update_subscription_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_update_job_execution_accepted)
    
            subscribed_rejected_future, _ = self.jobs_client.subscribe_to_update_job_execution_rejected(
                request=update_subscription_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_update_job_execution_rejected)
    
            # Wait for subscriptions to succeed
            subscribed_accepted_future.result()
            subscribed_rejected_future.result()
            self.try_start_next_job()

            
        except Exception as e:
            exit(e)
    
    
    def get_ts(self):
        ts_str = str(time.time()).replace('.','')[:13]
        return int(ts_str)
        
    
if __name__== "__main__":

    
    tv = RackTv()
    tv.banner()
    tv.start()
 
    try:
        
        tv.connect(tv.get_serial_number(),tv.get_iot_endpoint())
        tv.listen_for_jobs()
        
        while True:
            time.sleep(30)
     
    except Exception as e: 
        print(e)
        
        
  

