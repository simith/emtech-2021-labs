#!/bin/bash

# install awsiotsdk for python version 2
python3 -m pip install awsiotsdk 

# colorama
sudo pip3 install colorama pyfiglet
# install jq
sudo yum install jq -y
# install openssl
sudo yum install openssl-devel -y
sudo yum groupinstall "Development Tools" -y 
sudo yum install cmake -y

wget https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm -P /tmp
sudo yum install /tmp/epel-release-latest-7.noarch.rpm  -y
sudo yum install libwebsockets -y
sudo yum install mosquitto mosquitto-clients -y
