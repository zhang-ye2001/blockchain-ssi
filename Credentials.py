import  asyncio
import time
from indy import anoncreds, crypto, did, ledger, pool, wallet, IndyError
from indy.error import ErrorCode

import json
from typing import Optional
import random 

async def send_schema(pool_handle, wallet_handle, _did, schema):
    schema_request = await ledger.build_schema_request(_did, schema)
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, _did, schema_request)


async def send_cred_def(pool_handle, wallet_handle, _did, cred_def_json):
    cred_def_request = await ledger.build_cred_def_request(_did, cred_def_json)
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, _did, cred_def_request)


async def get_schema(pool_handle, _did, schema_id):
    get_schema_request = await ledger.build_get_schema_request(_did, schema_id)
    get_schema_response = await ledger.submit_request(pool_handle, get_schema_request)
    return await ledger.parse_get_schema_response(get_schema_response)


async def get_cred_def(pool_handle, _did, cred_def_id):
    get_cred_def_request = await ledger.build_get_cred_def_request(_did, cred_def_id)
    get_cred_def_response = await ledger.submit_request(pool_handle, get_cred_def_request)
    return await ledger.parse_get_cred_def_response(get_cred_def_response)


async def get_credential_for_referent(search_handle, referent):
    credentials = json.loads(
        await anoncreds.prover_fetch_credentials_for_proof_req(search_handle, referent, 10))
    return credentials[0]['cred_info']


async def schema_create(User_info):
    name =  input('请输出该Credentials Schema名称:')

    '''version = input('请输出该Credentials Schema版本号:')
    attributes = []
    while True:
        massage = input('请输出该Credentials Schema包含的属性,输入EOF表示结束输入:')
        if massage == 'EOF':
            break
        attributes,append(massage)'''
    
    '''attributes = []
    r = random.randint(1, 10000)
    for i in range (0, 20):
        attributes.append(str(i) + str(i))'''
    schema_ ={
        'name': name,
        'version': '1.2',
        'attributes': ['first_name', 'last_name', 'degree', 'status', 'year', 'average', 'ssn']
        #'attributes': attributes
    }

    (User_info[name + '_schema_id'], User_info[name + '_schema']) = \
    await anoncreds.issuer_create_schema(User_info['did'], schema_['name'], 
                                         schema_['version'], json.dumps(schema_['attributes']))


    await send_schema(User_info['pool'], User_info['wallet'], 
                      User_info['did'], User_info[name + '_schema'])
    schema_list = json.dumps({name: User_info[name + '_schema_id']})
    with open("schema_list.json", "w") as f:
        f.write(schema_list)

    return User_info, schema_['name']

async def definition_create(User_info, schema_id):
    name = input('请输出该Credentials Definition名称:')
    # name = schema_id    
    (User_info[name + '_schema_id'], User_info[name +'_schema']) = \
        await get_schema(User_info['pool'], User_info['did'], schema_id)

    cred_def = {
        'tag': 'TAG1',
        'type': 'CL',
        'config': {"support_revocation": False}
    }      

    (User_info[name + '_cred_def_id'], User_info[name + '_cred_def']) = \
        await anoncreds.issuer_create_and_store_credential_def(User_info['wallet'], User_info['did'],
                                                               User_info[name + '_schema'], cred_def['tag'],
                                                               cred_def['type'],
                                                               json.dumps(cred_def['config']))    
                                                               
    await send_cred_def(User_info['pool'], User_info['wallet'], User_info['did'], User_info[name + '_cred_def'])
    cred_def_list = json.dumps({name: User_info[name + '_cred_def_id']})
    with open("cred_def_list.json", "w") as f:
        f.write(cred_def_list)
    return User_info, name
