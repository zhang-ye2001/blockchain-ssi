import asyncio
import time
from indy import did, ledger, wallet, pool, IndyError, anoncreds, crypto
from indy.error import ErrorCode

import Pool, Wallet, get_verinym, Credentials
import session_acceptance, session_initiation
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


async def get_schema(pool_handle, _did, schema_id):
    get_schema_request = await ledger.build_get_schema_request(_did, schema_id)
    get_schema_response = await ledger.submit_request(pool_handle, get_schema_request)
    return await ledger.parse_get_schema_response(get_schema_response)


async def verifier_get_entities_from_ledger(pool_handle, _did, identifiers, actor):
    schemas = {}
    cred_defs = {}
    rev_reg_defs = {}
    rev_regs = {}
    for item in identifiers:
        print("\"{}\" -> Get Schema from Ledger".format(actor))
        (received_schema_id, received_schema) = await get_schema(pool_handle, _did, item['schema_id'])
        schemas[received_schema_id] = json.loads(received_schema)

        print("\"{}\" -> Get Credential Definition from Ledger".format(actor))
        (received_cred_def_id, received_cred_def) = await get_cred_def(pool_handle, _did, item['cred_def_id'])
        cred_defs[received_cred_def_id] = json.loads(received_cred_def)

        if 'rev_reg_seq_no' in item:
            pass  # TODO Get Revocation Definitions and Revocation Registries

    return json.dumps(schemas), json.dumps(cred_defs), json.dumps(rev_reg_defs), json.dumps(rev_regs)


async def trust_anchor(User_info):
    # 链上身份初始化
    
    # print(User_info)
    start_time = time.time()
    User_info, schema_name = await Credentials.schema_create(User_info)
    schema_time = time.time() - start_time
    start_time = time.time()
    User_info, definition_name = await Credentials.definition_create(User_info, User_info[schema_name + '_schema_id'])
    cred_time_time = time.time() - start_time
    return User_info, definition_name, schema_time, cred_time_time


async def credential_offer(User_info, definition_name):
    # after trust_anchor
    with open("cred_def_list.json", "r") as f:
        cred_def_id = f.read()
    User_info[definition_name + '_cred_def_id'] = json.loads(cred_def_id)
    User_info[definition_name + '_cred_def_id'] = User_info[definition_name + '_cred_def_id'][definition_name]
    User_info[definition_name + '_cred_offer'] = \
        await anoncreds.issuer_create_credential_offer(User_info['wallet'], User_info[definition_name + '_cred_def_id'])
    # 接收alice的did
    print(User_info[definition_name + '_cred_offer'])
    massage = session_acceptance.session_acceptance(User_info['name'], 8061)

    User_info['to_from_did'] = massage[0]
    User_info['to_from_key'] = massage[1]    

    User_info['from_to_did'], User_info['from_to_key'] = \
        await did.create_and_store_my_did(User_info['wallet'], "{}")
    # print(from_to_did)
    await send_nym(User_info['pool'], User_info['wallet'], User_info['did'], User_info['from_to_did'], User_info['from_to_key'], None)    
    User_info['authcrypted_' + definition_name + '_cred_offer'] = \
        await crypto.auth_crypt(User_info['wallet'], User_info['from_to_key'], User_info['to_from_key'],
                                User_info[definition_name +'_cred_offer'].encode('utf-8'))
    massage = [User_info['authcrypted_' + definition_name + '_cred_offer'], definition_name.encode()]
    # print(massage, type(massage[0]))
    time.sleep(1)
    session_initiation.easy_session_initiation(massage, User_info['name'], 8061)
    time.sleep(1)
    massage = session_acceptance.easy_session_acceptance(User_info['name'], 8061)
    User_info['authcrypted_' + definition_name + '_cred_request'] = massage[0]
    to_name = massage[1].decode()

    User_info['to_from_key'], User_info[definition_name + '_cred_request'], _ = \
        await auth_decrypt(User_info['wallet'], User_info['from_to_key'], User_info['authcrypted_' + definition_name + '_cred_request'])

    # 凭证数据输入，此时为一个demo，可以在这里插入遗留数据继承模块
    start_time = time.time()
    User_info[to_name + '_' + definition_name + '_cred_values'] = json.dumps({
        "first_name": {"raw": "Alice", "encoded": "1139481716457488690172217916278103335"},
        "last_name": {"raw": "Garcia", "encoded": "5321642780241790123587902456789123452"},
        "degree": {"raw": "Bachelor of Science, Marketing", "encoded": "12434523576212321"},
        "status": {"raw": "graduated", "encoded": "2213454313412354"},
        "ssn": {"raw": "123-45-6789", "encoded": "3124141231422543541"},
        "year": {"raw": "2015", "encoded": "2015"},
        "average": {"raw": "5", "encoded": "5"}
    })

    User_info[definition_name + '_cred'], _, _ = \
        await anoncreds.issuer_create_credential(User_info['wallet'], User_info[definition_name + '_cred_offer'],
                                                User_info[definition_name + '_cred_request'],
                                                User_info[to_name + '_' + definition_name + '_cred_values'], None, None)
    end_time =time.time()
    print('cred1:',end_time - start_time)
    start_time = time.time()
    User_info['authcrypted_'+ definition_name + '_cred'] = \
        await crypto.auth_crypt(User_info['wallet'], User_info['from_to_key'], User_info['to_from_key'],
                                User_info[definition_name + '_cred'].encode('utf-8'))
    end_time =time.time()
    print('crypt:',end_time - start_time)
    time.sleep(2)
    session_initiation.easy_session_initiation([User_info['authcrypted_'+ definition_name + '_cred']], User_info['name'], 8061)


async def credential_request(User_info, cred_def_id):
    nonce = await anoncreds.generate_nonce()

    request_name = input('请输入构建相关证明的名称：')
    User_info[request_name + '_proof_request'] = json.dumps({
        'nonce': nonce,
        'name': request_name,
        'version': '0.1',
        'requested_attributes': {
            'attr1_referent': {
                'name': 'first_name'
            },
            'attr2_referent': {
                'name': 'last_name'
            },
            'attr3_referent': {
                'name': 'degree',
                'restrictions': [{'cred_def_id': cred_def_id}]
            },
            'attr4_referent': {
                'name': 'status',
                'restrictions': [{'cred_def_id': cred_def_id}]
            },
            'attr5_referent': {
                'name': 'ssn',
                'restrictions': [{'cred_def_id': cred_def_id}]
            },
            'attr6_referent': {
                'name': 'phone_number'
            }
        },
        'requested_predicates': {
            'predicate1_referent': {
                'name': 'average',
                'p_type': '>=',
                'p_value': 4,
                'restrictions': [{'cred_def_id': cred_def_id}]
            }
        }
    })
    #print('AEFWWQFEEWQFEWQEFWQFWFEEW',json.loads(User_info[request_name + '_proof_request']))
    massage = session_acceptance.session_acceptance(User_info['name'], 8061)

    request_name_id = massage[0]
    User_info[request_name_id + 'to_from_did'] = massage[1]
    User_info[request_name_id + 'to_from_key'] = massage[2]    

    User_info[request_name_id + 'from_to_did'], User_info[request_name_id + 'from_to_key'] = \
        await did.create_and_store_my_did(User_info['wallet'], "{}")
    
    time.sleep(2)
    session_initiation.session_initiation([User_info[request_name_id + 'from_to_did'], User_info[request_name_id + 'from_to_key']], User_info['name'], 8061)

    User_info['authcrypted_' + request_name + '_proof_request'] = \
        await crypto.auth_crypt(User_info['wallet'], User_info[request_name_id + 'from_to_key'], User_info[request_name_id + 'to_from_key'],
                                User_info[request_name + '_proof_request'].encode('utf-8'))

    time.sleep(2)
    session_initiation.easy_session_initiation([User_info['authcrypted_' + request_name + '_proof_request'], request_name.encode()], User_info['name'], 8061)

    massage = session_acceptance.easy_session_acceptance(User_info['name'], 8061)
    User_info['authcrypted_' + request_name + '_proof'] = massage[0]
    _, User_info[request_name + '_proof'], decrypted_credential_proof = \
        await auth_decrypt(User_info['wallet'], User_info[request_name_id + 'from_to_key'], User_info['authcrypted_' + request_name + '_proof'])

    start_time = time.time()
    User_info['schemas'], User_info['cred_defs'], User_info['revoc_ref_defs'], User_info['revoc_regs'] = \
        await verifier_get_entities_from_ledger(User_info['pool'], User_info['did'],
                                                decrypted_credential_proof['identifiers'], User_info['name'])

    assert 'Bachelor of Science, Marketing' == \
           decrypted_credential_proof['requested_proof']['revealed_attrs']['attr3_referent']['raw']
    assert 'graduated' == \
           decrypted_credential_proof['requested_proof']['revealed_attrs']['attr4_referent']['raw']
    assert '123-45-6789' == \
           decrypted_credential_proof['requested_proof']['revealed_attrs']['attr5_referent']['raw']

    assert 'Alice' == decrypted_credential_proof['requested_proof']['self_attested_attrs']['attr1_referent']
    assert 'Garcia' == decrypted_credential_proof['requested_proof']['self_attested_attrs']['attr2_referent']
    assert '123-45-6789' == decrypted_credential_proof['requested_proof']['self_attested_attrs']['attr6_referent']

    assert await anoncreds.verifier_verify_proof(User_info[request_name + '_proof_request'], User_info[request_name + '_proof'],
                                                 User_info['schemas'], User_info['cred_defs'], User_info['revoc_ref_defs'],
                                                 User_info['revoc_regs'])
    end_time = time.time()
    print('verify:',end_time - start_time)


async def run():
    '''User_info = await get_verinym.identify_init('TRUST_ANCHOR')
    s_time = []
    d_time = []
    Range = 10
    for i in range(0, Range):
        _,_, schema_time,  cred_def_time = await trust_anchor(User_info)
        s_time.append(schema_time)
        d_time.append(cred_def_time)
    print(s_time, d_time)
    s_avg = 0
    d_avg = 0
    for i in range(0, Range):
        s_avg = s_avg + s_time[i]
        d_avg = d_avg + d_time[i]
    print('schema_time:',s_avg/Range)
    print('cred_def_time:',d_avg/Range)'''
    User_info =  await get_verinym.identify_init('TRUST_ANCHOR')
    User_info, cred_def_name, _,  _ = await trust_anchor(User_info)
    await credential_offer(User_info, cred_def_name)

    c = await get_verinym.identify_init('TRUST_ANCHOR')
    await credential_request(c, User_info[cred_def_name + '_cred_def_id'])

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())
    time.sleep(1)  # FIXME waiting for libindy thread complete


