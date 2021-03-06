#!/usr/bin/env python
import json
import logging
import os
import pytz
import requests
import sys
import types

from collections import OrderedDict
from datetime import datetime
from pytz import timezone

DATA_DIR = os.getenv("OPENSHIFT_DATA_DIR", '')
JSON_FILE = DATA_DIR + 'current.json'
PUSHBULLET_KEY_FILE = DATA_DIR + '.pb_key'
PASSWORD_FILE = DATA_DIR + '.cp_passwd'

logging.basicConfig(
    filename='process.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# Turn down requests module's logging
logging.getLogger("requests").setLevel(logging.WARNING)


def get_status_for_location(query_url):

    # Get user name and password from a file
    with open(PASSWORD_FILE) as passwd_file:
        credentials = [x.strip().split(':') for x in passwd_file.readlines()]
    cp_username, cp_password = credentials[0]


    # Validate user
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:21.0) Gecko/20100101 Firefox/21.0',
        'Host': 'na.chargepoint.com',
        'Referer': 'https://na.chargepoint.com/',
        'X-Requested-With': 'XMLHttpRequest'}
    login_data = {
        'user_name': cp_username,
        'user_password': cp_password,
        'recaptcha_response_field': '',
        'timezone_offset': '480',
        'timezone': 'PST',
        'timezone_name': ''}
    url = 'https://na.chargepoint.com/users/validate'


    logging.info("###Validating user with post %s # %s# %s", url, headers, login_data)
    req = session.post(url, headers=headers, data=login_data, verify=False)
    print("###User validation response:", req)
    logging.info("###User validation return value was %s", req.text)
    if req.status_code != 200:
	return None

    # Getting list of chargers and their status
    query_data=''
    headers=''
    req = session.post(query_url, headers=headers, data=query_data, verify=False)
    print("###Getting charger data response: %s", req)
    if req.status_code != 200:
	return None

    ## This call log raw data
    logging.info("###Getting charger data return value was %s", req.text)

    data = req.json()

    print("###Iterating stations")
    total_number_ports = 0
    total_number_stations = 0
    total_available = 0
    summaries = data['station_list']['summaries']
    port_status = {}
    for summary in summaries:
        if 'station_name' not in summary:
            continue

        station_name = ' '.join(summary['station_name'])
        number_ports = summary['port_count']['total']
        available = summary['port_count']['available']
        device_id = summary['device_id']
        status = summary['station_status']
        total_number_ports = total_number_ports + number_ports
	total_number_stations = total_number_stations + 1
    	total_available = total_available + available

	logging.info("### Device %s, %s, %d / %d, %s", device_id, station_name, available, number_ports, status)
	print("### ID", device_id, station_name, available, number_ports, status)
        port_status[device_id] = (station_name, available, number_ports, status)

    print("### Done Gettting Status - Grand total - Stations: ", total_number_stations, " Ports: ", total_number_ports, "Available:", total_available)
    return port_status


# Given a location (list of device IDs), return total number of ports and available ports
def summarize_location(location_name, station_list, port_status):
    location_data = OrderedDict()
    total = 0
    available = 0
    for station_id in station_list:
        if station_id not in port_status:
            continue
	print("Found ", station_id, "#", port_status[station_id][0], port_status[station_id][1],"of", port_status[station_id][2])

        total = total + port_status[station_id][2]
        available = available + port_status[station_id][1]

    location_data[location_name] = [total, available, 0]
    return location_data


# main routine to get charge stations status and build summary table of their status
def get_charger_status_for_comapny():


    # Each URL has different coordinates.  This is a way to make sure chargepoint returns list of stations that include target 
    # locations.  It still returns stations from near-by, so filter them out by company name first.
 
    # URL with coordinates for VMware
    vmware_query_url='https://mc.chargepoint.com/map-prod/get?{%22station_list%22:{%22ne_lat%22:37.40326613813511,%22ne_lon%22:-122.12273264881287,%22sw_lat%22:37.39303811289964,%22sw_lon%22:-122.15700055118714,%22page_size%22:100,%22page_size%22:100,%22page_offset%22:%22%22,%22sort_by%22:%22distance%22,%22filter%22:{%22connector_l1%22:false,%22connector_l2%22:true,%22is_bmw_dc_program%22:false,%22is_nctc_program%22:false,%22connector_chademo%22:false,%22connector_combo%22:false,%22connector_tesla%22:false,%22price_free%22:false,%22status_available%22:false,%22network_chargepoint%22:true,%22network_blink%22:false,%22network_semacharge%22:false,%22network_evgo%22:false},%22user_lat%22:37.3981436,%22user_lon%22:-122.1399129},%22user_id%22:453339}'

    # URL with coordinates for LinkedIn Sunnyvale ALL except 1000 Maude
    linkedin_query_url='https://mc.chargepoint.com/map-prod/get?{%22station_list%22:{%22ne_lat%22:37.394813674703265,%22ne_lon%22:-122.02370010316372,%22sw_lat%22:37.38969925979908,%22sw_lon%22:-122.03942857682705,%22page_size%22:100,%22page_offset%22:%22%22,%22sort_by%22:%22distance%22,%22screen_width%22:1513,%22screen_height%22:714,%22filter%22:{%22connector_l1%22:false,%22connector_l2%22:true,%22is_bmw_dc_program%22:false,%22is_nctc_program%22:false,%22connector_chademo%22:false,%22connector_combo%22:false,%22connector_tesla%22:false,%22price_free%22:false,%22status_available%22:false,%22network_chargepoint%22:true,%22network_blink%22:true,%22network_semacharge%22:false,%22network_evgo%22:false,%22connector_l2_nema_1450%22:true,%22connector_l2_tesla%22:false},%22user_lat%22:37.373725,%22user_lon%22:-122.1134166,%22include_map_bound%22:true},%22user_id%22:255431}'


# %22ne_lat%22:37.394813674703265,%22ne_lon%22:-122.02370010316372,%22sw_lat%22:37.38969925979908,%22sw_lon%22:-122.03942857682705
# %22ne_lat%22:37.43493620380932,%22ne_lon%22:-121.86945833265781,%22sw_lat%22:37.35310750758341,%22sw_lon%22:-122.22462572157383

    # URL with coordinates for LinkedIn just 1000 Maude
    linkedin1000_query_url='https://mc.chargepoint.com/map-prod/get?{%22station_list%22:{%22ne_lat%22:37.43493620380932,%22ne_lon%22:-121.86945833265781,%22sw_lat%22:37.35310750758341,%22sw_lon%22:-122.22462572157383,%22page_size%22:500,%22filter%22:{%22connector_l1%22:false,%22connector_l2%22:true,%22is_bmw_dc_program%22:false,%22is_nctc_program%22:false,%22connector_chademo%22:false,%22connector_combo%22:false,%22connector_tesla%22:false,%22price_free%22:false,%22status_available%22:false,%22network_chargepoint%22:true,%22network_blink%22:true,%22network_semacharge%22:false,%22network_evgo%22:false,%22connector_l2_nema_1450%22:true,%22connector_l2_tesla%22:false}},%22user_id%22:255431}'


    # URL with coordinates for Netflix
    netflix_query_url='https://mc.chargepoint.com/map-prod/get?{%22station_list%22:{%22ne_lat%22:37.26127813228069,%22ne_lon%22:-121.94680653512478,%22sw_lat%22:37.251030759462495,%22sw_lon%22:-121.98107443749905,%22page_size%22:100,%22page_offset%22:%22%22,%22sort_by%22:%22distance%22,%22filter%22:{%22connector_l1%22:false,%22connector_l2%22:true,%22is_bmw_dc_program%22:false,%22is_nctc_program%22:false,%22connector_chademo%22:false,%22connector_combo%22:false,%22connector_tesla%22:false,%22price_free%22:false,%22status_available%22:false,%22network_chargepoint%22:true,%22network_blink%22:false,%22network_semacharge%22:false,%22network_evgo%22:false},%22user_lat%22:37.3981436,%22user_lon%22:-122.1399129},%22user_id%22:255431}'

    # URL with coordinates for Adobe San Jose
    adobe_query_url='https://mc.chargepoint.com/map-prod/get?{%22station_list%22:{%22ne_lat%22:37.33133616678112,%22ne_lon%22:-121.88787096735001,%22sw_lat%22:37.32877683894866,%22sw_lon%22:-121.89715677495957,%22page_size%22:100,%22page_size%22:100,%22page_offset%22:%22%22,%22sort_by%22:%22distance%22,%22filter%22:{%22connector_l1%22:false,%22connector_l2%22:true,%22is_bmw_dc_program%22:false,%22is_nctc_program%22:false,%22connector_chademo%22:false,%22connector_combo%22:false,%22connector_tesla%22:false,%22price_free%22:false,%22status_available%22:false,%22network_chargepoint%22:true,%22network_blink%22:false,%22network_semacharge%22:false,%22network_evgo%22:false},%22user_lat%22:37.3981436,%22user_lon%22:-122.1399129},%22user_id%22:255431}'

    # URL with coordinates for Intuit Mt View
    intuit_query_url='https://mc.chargepoint.com/map-prod/get?{%22station_list%22:{%22ne_lat%22:37.4301772334932,%22ne_lon%22:-122.08839565515518,%22sw_lat%22:37.425065232426554,%22sw_lon%22:-122.10487514734268,%22page_size%22:100,%22page_size%22:100,%22page_offset%22:%22%22,%22sort_by%22:%22distance%22,%22filter%22:{%22connector_l1%22:false,%22connector_l2%22:true,%22is_bmw_dc_program%22:false,%22is_nctc_program%22:false,%22connector_chademo%22:false,%22connector_combo%22:false,%22connector_tesla%22:false,%22price_free%22:false,%22status_available%22:false,%22network_chargepoint%22:true,%22network_blink%22:false,%22network_semacharge%22:false,%22network_evgo%22:false},%22user_lat%22:37.3981436,%22user_lon%22:-122.1399129},%22user_id%22:255431}'

    # URL with coordinates for Intuit Menlo Park
    intuit_mp_query_url='https://mc.chargepoint.com/map-prod/get?{%22station_list%22:{%22ne_lat%22:37.48210016923632,%22ne_lon%22:-122.16587394475937,%22sw_lat%22:37.479545986193386,%22sw_lon%22:-122.17453747987747,%22page_size%22:100,%22page_size%22:100,%22page_offset%22:%22%22,%22sort_by%22:%22distance%22,%22filter%22:{%22connector_l1%22:false,%22connector_l2%22:true,%22is_bmw_dc_program%22:false,%22is_nctc_program%22:false,%22connector_chademo%22:false,%22connector_combo%22:false,%22connector_tesla%22:false,%22price_free%22:false,%22status_available%22:false,%22network_chargepoint%22:true,%22network_blink%22:false,%22network_semacharge%22:false,%22network_evgo%22:false},%22user_lat%22:37.3981436,%22user_lon%22:-122.1399129},%22user_id%22:255431}'

    # List of charging device IDs for a companhy 
    # These lists are used for how each stations are organized at a company
    # label will be used as location label, numbers are actual device ID assigned by chargepoint.com


   ## LinkedIn Sunnyvale locations
    linkedin_stations_all = {
	'SV-580':{95883, 92171, 92167, 92169, 155519, 92165, 91313},
	'815 W MAUDE':{130251, 145769},
	'880 W MAUDE':{156619, 156611, 156599, 156613},
	'605 STATION':{98897, 98489, 98909, 98583, 98467, 98801, 98885, 74123, 98899, 67663, 98887, 98889, 98901},
	'479 N PASTORIA':{131609, 131647, 131641, 131445},
	'680 VAQUEROS':{72553, 67783},
	'599 MATHILDA':{67663, 74123},
	'755 MATHILDA':{91719, 92025},
	'950 MAUDE':{155489, 153507, 153521, 153829, 153699, 153839, 153499, 153543, 153515, 155495, 153497, 153523, 153519, 159629, 155601}}


   ## LinkedIn Sunnyvale locations Just 1000 Maude
    linkedin1000_stations_all = {
	'1000 MAUDE':{153633,157861, 153619, 153641, 153635, 159613, 153643, 153517, 159607, 
		153647, 163021, 153637, 155247, 155481, 153841, 153629, 157187, 163023, 153583, 
		159609, 155493, 159627, 153645, 157881, 153621, 162669, 153639}}

    ## VMware locations
#    vmw_stations_all = {
#	'Cntl South Garage':{79403, 79363, 79333, 79383, 79083, 34743, 71263},
#	'Cntl North Garage':{150415, 132323, 132311, 132337, 132647},
#	'Hilltop Garage':{92219, 91749, 91783, 92525, 92197, 91753, 91777, 91781},
#	'Creekside (Uber) Garage':{98831, 111415, 92191, 91785, 92533, 91141, 91759, 91091}}

    ## VMware locations AS of Jan 31, 2017
    vmw_stations_all = {
	'Cntl South Garage':{79403, 79363, 79333, 79383, 79083, 34743, 71263},
	'Cntl North Garage':{150415, 132323, 132311, 132337, 132647, 168665, 174769, 174773, 174297, 175671},
	'Hilltop Garage':{92219, 91749, 91783, 92525, 92197, 91753, 91777, 91781},
	'Creekside Garage':{111415, 92191, 91785}}

    ## NETFLIX locations
    netflix_stations_all = {
    	'Building A':{34213, 3774, 98023, 97801,97811},
	'Building B':{34323, 93721, 34903},
	'Building D':{117361, 116063, 116059, 116075, 116045, 116027, 116069, 116061, 116065},
	'Building E':{117285},
	'Garage Lvl 2':{124923, 123723, 122945, 123747, 124739, 124919, 124891, 124929, 124741, 124925, 124889},
	'Garage Lvl 3':{123745, 124793, 124945, 124921, 124915},
	'Garage Lvl 4':{116003, 116009, 116005, 116067, 145205, 117387, 116011, 115959, 116031, 116029, 115961, 116007, 116001}}

    ## Adobe locations
    adobe_stations_all = {
	'Almaden Tower 5':{128175},
	'East Tower 1':{141739},
	'East Tower 4':{162255},
	'East Tower 5':{65253, 46293, 46463, 88125, 165967, 88193, 4792, 4281},
	'West Tower 5':{163151, 128329, 165997}}
##	'East Tower 4':{162255, 165995, 163161, 165969},
##	'East Tower 5':{4281, 4792, 2993, 88125, 88193, 46463, 46293, 65253},
##	'West Tower 5':{3499, 4612, 4614, 128329}}


    ## Intuit Mountain View locations
#    intuit_stations_all = {
#	'Bldg 1':{104375, 104377},
#	'Bldg 2':{92161, 91775},
#	'Bldg 4':{104013, 105173},
#	'Bldg 6':{104015, 105215, 105175},
#	'Bldg 8':{5404, 6508},
#	'Bldg 11':{103869, 106425},
#	'Bldg 14':{103949, 107299}}

    xxxintuit_stations_all = {
	'Bldg 1':{104375, 104377},
	'Bldg 2':{92161, 91775},
	'Bldg 4':{104013, 105173},
	'Bldg 6':{104015, 105215, 105175},
	'Bldg 8':{5404, 6508, 121803, 122855, 121785, 121367, 122631, 121771, 121799, 121809, 121811, 120579},
	'Bldg 11':{103869, 122943, 122501, 106425, 122525, 122969, 122495},
	'Bldg 14':{103949, 107299},
	'Bldg 20':{153273, 118143, 119811, 153407, 118115, 153389, 119809},
	'Bldg 20G':{152825, 118129, 152845, 119829, 153333, 153413}}

    intuit_stations_all = {
	'Bldg 1':{104375, 104377},
	'Bldg 2':{92161, 91775},
	'Bldg 4':{104013, 105173},
	'Bldg 6':{104015, 105215, 105175},
	'Bldg 8':{5404, 6508, 122631, 120579},
	'Bldg 11':{103869, 122943, 122501, 106425, 122525, 122969, 122495},
	'Bldg 14':{103949, 107299},
	'Bldg 20':{153273, 118143, 119811, 153407, 118115, 153389, 119809},
	'Bldg 20G':{152825, 118129, 152845, 119829, 153333, 153413}}

    ## Intuit Menlo Park locations
    intuit_mp_stations_all = {
	'180 Jefferson':{105213, 105225, 105227, 105209, 104023},
	'200 Jefferson':{103961, 106421, 107111, 107151, 107187, 106599}}

    ###########################################
    ## MAKE SURE WHICH LOCATION YOU WANT
    ###########################################



    ## Netflix
    company = netflix_stations_all
    query_url = netflix_query_url


    ## Intuit MP
    company = intuit_mp_stations_all
    query_url = intuit_mp_query_url

 
    ## Adobe
    company = adobe_stations_all
    query_url = adobe_query_url

    ## Intuit MV
    company =intuit_stations_all
    query_url = intuit_query_url


    ## LinknedIn Sunnyvale just 1000 Maude
    company =linkedin1000_stations_all
    query_url = linkedin1000_query_url

    ## LinknedIn Sunnyvale EXCEPT 1000 Maude
    company =linkedin_stations_all
    query_url = linkedin_query_url

   ## Vmware
    company = vmw_stations_all
    query_url = vmware_query_url
 
    ## First get charging station status
    port_status = []
    port_status = get_status_for_location(query_url) 

    company_data = OrderedDict()

    # The data can contain stations from other companies, so filter them out using the chrager device ID
    # iterate all stations in a company, build summary of charger status based on the devidce ID list
    for one_location in company:
	print("***", one_location)
	company_data[one_location] = summarize_location(one_location, company[one_location], port_status)
    	logging.info("###%s - %s", one_location, company_data[one_location])

    write_to_file(company_data)
    return company_data


def write_to_file(data):
    print("### Writing to file")
    new_data = data

    new_data['last_updated_epoch'] = (datetime.now() - datetime(1970, 1, 1)).total_seconds()
    with open(JSON_FILE, "w") as outfile:
        outfile.write(json.dumps(new_data, indent=2))


if __name__ == '__main__':
    get_charger_status_for_comapny()
