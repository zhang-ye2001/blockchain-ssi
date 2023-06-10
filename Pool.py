import asyncio
import time 
from indy import pool, IndyError
from indy.error import ErrorCode

import json 

async def Pool_create():
    await pool.set_protocol_version(2)
    pool_name = input("Please Input Pool Name:")
    # pool_txn = input("Please Input the Path of genesis_txn")
    pool_txn = '/home/ustcnet/paper_coding/pool_transactions_genesis'
    try:
        await pool.create_pool_ledger_config(pool_name, json.dumps({"genesis_txn": pool_txn}))
    except IndyError as ex:
        if ex.error_code == ErrorCode.PoolLedgerConfigAlreadyExistsError:
            print('{} has been registered!'.format(pool_name))
            pass
        else :
            print('Error happend: {}'.format(ex.error_code))
            exit()
    print("Open Pool Ledger: {}".format(pool_name))
    handle = await pool.open_pool_ledger(pool_name, None)
    Pool = {
        'name': pool_name,
        'config': json.dumps({"genesis_txn": pool_name}),
        'handle': handle
    }
    return Pool