import asyncio
import time
from indy import did, ledger, wallet, pool, IndyError
from indy.error import ErrorCode

import Pool, Wallet
import session_initiation 
import json


async def identify_init(role = 'None'):


    name = input("Please Input Your Alias:")
    seed = name.zfill(32)
    User_info = {
        'name': name,
        'did_info': json.dumps({'seed': seed}),
        'role': role
    }
    #start_time = time.time()
    Wallet_ = await Wallet.wallet_open()
    
    User_info.update(Wallet_)
    User_info['did'], User_info['key'] = await did.create_and_store_my_did(User_info['wallet'], User_info['did_info'])
    try:
        metadata = await did.get_did_metadata(User_info['wallet'], User_info['did'])
        metadata = json.loads(metadata)
    except:
        print('该did第一次创建')
        metadata = {}
        pass
    
    if 'status' not in metadata:
        metadata['name'] = User_info['name']
        massage = [User_info['did'], User_info['key'], User_info['role']]
        session_initiation.session_initiation(massage, User_info['name'], 8060)
        metadata['status'] = 'main_did'
        await did.set_did_metadata(User_info['wallet'], User_info['did'], json.dumps(metadata))
        print('身份初始化完成！')
    else :
        print('主身份已上链。')


    Pool_ = await Pool.Pool_create()

    User_info['pool'] = Pool_['handle']

    return User_info

async def send_nym(pool_handle, wallet_handle, _did, new_did, new_key, role, dest_name):
    nym_request = await ledger.build_nym_request(_did, new_did, new_key, None, role)
    metadata = {}
    metadata['name'] = dest_name
    metadata['role'] = role
    metadata['submit_by'] = _did
    await did.set_did_metadata(wallet_handle, new_did, json.dumps(metadata))
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, _did, nym_request)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(identify_init('TRUST_ANCHOR'))
    time.sleep(1)  # FIXME waiting for libindy thread complete
