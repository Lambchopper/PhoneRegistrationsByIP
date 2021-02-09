##################################################
# COLO MRA Connected Phones
# This script is intended to use the UCM RisPort
# to find which phones are registered via the COLO
# MRA and alert the NOC team to reregister the 
# Phone to the HQ MRA EXP-E.
#
# Version 1.1
# Created for Converged Technology Group
# By Dave Lamb - 10/28/2020
#
# Added AXL connection and restart function 
#   so that phones are automatically restarted
#   when they are found on the Colo Expressway
##################################################

from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
from zeep.exceptions import Fault
from zeep.plugins import HistoryPlugin
from requests import Session
from requests.auth import HTTPBasicAuth
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from lxml import etree
import smtplib
from email.message import EmailMessage
import requests
from os.path import abspath


disable_warnings(InsecureRequestWarning)

#================================================================
# Configure Script
#================================================================

#Toggle so restart can be quickly enavled/disabled by changing this variable
restartPhones = True

# Cluster specific variables
username = ''   #UCM UserID
password = ''   #UCM Password
server = ''     #UCM Publisher IP
NodeIP = ''     #IP Address of phones the script should identify
EmailFrom = 'telcom-dudes@acmewidgets.com'  #Email Address of the From Party
EmailTo = 'user1@acmewidgets.com, user2@acmewidgets.com'    #Who gets the email
SMTPServer = 'acmewidgets-com.mail.protection.outlook.com'  #The SMTP Smarthost to send the email to


#================================================================
# Setup UCM Connection Objects
#================================================================

#===================Setup Zeep Soap Client for RIS Connection===================
#Collect path to the UCM AXL Schema
#The schema files are downloaded from UCM > Applications > Plugins > Cisco AXL Toolkit
riswsdl = f'https://{server}:8443/realtimeservice2/services/RISService70?wsdl'

# Define http session and allow insecure connections
rissession = Session()
rissession.trust_env = False
rissession.verify = False
requests.packages.urllib3.disable_warnings()
rissession.auth = HTTPBasicAuth(username, password)

#Define a SOAP client
ristransport = Transport(cache=SqliteCache(), session=rissession, timeout=20)
risclient = Client(wsdl=riswsdl, transport=ristransport)
#===================Setup Zeep Soap Client for RIS Connection==================



#===================Setup Zeep Soap Client for AXL Connection===================
#Collect path to the UCM AXL Schema
#The schema files are downloaded from UCM > Applications > Plugins > Cisco AXL Toolkit
#If we are not restarting Phones, don't bother with setting up the AXL Session
if restartPhones:
    axlwsdl = abspath('axlsqltoolkit/schema/current/AXLAPI.wsdl')
    axllocation = 'https://{host}:8443/axl/'.format(host=server)
    axlbinding = "{http://www.cisco.com/AXLAPIService/}AXLAPIBinding"

    # Define http session and allow insecure connections
    axlsession = Session()
    axlsession.verify = False
    requests.packages.urllib3.disable_warnings()
    axlsession.auth = HTTPBasicAuth(username, password)

    #Define a SOAP client
    axltransport = Transport(cache=SqliteCache(), session=axlsession, timeout=20)
    axlclient = Client(wsdl=axlwsdl, transport=axltransport)
    axlservice = axlclient.create_service(axlbinding, axllocation)
#===================Setup Zeep Soap Client for AXL Connection==================



#================================================================
# Meat and Potatoes 
#================================================================

#Selection Critera for RIS lookup
#We are looking for phones with the CTG-COLO-VCSC IP as the registration iP
#These are phones connected via the COLO Expressway

CmSelectionCriteria = {
    'MaxReturnedDevices': '1000',
    'DeviceClass': 'Phone',
    'Model': '255',
    'Status': 'Any',
    'NodeName': '',
    'SelectBy': 'IPV4Address',
    'SelectItems': {
        'item': NodeIP
    },
    'Protocol': 'Any',
    'DownloadStatus': 'Any'
}

StateInfo = ''

#Execute RIS Query
try:
    risresp = risclient.service.selectCmDeviceExt(CmSelectionCriteria=CmSelectionCriteria, StateInfo=StateInfo)
except Fault:
    show_history()
    raise

#Create Email Object
msg = EmailMessage()
msg['Subject'] = "Phones registered via COLO Expressway"
msg['From'] = EmailFrom
msg['To'] = EmailTo

#Build Command Output
print()
print("Phones registered via COLO Expressway")
print()
print("="*75)
print('{:18}{:30}{:9}{:18}'.format("Name", "Description", "DN", "IP"))
print("="*75)


EmailBody = "Phones registered via COLO Expressway"
EmailBody = EmailBody + "\n\nThis script will automatically restart these phones, to register them to the HQ Expressway."
EmailBody = EmailBody + "\n\n" + "="*75 + "\n" + "{:18}{:30}{:9}{:18}".format("Name", "Description", "DN", "IP") + "\n" + "="*75 + "\n"

#Loop Through RIS results and print values
CmNodes = risresp.SelectCmDeviceResult.CmNodes.item
for CmNode in CmNodes:
    if len(CmNode.CmDevices.item) > 0:
        # If the node has returned CmDevices, save to the snapshot to
        # later compare
        for item in CmNode.CmDevices.item:
            # Creates a new list if the key in the dictionary isn't yet
            # assigned or simply appends to the entry if there is already
            # a value present
            PhoneName = item.Name
            PhoneDesc = item.Description
            LineInfoList = item.LinesStatus.item
            PhoneDN = LineInfoList[0].DirectoryNumber
            IPAddressInfoList = item.IPAddress.item
            PhoneIP = IPAddressInfoList[0].IP
            print('{:18}{:30}{:9}{:18}'.format(PhoneName, PhoneDesc, PhoneDN, PhoneIP))
            EmailBody = EmailBody + "{:18}{:30}{:9}{:18}".format(PhoneName, PhoneDesc, PhoneDN, PhoneIP) + "\n"
            
            #Restart the phones
            if restartPhones:
                axlservice.restartPhone(name = PhoneName)

#Send Email
msg.set_content(EmailBody)
s = smtplib.SMTP(SMTPServer)
s.send_message(msg)
s.quit()
