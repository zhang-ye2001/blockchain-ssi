import asyncio
import time
from indy import did, ledger, wallet, IndyError, anoncreds
from indy.error import ErrorCode
import getpass

import json

async def wallet_open():
    wallet_id = input("Please Input Wallet Name:")
    wallet_key =  getpass.getpass("Please Input Key:")
    wallet_config = json.dumps({'id': wallet_id})
    wallet_credentials = json.dumps({'key': wallet_key})
    try:
        await wallet.create_wallet(wallet_config, wallet_credentials)
        print("Wallet created successfully.")
    except IndyError as ex:
        if ex.error_code == ErrorCode.WalletAlreadyExistsError:
            print("Wallet has aleady been created.")
            pass
        else :
            print('Error happend: {}'.format(ex.error_code))
            exit() 
    wallet_info = await wallet.open_wallet(wallet_config, wallet_credentials)
    # did_list = await did.list_my_dids_with_meta(wallet_info)
    # print(json.loads(did_list))
    Wallet = {
        'wallet_config': wallet_config,
        'wallet_credentials': wallet_credentials,
        'wallet': wallet_info
    }
    return Wallet
