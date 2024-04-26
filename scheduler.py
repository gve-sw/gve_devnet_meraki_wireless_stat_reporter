""" 
Copyright (c) 2024 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
           https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

import meraki
import csv
import os
from datetime import datetime
import time
import config
import schedule

API_KEY = config.api_key
ORGANIZATION_ID = config.organization_id
SSID_NAME = config.ssid_name

# Initialize the Meraki Dashboard API
dashboard = meraki.DashboardAPI(API_KEY,output_log=False,log_path=False,print_console=False)

def fetch_signal(network_id,device_serial):
    response = dashboard.wireless.getNetworkWirelessSignalQualityHistory(network_id,deviceSerial=device_serial,resolution=600,timespan=600)
    return response

def fetch_ping(device_serial):
    response = dashboard.devices.createDeviceLiveToolsPingDevice(device_serial, count=5)
    test_id = response['pingId']
    print('Pausing to wait for ping test')
    time.sleep(10)
    response = dashboard.devices.getDeviceLiveToolsPingDevice(device_serial, test_id)
    return response['results']

def fetch_throughput(device_serial):
    response = dashboard.devices.createDeviceLiveToolsThroughputTest(device_serial)
    test_id = response['throughputTestId']
    print('Pausing to wait for throughput test')
    time.sleep(10)
    response = dashboard.devices.getDeviceLiveToolsThroughputTest(device_serial, test_id)
    if response['status']=='running':
        time.sleep(3)
        response = dashboard.devices.getDeviceLiveToolsThroughputTest(device_serial, test_id)
    return response['result']['speeds']

def fetch_channel_width(device_serial):
    response = {'2.4': 0, '5': 0}
    try:
        # Fetch radio settings from the Meraki API
        radio_settings = dashboard.wireless.getDeviceWirelessStatus(serial=device_serial)
        for ssid in radio_settings['basicServiceSets']:
            if ssid['ssidName'] == SSID_NAME:
                if ssid['band'] == "2.4 GHz":
                    response['2.4'] = ssid["channelWidth"].strip('MHz')
                if ssid['band'] == "5 GHz":
                    response['5'] = ssid["channelWidth"].strip('MHz')
        return response
    except Exception as e:
        print(f"Error fetching channel width for serial {device_serial}: {e}")
        return None
def fetch_channel_utilization(network_id, device_serial):
    resp = {}
    utilization = dashboard.networks.getNetworkNetworkHealthChannelUtilization(networkId=network_id,timespan=600)
    # Extract data for the specific serial
    for device in utilization:
        if device['serial'] == device_serial:
            try:
                resp['wifi0'] = device['wifi0'][0]['utilization']
            except: 
                resp['wifi0'] = 0
            try: 
                resp['wifi1'] = device['wifi1'][0]['utilization']
            except:
                resp['wifi1'] = 0
            try:
                resp['wifi2'] = device['wifi2'][0]['utilization']
            except:
                resp['wifi2'] = 0
            try:
                resp['wifi3'] = device['wifi3'][0]['utilization']
            except:
                resp['wifi3'] = 0
            return resp

def fetch_device_data_rate(network_id, device_serial):
    response = dashboard.wireless.getNetworkWirelessDataRateHistory(network_id,deviceSerial=device_serial,timespan=600,resolution=600)
    return response

def fetch_device_latency(network_id, device_serial):
    response = dashboard.wireless.getNetworkWirelessLatencyHistory(network_id,deviceSerial=device_serial,resolution=600,timespan=600)
    return response

def fetch_device_packet_loss(org_id, device_serial):
    res = {}
    response = dashboard.wireless.getOrganizationWirelessDevicesPacketLossByDevice(org_id,total_pages='all',serials=[device_serial],timespan=600)
    res['downstream'] = response[0]['downstream']['lossPercentage']
    res['upstream'] = response[0]['upstream']['lossPercentage']
    return res

def fetch_ap_stats():
    networks = dashboard.organizations.getOrganizationNetworks(organizationId=ORGANIZATION_ID)
    data = []
    
    for network in networks:
        network_id = network['id']
        devices = dashboard.networks.getNetworkDevices(network_id)
        
        for device in devices:
            if device['model'].startswith('MR'):
                # Device is an AP, we get the performance stats
                packet_loss = fetch_device_packet_loss(ORGANIZATION_ID,device['serial'])
                channel_width = fetch_channel_width(device['serial'])
                channel_utlization = fetch_channel_utilization(network_id, device['serial'])
                data.append({
                    'Timestamp': datetime.now(),
                    'Network': network['name'],
                    'Device Name': device['name'],
                    'Serial': device['serial'],
                    'Channel Utilization wifi 0': channel_utlization['wifi0'],
                    'Channel Utilization wifi 1': channel_utlization['wifi1'],
                    'Channel Utilization wifi 2': channel_utlization['wifi2'],
                    'Channel Utilization wifi 3': channel_utlization['wifi3'],
                    'Channel Width - 2.4': channel_width['2.4'],
                    'Channel Width - 5': channel_width['5'],
                    'Clients': len(dashboard.devices.getDeviceClients(device['serial'],timespan=600)),
                    'Average Throughput': fetch_device_data_rate(network_id, device['serial'])[0]['averageKbps'],
                    'RTT': fetch_device_latency(network_id, device['serial'])[0]['avgLatencyMs'],
                    'Packet Loss - Downstream': packet_loss['downstream'],
                    'Packet Loss - Upstream': packet_loss['upstream'],
                    'SNR': fetch_signal(network_id,device['serial'])[0]['snr']
                })
    
    return data

def save_to_csv(data):
    # Check if the file exists and is empty
    csv_file_path = 'ap_stats.csv'
    file_exists = os.path.isfile(csv_file_path)
    is_empty = True if not file_exists or os.stat(csv_file_path).st_size == 0 else False
    keys = data[0].keys()
    with open('ap_stats.csv', 'a', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        if is_empty:
            dict_writer.writeheader()
        dict_writer.writerows(data)

def task():
    # Example Usage
    print(f"{datetime.now()}: Running the reporting script...")
    ap_data = fetch_ap_stats()
    save_to_csv(ap_data)

def job():
    current_time = datetime.now()
    # Check both time and day of the week (Monday=0, Sunday=6)
    if 8 <= current_time.hour < 16 and current_time.weekday() < 5:
        task()
    else:
        print(f"{datetime.now()}: Out of scheduled hours or not a weekday, no action taken.")

# Schedule the task to run every 10 minutes
schedule.every(10).minutes.do(job)

print("Scheduler started. Monitoring scheduled tasks...")
while True:
    schedule.run_pending()
    time.sleep(1)
