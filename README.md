# CompusID

## 介绍

这是一个基于Indy python-SDK的DID注册使用、以及VC颁发和验证的程序，开发环境为Linux。

## 会话密钥协商

**相关函数在session_acceptance.py（接收端）和session_initiation.py(发送端)文件中**

在本项目的实现初步，使用了python 中的pypbc库，该库是一个Linux下基于pbc库实现的双线性库，实现了ECDH密钥交换协议。

相关的通信函数：

```python
# 发送端
def session_initiation(Data, my_id, PORT)
# 接收端
def session_acceptance(my_id, PORT)
``` 

Data是一个由待发送消息组成的列表，my_id用于标识身份，运行时需要先启动接收端进行消息等待。消息加密通过AES的CTR模式实现。

经过后续的indy SDK的使用，发现他自带一个消息加解密函数：

```python
# 加密
await crypto.auth_crypt(alice['wallet'], alice['key_for_faber'], alice['faber_key_for_alice'],
                                massage.encode('utf-8'))
# 解密
async def auth_decrypt(wallet_handle, key, message)
```

相应的，为了适配该函数，写了一个不带加解密的通讯函数：

```python
# 发送端
def easy_session_initiation(Data, my_id, PORT)
# 接收端
def easy_session_acceptance(my_id, PORT)
```

## 账本连接

**相关函数在Pool.py中。**

```python
    pool_name = input("Please Input Pool Name:")
    # pool_txn = input("Please Input the Path of genesis_txn")
    pool_txn = '/home/ustcnet/paper_coding/pool_transactions_genesis'
```

这里为了操作方便，直接将账本连接信息`pool_txn`直接写死在了里面，后续在实现中可以通过拖入等方式实现。

返回是一个字典，最重要的属性值为`Pool['handle']`，用于标识账本。

## 钱包打开

**相关函数在Wallet.py中。**

通过`wallet_id、wallet_key`以用户名密码的方式打开钱包。

可以通过钱包操作函数列出钱包中的`did、credentials`，返回值为一个字符串，如：

```python
did_list = await did.list_my_dids_with_meta(wallet_info)
```

该函数返回是一个字典，最重要的属性值为`Wallet['wallet']`，用于标识钱包。

## DID身份初始化（用户本地端）

**负责打开钱包，连接账本，设置用户main_did，并检查该did是否上链，若是上链则返回，若是没有上链，则加密发送给代理，由其上链，相关函数在get_verinym.py中。**

我们为每个用户的第一个由机构提交的`did`，设置为`main_did`，并写入`metadata`中，之后通过检查该`did`是否有该字段，若是有，则认为以上链。

```python
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
```

## DID身份初始化(代理提交部分)

**为了抵抗女巫攻击，且实现用户身份可审计，用户身份初始化时，需要一个有链上身份的用户。相关函数在steward.py中。**

```python
# DID向链上提交函数
async def send_nym(pool_handle, wallet_handle, _did, new_did, new_key, role, dest_name):
    nym_request = await ledger.build_nym_request(_did, new_did, new_key, None, role)
    # 这里的metadata是一个字典就行，有些文件中的send_nym（）中不涉及metadata内容写入。
    metadata = {}
    metadata['name'] = dest_name
    metadata['role'] = role
    metadata['submit_by'] = _did
    await did.set_did_metadata(wallet_handle, new_did, json.dumps(metadata))
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, _did, nym_request)

```

`steward()`函数单独执行，使用8060端口，只负责接受用户提交的`did`，并上链。用户在拥有一个初始化的链上身份后，即可自己向链上提交`did`.

## Credential Schema、definition创建

**相关函数在Credentials.py中。**

schema提交函数，schema名称、属性自定义（这里为了操作方便，是写死的状态）：

```python
    name =  input('请输出该Credentials Schema名称:')

    '''version = input('请输出该Credentials Schema版本号:')
    attributes = []
    while True:
        massage = input('请输出该Credentials Schema包含的属性,输入EOF表示结束输入:')
        if massage == 'EOF':
            break
        attributes,append(massage)'''
    
    schema_ ={
        'name': name,
        'version': '1.2',
        'attributes': ['first_name', 'last_name', 'degree', 'status', 'year', 'average', 'ssn']
        #'attributes': attributes
    }
```

definition提交时，先从链上获取相关的schema模板，之后签名后并上链：

```python
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
```

这里我计划将所用的schema_id和definition_id写入一个文件中，**之后可以直接通过文件读取获取不用用户提交的信息的id。但是，在实验中，我只涉及一个用户的钱包，和同一个证书的模板和定义。**这可以通过简单的文件读写操作即可。

## 用户端执行

**相关函数在user.py中。**

```python
# 从学校等机构获取凭证
async def get_credentials(User_info)
# 向企业提交学历证明
async def request_proof(User_info)
```

## 机构端执行

**相关函数在trust_anchor.py中，默认机构用户的权限为trust_anchor。**

`trust_anchor(User_info)`函数负责初始化一份Credential Schema和Credential Definition。

```python
    # 初始化机构用户钱包
    User_info =  await get_verinym.identify_init('TRUST_ANCHOR')
    User_info, cred_def_name, _,  _ = await trust_anchor(User_info)
    await credential_offer(User_info, cred_def_name)

    # 验证用户提交的学历证明文件
    c = await get_verinym.identify_init('TRUST_ANCHOR')
    await credential_request(c, User_info[cred_def_name + '_cred_def_id'])
```

## 执行流程

凭证颁发：
！[cred_get](cred_get.png)

凭证检查：

！[cred_check](cred_check.png)