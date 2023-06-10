import asyncio
import time
from indy import did, ledger, wallet, pool, IndyError, anoncreds, crypto
from indy.error import ErrorCode

import Pool, Wallet, get_verinym, Credentials
import session_initiation, session_acceptance 
import json

async def send_nym(pool_handle, wallet_handle, _did, new_did, new_key, role):
    nym_request = await ledger.build_nym_request(_did, new_did, new_key, None, role)
    # 可以在metadata里面补充一些比如以注册成功等信息
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, _did, nym_request)


async def auth_decrypt(wallet_handle, key, message):
    from_verkey, decrypted_message_json = await crypto.auth_decrypt(wallet_handle, key, message)
    decrypted_message_json = decrypted_message_json.decode("utf-8")
    decrypted_message = json.loads(decrypted_message_json)
    return from_verkey, decrypted_message_json, decrypted_message


async def get_cred_def(pool_handle, _did, cred_def_id):
    get_cred_def_request = await ledger.build_get_cred_def_request(_did, cred_def_id)
    get_cred_def_response = await ledger.submit_request(pool_handle, get_cred_def_request)
    return await ledger.parse_get_cred_def_response(get_cred_def_response)


async def get_credential_for_referent(search_handle, referent):
    credentials = json.loads(
        await anoncreds.prover_fetch_credentials_for_proof_req(search_handle, referent, 10))
    return credentials[0]['cred_info']

async def prover_get_entities_from_ledger(pool_handle, _did, identifiers, actor):
    schemas = {}
    cred_defs = {}
    rev_states = {}
    for item in identifiers.values():
        print("\"{}\" -> Get Schema from Ledger".format(actor))
        (received_schema_id, received_schema) = await get_schema(pool_handle, _did, item['schema_id'])
        schemas[received_schema_id] = json.loads(received_schema)

        print("\"{}\" -> Get Credential Definition from Ledger".format(actor))
        (received_cred_def_id, received_cred_def) = await get_cred_def(pool_handle, _did, item['cred_def_id'])
        cred_defs[received_cred_def_id] = json.loads(received_cred_def)

        if 'rev_reg_seq_no' in item:
            pass  # TODO Create Revocation States

    return json.dumps(schemas), json.dumps(cred_defs), json.dumps(rev_states)

async def get_schema(pool_handle, _did, schema_id):
    get_schema_request = await ledger.build_get_schema_request(_did, schema_id)
    get_schema_response = await ledger.submit_request(pool_handle, get_schema_request)
    return await ledger.parse_get_schema_response(get_schema_response)


async def user():
    # 链上身份初始化
    User_info = await get_verinym.identify_init()

    return User_info


async def get_credentials(User_info):
    # from:alice to:faber
    (User_info['from_to_did'], User_info['from_to_key']) = \
        await did.create_and_store_my_did(User_info['wallet'], "{}")
    # print(from_to_did)
    await send_nym(User_info['pool'], User_info['wallet'], User_info['did'], User_info['from_to_did'], User_info['from_to_key'], None)    
    # 向faber发送该did,faber:8061
    massage = [User_info['from_to_did'], User_info['from_to_key']]
    session_initiation.session_initiation(massage, User_info['name'], 8061)
    
    time.sleep(1)
    massage = session_acceptance.easy_session_acceptance(User_info['name'], 8061)
    
    definition_name = massage[1].decode()
    
    User_info['authcrypted_' + definition_name + '_cred_offer'] = massage[0]
    # User_info['to_from_did'] = 
    User_info['to_from_key'], User_info[definition_name + '_cred_offer'], authdecrypted_credential_cred_offer = \
        await auth_decrypt(User_info['wallet'], User_info['from_to_key'], User_info['authcrypted_' + definition_name + '_cred_offer'])
    # print(authdecrypted_credential_cred_offer)
    User_info[definition_name + '_schema_id'] = authdecrypted_credential_cred_offer['schema_id']
    User_info[definition_name + '_cred_def_id'] = authdecrypted_credential_cred_offer['cred_def_id']
    
    User_info['master_secret_id'] = await anoncreds.prover_create_master_secret(User_info['wallet'], None)
    start_time = time.time()
    (User_info[definition_name + '_cred_def_id'], User_info[definition_name + '_cred_def']) = \
        await get_cred_def(User_info['pool'], User_info['from_to_did'], authdecrypted_credential_cred_offer['cred_def_id'])
    end_time = time.time()
    print('definition_get:',end_time - start_time)
    (User_info[definition_name + '_cred_request'], User_info[definition_name + '_cred_request_metadata']) = \
        await anoncreds.prover_create_credential_req(User_info['wallet'], User_info['from_to_key'],
                                                     User_info[definition_name + '_cred_offer'], User_info[definition_name + '_cred_def'],
                                                     User_info['master_secret_id'])
    User_info['authcrypted_' + definition_name + '_cred_request'] = \
        await crypto.auth_crypt(User_info['wallet'], User_info['from_to_key'], User_info['to_from_key'],
                                User_info[definition_name + '_cred_request'].encode('utf-8'))

    time.sleep(2)
    session_initiation.easy_session_initiation([User_info['authcrypted_' + definition_name + '_cred_request'], User_info['name'].encode()], User_info['name'], 8061)
    # print(User_info)
    time.sleep(1)
    massage = session_acceptance.easy_session_acceptance(User_info['name'], 8061)
    start_time = time.time()
    User_info['authcrypted_'+ definition_name + '_cred'] = massage[0]
    _, User_info[definition_name + '_cred'], _ = \
        await auth_decrypt(User_info['wallet'], User_info['from_to_key'], User_info['authcrypted_'+ definition_name + '_cred'])
    end_time = time.time()
    print('decrypt:',end_time - start_time)
    start_time = time.time()
    await anoncreds.prover_store_credential(User_info['wallet'], None, User_info[definition_name + '_cred_request_metadata'],
                                            User_info[definition_name + '_cred'], User_info[definition_name + '_cred_def'], None)
    end_time = time.time()
    print('cred2:',end_time - start_time)
    print('0dsfsfsdfsdf\n', json.loads(User_info[definition_name + '_cred']))


async def request_proof(User_info):
    request_name_id = input('请输入验证方id:')
    (User_info[request_name_id + 'from_to_did'], User_info[request_name_id + 'from_to_key']) = \
        await did.create_and_store_my_did(User_info['wallet'], "{}")

    massage = [User_info['name'], User_info[request_name_id + 'from_to_did'], User_info[request_name_id + 'from_to_key']]
    session_initiation.session_initiation(massage, User_info['name'], 8061)    

    massage = session_acceptance.session_acceptance(User_info['name'], 8061)
    User_info[request_name_id + 'to_from_did'] = massage[0]
    User_info[request_name_id + 'to_from_key'] = massage[1]

    massage = session_acceptance.easy_session_acceptance(User_info['name'], 8061)
    request_name = massage[1].decode()
    User_info['authcrypted_' + request_name + '_proof_request'] = massage[0]

    User_info[request_name_id + 'to_from_key'], User_info[request_name + '_proof_request'], _ = \
        await auth_decrypt(User_info['wallet'], User_info[request_name_id + 'from_to_key'], User_info['authcrypted_' + request_name + '_proof_request'])
    start_time = time.time()
    search_for_credential_proof_request = \
        await anoncreds.prover_search_credentials_for_proof_req(User_info['wallet'],
                                                                User_info[request_name + '_proof_request'], None)   

    cred_for_attr1 = await get_credential_for_referent(search_for_credential_proof_request, 'attr1_referent')
    cred_for_attr2 = await get_credential_for_referent(search_for_credential_proof_request, 'attr2_referent')
    cred_for_attr3 = await get_credential_for_referent(search_for_credential_proof_request, 'attr3_referent')
    cred_for_attr4 = await get_credential_for_referent(search_for_credential_proof_request, 'attr4_referent')
    cred_for_attr5 = await get_credential_for_referent(search_for_credential_proof_request, 'attr5_referent')
    cred_for_predicate1 = \
        await get_credential_for_referent(search_for_credential_proof_request, 'predicate1_referent')

    print(User_info[request_name + '_proof_request'],'\n', cred_for_attr1, '\n', cred_for_predicate1)

    await anoncreds.prover_close_credentials_search_for_proof_req(search_for_credential_proof_request)

    User_info['creds_for_' + request_name + '_proof'] = {cred_for_attr1['referent']: cred_for_attr1,
                                                cred_for_attr2['referent']: cred_for_attr2,
                                                cred_for_attr3['referent']: cred_for_attr3,
                                                cred_for_attr4['referent']: cred_for_attr4,
                                                cred_for_attr5['referent']: cred_for_attr5,
                                                cred_for_predicate1['referent']: cred_for_predicate1}

    User_info['schemas'], User_info['cred_defs'], User_info['revoc_states'] = \
        await prover_get_entities_from_ledger(User_info['pool'], User_info[request_name_id + 'from_to_did'],
                                             User_info['creds_for_' + request_name + '_proof'], User_info['name'])

    User_info[request_name + '_requested_creds'] = json.dumps({
        'self_attested_attributes': {
            'attr1_referent': 'Alice',
            'attr2_referent': 'Garcia',
            'attr6_referent': '123-45-6789'
        },
        'requested_attributes': {
            'attr3_referent': {'cred_id': cred_for_attr3['referent'], 'revealed': True},
            'attr4_referent': {'cred_id': cred_for_attr4['referent'], 'revealed': True},
            'attr5_referent': {'cred_id': cred_for_attr5['referent'], 'revealed': True},
        },
        'requested_predicates': {'predicate1_referent': {'cred_id': cred_for_predicate1['referent']}}
    })

    #print('safafawefwef\n', json.loads(User_info[request_name + '_requested_creds']))
    User_info[request_name + '_proof'] = \
        await anoncreds.prover_create_proof(User_info['wallet'], User_info[request_name + '_proof_request'],
                                            User_info[request_name + '_requested_creds'], User_info['master_secret_id'],
                                            User_info['schemas'], User_info['cred_defs'], User_info['revoc_states'])
    
    #print('asfawefwafewafwaefawe\n', json.loads(User_info[request_name + '_proof']))
    end_time =time.time()
    print('request:',end_time - start_time)
    User_info['authcrypted_' + request_name + '_proof'] = \
        await crypto.auth_crypt(User_info['wallet'], User_info[request_name_id + 'from_to_key'], User_info[request_name_id + 'to_from_key'],
                                User_info[request_name + '_proof'].encode('utf-8'))

    # time.sleep(2)
    session_initiation.easy_session_initiation([User_info['authcrypted_' + request_name + '_proof']], User_info['name'], 8061)



async def run():
    User_info = await user()
    await get_credentials(User_info)
    await request_proof(User_info)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())
    time.sleep(1)  # FIXME waiting for libindy thread complete


