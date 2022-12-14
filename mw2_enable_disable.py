#!/usr/bin/python3
# Must run export api command prior to running this script
# example:   export ct_api_token=app_13986_O4p21aM6gpRPrV4HTaV34jd88efjfee 
import boto3
import re
import requests
import json
import os
#True means MW's are enabled / False means MW's are not-enabled
non_mrktplce_dev=True
non_mrktplce_prod=True
mrktplce_dev=False
mrktplce_impl=False
mrktplce_prod=False

#secret_id = 'arn:aws:secretsmanager:us-east-1:842420567215:secret:CloudTamer_API_Key-7iPuKK'
api_token = os.environ['ct_api_token']
oc_account_num = '842420567215'
oc_iam_role = 'ct-gss-ado-admin'
ct_API_URL = "https://cloudtamer.cms.gov/api"
account_files=['/ITOPS/ssm-patching/marketplace/accounts']
#account_files=['/ITOPS/ssm-patching/non-marketplace/accounts']
for account_file in account_files:
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
    # Pulls from SSM Parmater store OR you can enter accounts manually    
    accounts_list = ssm.get_parameter(
                Name="{file}".format(file=account_file)
            )['Parameter']['Value'].split(',')
    #accounts_list=[ '842420567215', '464673255361', '444783909713','517475254363', '052042835508', '758011882210' ]
    for account_num in accounts_list:
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
                }),headers={"Authorization":"Bearer {API_TOKEN}".format(API_TOKEN=api_token)})
            if cred_response.status_code != 200:
                print(account_num,":HTTP Status Code: ",cred_response.status_code,",",cred_response.json()['message'])
            elif cred_response.status_code == 200:
                ssm = boto3.client('ssm',
                aws_access_key_id=cred_response.json()['data']['access_key'],
                aws_secret_access_key=cred_response.json()['data']['secret_access_key'],
                aws_session_token=cred_response.json()['data']['session_token'])
                ssm_response = ssm.describe_maintenance_windows(
                    #Filters= [ { 'Key':'Enabled', 'Values':['False',] }, ],
                    MaxResults=50,
                )
                   
                for ssm_window in ssm_response['WindowIdentities']:
                    if re.findall(r'^ITOPS.*Non-Mktplc.*Impl.*',ssm_window['Name']):
                        mw_list=ssm_window['WindowId']                        
                        for item in mw_list:
                            ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Enabled=non_mrktplce_dev)                                                           
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'])                                              
                            ssm_response = ssm.describe_maintenance_windows(
                                #Filters= [ { 'Key':'Enabled', 'Values':['False',] }, ],
                                MaxResults=50,
                                )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'],ssm_window['Enabled'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])
                    elif re.findall(r'^ITOPS.*Non-Mktplc.*Prod.*',ssm_window['Name']):
                        mw_list=ssm_window['WindowId'] 
                        for item in mw_list:
                            ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Enabled=non_mrktplce_prod)
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'])
                            ssm_response = ssm.describe_maintenance_windows(
                            #Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                            MaxResults=50,
                            )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'],ssm_window['Enabled'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])
                    elif re.findall(r'^ITOPS.*Mktplc.*Prod.*',ssm_window['Name']) and not re.findall(r'^ITOPS.*Non-Mktplc.*Prod.*',ssm_window['Name']):
                        mw_list=ssm_window['WindowId'] 
                        for item in mw_list:
                            ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Enabled=mrktplce_prod)
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],)
                            ssm_response = ssm.describe_maintenance_windows(
                            #Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                            MaxResults=50,
                            )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'],ssm_window['Enabled'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])
                    elif re.findall(r'^ITOPS.*Mktplc.*Dev.*',ssm_window['Name']) and not re.findall(r'^ITOPS.*Non-Mktplc.*Dev.*',ssm_window['Name']):
                        mw_list=ssm_window['WindowId'] 
                        for item in mw_list:
                            ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Enabled=mrktplce_dev)
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'])
                            ssm_response = ssm.describe_maintenance_windows(
                            #Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                            MaxResults=50,
                            )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'],ssm_window['Enabled'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])
                    elif re.findall(r'^ITOPS.*Mktplc.*Impl.*',ssm_window['Name']) and not re.findall(r'^ITOPS.*Non-Mktplc.*Impl.*',ssm_window['Name']):
                        mw_list=ssm_window['WindowId']
                        for item in mw_list:
                            ssm.update_maintenance_window(WindowId=ssm_window['WindowId'],Enabled=mrktplce_impl)     
                        try:
                            update_response = ssm.update_maintenance_window(WindowId=ssm_window['WindowId'])
                            ssm_response = ssm.describe_maintenance_windows(
                            #Filters= [ { 'Key':'Enabled', 'Values':['True',] }, ],
                            MaxResults=50,
                            )
                            print("Name: "+ssm_window['Name']+","+"Schedule: "+ssm_window['Schedule'],ssm_window['Enabled'])
                        except BaseException as error:
                            print(error)
                            print("Unable to update maintenance window: "+ ssm_window['Name'])                