from os.path import isfile, join
import pandas as pd
import requests
import random
import base64
import time
import adal
import json
import math
import os

path = 'configs/'
onlyfiles = [f for f in os.listdir(path) if isfile(join(path,f))]
fileDict, count = {}, 0
for file in onlyfiles:
    if 'json' in file:
        fileDict[count] = file
        count+=1
inFile = input(f'Select config file (0, 1, 2 etc.)\n{fileDict}\nEnter selection: ')
inFile = fileDict.get(int(inFile))
with open(path+inFile) as f:
	config = json.load(f)

def getAccessKey():
    print('Requesting Azure auth token...')
    clientId = config.get('Azure Account Details').get('Client ID')
    clientSecret = config.get('Azure Account Details').get('Client Secret')
    tenant = config.get('Azure Account Details').get('Tenant')
    authority_url = f'https://login.microsoftonline.com/{tenant}'
    resource = 'https://management.azure.com/'
    context = adal.AuthenticationContext(authority_url)
    token = context.acquire_token_with_client_credentials(resource, clientId, clientSecret)
    headers = {'Authorization': 'Bearer ' + token['accessToken'], 'Content-Type': 'application/json'}
    return headers

def createResourceGroup(subscription, location, resourceGroupName, headers):
    print(f'Creating resource group {resourceGroupName}...')
    # https://docs.microsoft.com/en-us/rest/api/resources/resourcegroups/createorupdate
    url = f'https://management.azure.com/subscriptions/{subscription}/resourcegroups/{resourceGroupName}?api-version=2019-08-01'

    data = {'location':location}

    response = requests.put(url, data=str(data), headers=headers)
    success = False
    while not success:
        try:
            response = requests.put(url, headers=headers, data=str(data))
            responseData = response.json()
            if not responseData.get('id'):
                print(responseData)
                print(response)
                print(response.headers)
            else:
                resourceGroupId = responseData['id']
                success = True
                return resourceGroupId
        except Exception as e:
            print(e)

def checkPublicIpLimit(subscription, location, headers):
    #Used limit: {'currentValue': 50, 'id': 'providers/Microsoft.Network/locations/eastus/usages/PublicIPAddresses', 'limit': 1000, 'name': {'localizedValue': 'Public IP Addresses', 'value': 'PublicIPAddresses'}, 'unit': 'Count'}
    url = f'https://management.azure.com/subscriptions/{subscription}/providers/Microsoft.Network/locations/{location}/usages?api-version=2019-09-01'
    response = requests.get(url, headers=headers)
    for limit in response.json()['value']:
            if limit['name']['value'] == 'PublicIPAddresses':
                ipLimit = limit['limit']
                ipCurrentUsed = limit['currentValue']
    return ipLimit, ipCurrentUsed

def checkVcpuLimit(subscription, location, headers):
    url = f'https://management.azure.com/subscriptions/{subscription}/providers/Microsoft.Compute/locations/{location}/usages?api-version=2019-03-01'
    response = requests.get(url, headers=headers)
    for limit in response.json()['value']:
        if limit['name']['value'] == 'standardBSFamily':
            vcpuLimit = limit['limit']
            vcpuCurrentUsed = limit['currentValue']
    return vcpuLimit, vcpuCurrentUsed

		
def createNetworkSecurityGroup(subscription, location, resourceGroupName, networkSecurityGroupName, headers):
    print(f'Creating networking security group {networkSecurityGroupName}...')
    # https://docs.microsoft.com/en-us/rest/api/virtualnetwork/networksecuritygroups/createorupdate#examples

    url = f'https://management.azure.com/subscriptions/{subscription}/resourceGroups/{resourceGroupName}/providers/Microsoft.Network/networkSecurityGroups/{networkSecurityGroupName}?api-version=2019-09-01'

    data ={
          "properties": {
            "securityRules": [
              {
                "name": "CustomInBound",
                "properties": {
                  "protocol": "*",
                  "sourceAddressPrefix": "*",
                  "destinationAddressPrefix": "*",
                  "access": "Allow",
                  "destinationPortRange": "*",
                  "sourcePortRange": "*",
                  "priority": 100,
                  "direction": "Inbound"
                }
              },
              {
                "name": "CustomOutBound",
                "properties": {
                  "protocol": "*",
                  "sourceAddressPrefix": "*",
                  "destinationAddressPrefix": "*",
                  "access": "Allow",
                  "destinationPortRange": "*",
                  "sourcePortRange": "*",
                  "priority": 100,
                  "direction": "Outbound"
                }
              },
                            
            ]
          },
          "location": location
        }
    
    success = False
    while not success:
        try:
            response = requests.put(url, headers=headers, data=str(data))
            responseData = response.json()
            if not responseData.get('id'):
                print(responseData)
                print(responseData.text)
                print(responseData.headers)
            else:
                networkSecurityGroupId = responseData['id']
                success = True
        except Exception as e:
            print(e)
    return networkSecurityGroupId

def parseHeaders(headers):
    pass

def getAllResources(subscription, headers):
    success, resourceList = False, []
    ignoreTypes = ['Microsoft.Compute/images','Microsoft.Storage/storageAccounts','Microsoft.Network/networkWatchers','Microsoft.Compute/galleries/images','Microsoft.Compute/galleries','Microsoft.Compute/galleries/images/versions'] #,'Microsoft.Network/networkSecurityGroups'
    url = f"https://management.azure.com/subscriptions/{subscription}/resources?api-version=2018-05-01"
    while not success:
        try:
            response = requests.get(url, headers=headers)
            for resource in response.json()['value']:
                if resource.get('type') not in ignoreTypes:
                    resourceList.append(resource)
            success = True
        except Exception as e:
            print(e)
    return resourceList

def getScaleSets(subscription, headers):
    success, resourceList = False, []
    url = f"https://management.azure.com/subscriptions/{subscription}/resources?$filter=resourceType eq 'Microsoft.Compute/virtualMachineScaleSets'&api-version=2018-05-01"
    while not success:
        try:
            response = requests.get(url, headers=headers)
            for resource in response.json()['value']:
                resourceList.append(resource)
            success = True
        except Exception as e:
            print(e)
    return resourceList

def getScaleSetIps(scaleSet, headers):
    # https://docs.microsoft.com/en-us/azure/virtual-machine-scale-sets/virtual-machine-scale-sets-networking
    success = False
    
    url = f"https://management.azure.com/{scaleSet['id']}/publicipaddresses?api-version=2019-03-01"

    while not success:
        print(f'Fetching scale set IPs for region {scaleSet["location"]} scale set {scaleSet["name"]}...')
        response = requests.get(url, headers=headers)
        print(response.json())
        if not response.json().get('value'):
            if 'not found' in response.json().get('error').get('message'):
                print('Scale set IPs not yet provisioned. Retrying in 15 seconds.')
                #success = True
                #scaleSetIpList = []
            else:
                print('Unrecognized response: ')
                print(response.json())
                print(response.headers)
                print(response)
            time.sleep(15)
        else:
            if response.json()['value'][0].get('properties').get('ipAddress'):
                scaleSetIpList = response.json()['value']
                success = True
            else:
                print('Scale set IPs not yet provisioned. Retrying in 15 seconds.')
                time.sleep(15)
    
    return scaleSetIpList

def createIpConfigs(ipCount, subscription, resourceGroupName, virtualNetworkName, subnetName, tag):
    ipConfigList = []
    for x in range(ipCount):
        if x == 0:
            primary = 'true'
        else:
            primary = 'false'
        row = {
            "name": f'RW_IP_{x}_{tag}',
            "properties": {
              "primary": primary,  
              "subnet": {
                "id": f"/subscriptions/{subscription}/resourceGroups/{resourceGroupName}/providers/Microsoft.Network/virtualNetworks/{virtualNetworkName}/subnets/{subnetName}"
              },
            "publicipaddressconfiguration": {
                "name": f'RW_ipConf_{x}_{tag}', #Maybe this needs to be inique ???
                "properties": {
                    "idleTimeoutInMinutes": 15
                    }
                }
            }
            }
        ipConfigList.append(row)
    return ipConfigList

def getYaml():
    with open('cloudinit.yaml', 'rb') as myfile:
        data = myfile.read()
    cloudInit = base64.b64encode(data).decode()
    return cloudInit
    
def createScaleSet(scaleSet, headers):
    scaleSetName = scaleSet['scaleSetName']
    subscription = scaleSet['subscription']
    scaleSetVmCount = scaleSet['vmCount']
    scaleSetProxyCount = scaleSet['proxyCount']
    location = scaleSet['location']
    virtualNetworkName = scaleSet['virtualNetworkName']
    subnetName = scaleSet['subnetName']
    resourceGroupName = scaleSet['resourceGroupName']
    networkSecurityGroupId = scaleSet['networkSecurityGroupId']
    tag = scaleSet['tag']

    yamlConf = getYaml()

    if scaleSetProxyCount % 100 == 0:
        ipsPerVm = 100
    else:
        ipsPerVm = math.floor(scaleSetProxyCount/scaleSetVmCount)
        
    ipConfigList = createIpConfigs(ipsPerVm, subscription, resourceGroupName, virtualNetworkName, subnetName, tag)

    print(f'Deploying {scaleSetName} in region {location} with {scaleSetVmCount} VMs with {ipsPerVm} IPs per VM...')
    success = False
    url = f'https://management.azure.com/subscriptions/{subscription}/resourceGroups/{resourceGroupName}/providers/Microsoft.Compute/virtualMachineScaleSets/{scaleSetName}?api-version=2019-03-01'
    data = {
        "sku": {
          "tier": "Standard",
          "capacity": scaleSetVmCount,
          "name": "Standard_B1ls"
        },
        "location": location,
        "properties": {
          "overprovision": 'false',
          "virtualMachineProfile": {
            "storageProfile": {
              "imageReference": {
                "sku": "18.04-LTS",
                "publisher": "Canonical",
                "version": "latest",
                "offer": "UbuntuServer"
              },
              "osDisk": {
                "caching": "ReadWrite",
                "managedDisk": {
                  "storageAccountType": "Standard_LRS"
                },
                "createOption": "FromImage"
              }
            },
            "osProfile": {
              "computerNamePrefix": 'RW-PC-'+tag,
              "adminUsername": "login",
              "adminPassword": "pass",
              "customData": yamlConf
            },
            "networkProfile": {
              "networkInterfaceConfigurations": [
                {
                  "name": 'RW_NIC_A_'+tag,
                  "properties": {
                    "primary": 'true',
                    "enableIPForwarding": 'true',
                    "ipConfigurations": ipConfigList,
                    "networkSecurityGroup": {
                        "id": networkSecurityGroupId
                        }
                  }
                }                
              ]
            }
          },
          "upgradePolicy": {
            "mode": "Manual"
          }
        }
        }

    while not success:
        try:
            response = requests.put(url, headers=headers, data=str(data))
            responseData = response.json()
            if not responseData.get('id'):
                print(responseData)
                print(response.headers)
                print('Error creating scale set. Sleeping 10 seconds.')
                time.sleep(10)
            else:
                scaleSet['scaleSetId'] = responseData['id']
                scaleSet['status'] = responseData['properties']['provisioningState']
                success = True
        except Exception as e:
            print(f'Hard error creating scale set. Sleeping 10 seconds\n{e}')
            time.sleep(10)
    parseHeaders(response)
    return scaleSet

def createVirtualNetwork(virtualNetworkName, location, subscription, resourceGroupName, headers):
    success = False
    url = 'https://management.azure.com/subscriptions/'+subscription+'/resourcegroups/'+resourceGroupName+'/providers/Microsoft.Network/virtualNetworks/'+virtualNetworkName+'?api-version=2018-08-01'
    data ={"location":location,
          "properties": {
            "addressSpace": {
              "addressPrefixes": [
                "10.0.0.0/16"
              ]
            }
          }
        }
    print('Creating virtual network...')
    while not success:
        try:
            response = requests.put(url, headers=headers, data=str(data))
            responseData = response.json()
            if not responseData.get('id'):
                try:
                    if responseData.get('error').get('details')[0].get('message'):
                        if 'Retryable' in responseData.get('error').get('details')[0].get('code'):
                            print(responseData.get('error').get('details'))
                            sleepTime = int(responseData.get('error').get('details')[0].get('message').split('retried in ')[1].split(' ')[0])
                            print(f'Sleeping for {sleepTime} seconds.')
                            time.sleep(sleepTime)
                except Exception as e:
                    print(e)
                    print(responseData)
                    print(response.headers)
                    print('Error creating virtual network. Sleeping 10 seconds.')
                    time.sleep(10)
            else:
                virtualNetworkId = responseData['id']
                success = True
        except Exception as e:
            print(f'Hard error creating virtual network. Sleeping 10 seconds\n{e}')
            time.sleep(10)
    parseHeaders(response)
    return virtualNetworkId

def createSubnet(subnetName, location, virtualNetworkName, subscription, resourceGroupName, headers, networkSecurityGroupId):
    success = False
    url = 'https://management.azure.com/subscriptions/'+subscription+'/resourcegroups/'+resourceGroupName+'/providers/Microsoft.Network/virtualNetworks/'+virtualNetworkName+'/subnets/'+subnetName+'?api-version=2018-08-01'

    data = {
    "location":location,
      "properties": {
        "addressPrefix": "10.0.0.0/16",
        "networkSecurityGroup": {
           "id": networkSecurityGroupId,
           "location": location
        	}
      }
    }
    print('Creating subnet...')
    while not success:
        try:
            response = requests.put(url, headers=headers, data=str(data))
            responseData = response.json()
            if not responseData.get('id'):
                print(responseData)
                print(response.headers)
                print('Error creating subnet. Sleeping 10 seconds.')
                time.sleep(10)
            else:
                subnetId = responseData['id']
                success = True
        except Exception as e:
            print(f'Hard error creating subnet. Sleeping 10 seconds\n{e}')
            time.sleep(10)
    return subnetId

def deleteResource(resource, headers):
    delResponse = None
    try:
        delResponse = requests.delete('https://management.azure.com/'+resource['id']+'?api-version=2018-06-01',headers=headers)
        if str(delResponse) == '<Response [202]>' or str(delResponse) == '<Response [204]>': #202 accepted, 204 success
            return True
        else:
            print(f'Non-202 response for resource deletion {resource}.')
            print(delResponse)
            print(delResponse.headers)
            print(delResponse.text)
    except Exception as e:
        print(f'Exception caught:\n{e}\nSleeping 10 seconds.')
        time.sleep(10)
    return True

def deployRegion(regionSet, tag='RWFO'):
    region = regionSet['region']
    totalProxies = regionSet['totalProxies']
    scaleSets = regionSet['scaleSets']
    location = config['Azure Regions'].get(region)

    subscription = config.get('Azure Account Details').get('Subscription ID')
    headers = getAccessKey()

    print('Deploying scale sets...')
    startTime = time.time()
    
    resourceGroupName = f'RWFO_RG_{random.randint(1000,99999)}'
    resourceGroupId = createResourceGroup(subscription, location, resourceGroupName, headers)
    networkSecurityGroupName = f'RWFO_NSG_{random.randint(1000,99999)}'
    networkSecurityGroupId = createNetworkSecurityGroup(subscription, location, resourceGroupName, networkSecurityGroupName, headers)
        
    vnetIndex = -1
    for scaleSet in scaleSets: 
        virtualNetworkName, subnetName = f'RW_VNet_{tag}_{random.randint(0,9999)}',f'RW_Subnet_{random.randint(0,9999)}'
        virtualNetworkId = createVirtualNetwork(virtualNetworkName, location, subscription, resourceGroupName, headers)
        subnetId = createSubnet(subnetName, location, virtualNetworkName, subscription, resourceGroupName, headers, networkSecurityGroupId)

        scaleSet['vmCount'] = math.ceil(scaleSet['proxyCount'] / 100)
        scaleSet['scaleSetName'] = f'RW_SS_{tag}_{random.randint(0,9999)}'
        scaleSet['tag'] = tag
        scaleSet['status'] = 'Defined'
        scaleSet['networkSecurityGroupName'] = networkSecurityGroupName
        scaleSet['networkSecurityGroupId'] = networkSecurityGroupId
        scaleSet['resourceGroupName'] = resourceGroupName #all in same resource group now.
        scaleSet['resourceGroupId'] = resourceGroupId
        scaleSet['subscription'] = subscription
        scaleSet['location'] = location
        scaleSet['virtualNetworkName'] = virtualNetworkName
        scaleSet['virtualNetworkId'] = virtualNetworkId
        scaleSet['subnetName'] = subnetName
        scaleSet['subnetId'] = subnetId

    for scaleSet in scaleSets:
        scaleSet = createScaleSet(scaleSet, headers)
    endTime = time.time()
    print(f'Deployed {len(scaleSets)} scale sets in region {location} in {round(endTime-startTime,2)} seconds.')    
    return regionSet
    

def deploy():
    print('Loading tasks...') #Load in tasks ; print totals for display, save to dict in scaleset lists of 100 per scaleset
    regionalTaskList, taskInputDict, totalProxies = [], config.get('Proxies'), 0
    for region in taskInputDict:      
        regionValue = taskInputDict.get(region)
        if regionValue != 0:
            count = 0
            scaleSetValues = []
            for x in range(regionValue // 100):
                scaleSetValues.append({'scaleSetNum':count,'proxyCount':100})
                count+=1
            if regionValue % 100 != 0:
                scaleSetValues.append({'scaleSetNum':count,'proxyCount':regionValue % 100})
            totalProxies = totalProxies + regionValue
            regionalTaskList.append({'region':region,'totalProxies':regionValue,'scaleSets':scaleSetValues})
            print(f'{region}\t{regionValue}'.expandtabs(20))
    tag = input('Tasks loaded. Enter a resource tag: ')

    fullStartTime = time.time()
    for regionSet in regionalTaskList:
        regionSet = deployRegion(regionSet, tag)
    fullEndTime = time.time()
    print(f'Deployed {totalProxies} proxies in {round(fullEndTime-fullStartTime,2)} seconds. Fetching IPs...')

    fetchProxies()


def deleteResources():
    subscription = config.get('Azure Account Details').get('Subscription ID')
    headers = getAccessKey()

    scaleSetList = getScaleSets(subscription, headers)
    print(f'Deleting {len(scaleSetList)} scale sets...')
    for scaleSet in scaleSetList:
        deleteResource(scaleSet, headers)
    resourceList = getAllResources(subscription, headers)
    print(f'Deleting {len(resourceList)} other resources...')
    for resource in resourceList: #Need to loop this deletion ; subnet hangs until scaleset delete processes
        #if resource['type'] != 'Microsoft.Compute/virtualMachineScaleSets':
        deleteResource(resource, headers)


def fetchProxies():
    scaleSetIpList = []
    headers = getAccessKey()
    subscription = config.get('Azure Account Details').get('Subscription ID')
    
    scaleSetList = getScaleSets(subscription, headers)
    for scaleSet in scaleSetList:
        ipList = getScaleSetIps(scaleSet, headers)
        for ip in ipList:
            ipRow = {
                'scaleSet':scaleSet,
                'location':scaleSet['location'],
                'proxy':f'{ip["properties"]["ipAddress"]}:3128:login:pass'
                }
            scaleSetIpList.append(ipRow)

    keys = scaleSetIpList[0].keys()
    a = pd.DataFrame.from_dict(scaleSetIpList)
    a.to_excel('proxyOutput.xlsx')  

def checkLimits():
    limits = {}
    headers = getAccessKey()
    subscription = config.get('Azure Account Details').get('Subscription ID')
    for region in config['Azure Regions']:
        location = config['Azure Regions'][region]
        ipLimit, ipCurrentUsed = checkPublicIpLimit(subscription, location, headers)
        vcpuLimit, vcpuCurrentUsed = checkVcpuLimit(subscription, location, headers)
        limits[location] = {'ipLimit':ipLimit,'ipCurrentUsed':ipCurrentUsed,'vcpuLimit':vcpuLimit,'vcpuCurrentUsed':vcpuCurrentUsed}
    for limit in limits:
        print(f'{limit}: {limits[limit]}')



def rebootScaleSets():
	headers = getAccessKey()
	subscription = config.get('Azure Account Details').get('Subscription ID')
	scaleSetList = getScaleSets(subscription, headers)
	ids = []
	for scaleSet in scaleSetList:
		ids.append(scaleSet['id'])
	for idd in ids:
		url = 'https://management.azure.com/'+idd+'/restart?api-version=2019-12-01'
		req = requests.post(url, headers=headers)

	print('Rebooting all ScaleSets - Please wait')

    
taskSelection = int(input('Enter task selection:\n0 Deploy Scale Sets\n1 Fetch IPs\n2 Delete Resources\n3 Check Limits\n4 Reboot ScaleSets\n Enter Selection: '))
if taskSelection == 0:
    deploy()
elif taskSelection == 1:
    fetchProxies()
elif taskSelection == 2:
    deleteResources()
elif taskSelection == 3:
    checkLimits()
elif taskSelection == 4:
	rebootScaleSets()
