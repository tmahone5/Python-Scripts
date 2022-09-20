#!/usr/bin/python3

#aws python lib
import boto3

#regex 
#https://docs.python.org/3/library/re.html
import re

#to make api calls
import requests

#store api calls in a json dump file
import json

#os level commands
import os

#defined variables
non_mrktplce_dev=4
non_mrktplce_prod=5
mrktplce_dev=4
mrktplce_impl=5
mrktplce_prod=2

#pulling value from secrets manager in aws and storing it in a variable
secret_id = 'arn:aws:secretsmanager:us-east-1:842420567215:secret:CloudTamer_API_Key-7iPuKK'
#using OS library to create an api token
api_token = os.environ['ct_api_token']
#set var for account number
oc_account_num = '842420567215'
#set var for role
oc_iam_role = 'ct-gss-ado-admin'
#set var for url
ct_API_URL = "https://cloudtamer.cms.gov/api"
#set var account files
account_files=['/ITOPS/ssm-patching/marketplace/accounts']
#account_files=['/ITOPS/ssm-patching/marketplace/accounts','/ITOPS/ssm-patching/non-marketplace/accounts']

#top level for loop evaluating a list called "account files"
for account_file in account_files:
    #prints out each account number in the list above
    print(account_file,'\n')
    oc_cred_response=requests.post(url="{API_URL}/v3/temporary-credentials".format(API_URL=ct_API_URL), data=json.dumps({
                "account_number": oc_account_num,
                "iam_role_name": oc_iam_role 
                }),headers={"Authorization":"Bearer {API_TOKEN}".format(API_TOKEN=api_token)})
    ssm = boto3.client('ssm',
        aws_access_key_id=oc_cred_response.json()['data']['access_key'],
        aws_secret_access_key=oc_cred_response.json()['data']['secret_access_key'],
        aws_session_token=oc_cred_response.json()['data']['session_token']
        )

    #defining a list of account numbers and putting them in a list
    accounts_list = ssm.get_parameter(
                Name="{file}".format(file=account_file)
            )['Parameter']['Value'].split(',')
    #accounts_list=['656395180286']
    for account_num in accounts_list:
        #creating variable account_response using the json and request libraries. Will store the filtered output of API call being made
        account_response=requests.get(url="{API_URL}/v3/account/by-account-number/{cloudtamerAccountNumber}".format(API_URL=ct_API_URL,cloudtamerAccountNumber=account_num),headers={"Authorization":"Bearer {API_TOKEN}".format(API_TOKEN=api_token)})
        if account_response.status_code != 200:
            print(account_num,":HTTP Status Code: ",account_response.status_code,",",account_response.json()['message'])
        elif account_response.status_code == 200:
            cloud_access_role_response=requests.get(url="{API_URL}/v3/project/{id}/cloud-access-role".format(API_URL=ct_API_URL,id=account_response.json()['data']['project_id']),headers={"Authorization":"Bearer {API_TOKEN}".format(API_TOKEN=api_token)})
            iam_role_name = cloud_access_role_response.json()['data']['ou_cloud_access_roles'][0]['aws_iam_role_name']
            #iam_role_name = oc_iam_role
            cred_response=requests.post(url="{API_URL}/v3/temporary-credentials".format(API_URL=ct_API_URL), data=json.dumps({
                "account_number": "{x}".format(x=account_num),
                "iam_role_name": iam_role_name
                }),headers={"Authorization":"Bearer {API_TOKEN}".format(API_TOKEN=api_token)}
            if cred_response.status_code != 200:
                print(account_num,":HTTP Status Code: ",cred_response.status_code,",",cred_response.json()['message'])
            elif cred_response.status_code == 200:
                ssm = boto3.client('ssm',
                aws_access_key_id=cred_response.json()['data']['access_key'],
                aws_secret_access_key=cred_response.json()['data']['secret_access_key'],
                aws_session_token=cred_response.json()['data']['session_token'])
  # see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html?highlight=ssm#SSM.Client.describe_maintenance_windows
                ssm_response = ssm.describe_maintenance_windows(
                    Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                    MaxResults=50,
                )
                   
                for ssm_window in ssm_response['WindowIdentities']:
                    if re.findall(r'^ITOPS.*Non-Mktplc.*Impl.*',ssm_window['Name']):
                        cron_list=ssm_window['Schedule'].split()
                        cron_date=ssm_window['Schedule'].split()[4].split('#')
                        cron_list[4]=cron_date[0]+"#{non_mrktplce_dev}".format(non_mrktplce_dev=non_mrktplce_dev)
                        cron_result=""
                        space_counter=0 
                        for item in cron_list:
                            if space_counter > 0:
                                cron_result=cron_result+' '+item
                            else:
                                cron_result=cron_result+item
                            space_counter += 1
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Schedule=cron_result)
                            ssm_response = ssm.describe_maintenance_windows(
                                Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                                MaxResults=50,
                                )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])
                    elif re.findall(r'^ITOPS.*Non-Mktplc.*Prod.*',ssm_window['Name']):
                        cron_list=ssm_window['Schedule'].split()
                        cron_date=ssm_window['Schedule'].split()[4].split('#')
                        cron_list[4]=cron_date[0]+"#{non_mrktplce_prod}".format(non_mrktplce_prod=non_mrktplce_prod)
                        cron_result=""
                        space_counter=0 
                        for item in cron_list:
                            if space_counter > 0:
                                cron_result=cron_result+' '+item
                            else:
                                cron_result=cron_result+item
                            space_counter += 1
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Schedule=cron_result)
                            ssm_response = ssm.describe_maintenance_windows(
                            Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                            MaxResults=50,
                            )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])
                    elif re.findall(r'^ITOPS.*Mktplc.*Prod.*',ssm_window['Name']) and not re.findall(r'^ITOPS.*Non-Mktplc.*Prod.*',ssm_window['Name']):
                        cron_list=ssm_window['Schedule'].split()
                        cron_date=ssm_window['Schedule'].split()[4].split('#')
                        cron_list[4]=cron_date[0]+"#{mrktplce_prod}".format(mrktplce_prod=mrktplce_prod)
                        cron_result=""
                        space_counter=0 
                        for item in cron_list:
                            if space_counter > 0:
                                cron_result=cron_result+' '+item
                            else:
                                cron_result=cron_result+item
                            space_counter += 1
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Schedule=cron_result)
                            ssm_response = ssm.describe_maintenance_windows(
                            Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                            MaxResults=50,
                            )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])
                    elif re.findall(r'^ITOPS.*Mktplc.*Dev.*',ssm_window['Name']) and not re.findall(r'^ITOPS.*Non-Mktplc.*Dev.*',ssm_window['Name']):
                        cron_list=ssm_window['Schedule'].split()
                        cron_date=ssm_window['Schedule'].split()[4].split('#')
                        cron_list[4]=cron_date[0]+"#{mrktplce_dev}".format(mrktplce_dev=mrktplce_dev)
                        cron_result=""
                        space_counter=0 
                        for item in cron_list:
                            if space_counter > 0:
                                cron_result=cron_result+' '+item
                            else:
                                cron_result=cron_result+item
                            space_counter += 1
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Schedule=cron_result)
                            ssm_response = ssm.describe_maintenance_windows(
                            Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                            MaxResults=50,
                            )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])
                    elif re.findall(r'^ITOPS.*Mktplc.*Impl.*',ssm_window['Name']) and not re.findall(r'^ITOPS.*Non-Mktplc.*Impl.*',ssm_window['Name']):
                        cron_list=ssm_window['Schedule'].split()
                        cron_date=ssm_window['Schedule'].split()[4].split('#')
                        cron_list[4]=cron_date[0]+"#{mrktplce_impl}".format(mrktplce_impl=mrktplce_impl)
                        cron_result=""
                        space_counter=0 
                        for item in cron_list:
                            if space_counter > 0:
                                cron_result=cron_result+' '+item
                            else:
                                cron_result=cron_result+item
                            space_counter += 1
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Schedule=cron_result)
                            ssm_response = ssm.describe_maintenance_windows(
                            Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                            MaxResults=50,
                            )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])
