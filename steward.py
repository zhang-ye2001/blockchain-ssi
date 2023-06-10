import  asyncio
import time
from indy import anoncreds, crypto, did, ledger, pool, wallet, IndyError
from indy.error import ErrorCode

import json
from typing import Optional

import Pool
import session_acceptance

async def send_nym(pool_handle, wallet_handle, _did, new_did, new_key, role):
    nym_request = await ledger.build_nym_request(_did, new_did, new_key, None, role)
    # 可以在metadata里面补充一些比如以注册成功等信息
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, _did, nym_request)


async def steward():
    steward = {
        'name': "Sovrin Steward",
        'wallet_config': json.dumps({'id': 'sovrin_steward_wallet'}),
        'wallet_credentials': json.dumps({'key': 'steward_wallet_key'}),
        'seed': '000000000000000000000000Steward1'
    } 
    try:
        await wallet.create_wallet(steward['wallet_config'], steward['wallet_credentials'])
    except IndyError as ex:
        if ex.error_code == ErrorCode.WalletAlreadyExistsError:
            pass

    steward['wallet'] = await wallet.open_wallet(steward['wallet_config'], steward['wallet_credentials'])
    steward['did_info'] = json.dumps({'seed': steward['seed']})
    steward['did'], steward['key'] = await did.create_and_store_my_did(steward['wallet'], steward['did_info'])
    # print(type(steward['did']))
    Pool_ = await Pool.Pool_create()
    steward['pool'] = Pool_['handle']
    while True:
        massage = session_acceptance.session_acceptance(steward['name'], 8060)
            # print(massage)
        if massage[2] == 'None':
            massage[2] = None
        await send_nym(steward['pool'], steward['wallet'], steward['did'], massage[0], massage[1], massage[2])

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(steward())
    time.sleep(1) 