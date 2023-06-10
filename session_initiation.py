# 消息发送方
from Crypto.Util.number import *
import hashlib
from socket import *
from pypbc import *
from time import ctime
from Crypto.Cipher import AES
from binascii import a2b_hex
from Crypto.Util import Counter
import binascii
import os
from time import time, sleep

class aesCTR:
    def int_of_string(self,s):
        return int(binascii.hexlify(s), 16)

    def encrypt_message(self,key, plaintext):
        count= os.urandom(16)
        ctr = Counter.new(128, initial_value=self.int_of_string(count))
        aes = AES.new(a2b_hex(key), AES.MODE_CTR, counter=ctr)
        en = aes.encrypt(plaintext.encode())
        return count + en

    def decrypt_message(self,key, ciphertext):
        count=ciphertext[:16]
        ctr = Counter.new(128, initial_value=self.int_of_string(count))
        aes =AES.new(a2b_hex(key), AES.MODE_CTR, counter=ctr)
        return aes.decrypt(ciphertext[16:])
    

def easy_session_initiation(Data, my_id, PORT):
    HOST = '222.195.70.40'
    BUFSIZ = 32768
    ADDRESS = (HOST, PORT)

    tcpHostSocket = socket(AF_INET, SOCK_STREAM)
    tcpHostSocket.connect(ADDRESS)  

    Data.append(b'exit')
    for data in Data:
        # 发送数据
        tcpHostSocket.send(data)
        # print(data,'\n')
        # 接收数据
        data, ADDR = tcpHostSocket.recvfrom(BUFSIZ)
        if not data:
            tcpHostSocket.close()
            break
        print("从机端响应：", data)

    tcpHostSocket.close()

def session_initiation(Data, my_id, PORT):
    HOST = '222.195.70.40'
    # PORT = 8060
    BUFSIZ = 1024
    ADDRESS = (HOST, PORT)

    tcpHostSocket = socket(AF_INET, SOCK_STREAM)

    # my_id = 'A'
    start_time = time()
    
    # 参数初始化
    params = Parameters(qbits=256, rbits=160)
    pairing = Pairing(params)
    g = Element.random(pairing, G1)

    my_private = Element.random(pairing, Zr) # 生成本方私钥
    my_public = g * my_private  # 生成本方公钥

    # 身份交换以及认证
    tcpHostSocket.connect(ADDRESS)   
    tcpHostSocket.send(my_id.encode())
    # sleep(1)
    opp_id, ADDR = tcpHostSocket.recvfrom(BUFSIZ)
    print("对方id: ", opp_id.decode())

    # 曲线参数传递
    tcpHostSocket.send(str(params).encode())
    # print(g, type(g), type(g_str), pairing)
    tcpHostSocket.send(str(g).encode())

    # ECDH 会话公钥传递
    other_public, ADDR = tcpHostSocket.recvfrom(BUFSIZ)
    other_public = Element(pairing, G1, value = other_public.decode())
    my_public_str = str(my_public)
    tcpHostSocket.send(my_public_str.encode())

    # 会话密钥计算
    session_key = other_public * my_private
    # print(session_key)
    key = (hashlib.sha256(str(session_key).encode()).digest())[:16]
    key = ''.join(map(lambda x:('' if len(hex(x))>=4 else '0')+hex(x)[2:],key))
    # print(key)
    end_time = time()
    print('Time to establish a connection: ', end_time - start_time)

    decryptor2=aesCTR()

    Data.append('exit')
    for data in Data:
        # data = input('>')
        data = decryptor2.encrypt_message(key,data)
        # 发送数据
        tcpHostSocket.send(data)
        # print(data,'\n')
        # 接收数据
        data, ADDR = tcpHostSocket.recvfrom(BUFSIZ)
        if not data:
            tcpHostSocket.close()
            break
        print("从机端响应：", data)

    tcpHostSocket.close()