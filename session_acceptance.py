# 消息接受方
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

def easy_session_acceptance(my_id, PORT):
    HOST = ''
    BUFSIZ = 32768
    ADDRESS = (HOST, PORT)

    tcpSlaveSocket = socket(AF_INET, SOCK_STREAM)
    #立即释放端口
    tcpSlaveSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
 
    #非阻塞
    # tcpSlaveSocket.setblocking(False)
 
    tcpSlaveSocket.bind(ADDRESS)      # 绑定客户端口和地址

    print('Listening to Initiator...')
    tcpSlaveSocket.listen(5)
    con, ADDR = tcpSlaveSocket.accept()
    print("waiting for message...")

    Data = []
    while True:
        print("waiting for main message...")
        data, addr = con.recvfrom(BUFSIZ) 
        print("接收到数据：", data)
        if data == b'exit':
            con.close()
            break
        Data.append(data)
        content = '[%s]' % (bytes(ctime(), 'utf-8'))
        con.send(content.encode('utf-8'))
        print('...received from and returned to:', addr)
    con.close()
    return Data

def session_acceptance(my_id, PORT):

    HOST = ''
    # PORT = 8060
    BUFSIZ = 1024
    ADDRESS = (HOST, PORT)

    tcpSlaveSocket = socket(AF_INET, SOCK_STREAM)
    #立即释放端口
    tcpSlaveSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
 
    #非阻塞
    #tcpSlaveSocket.setblocking(False)
    tcpSlaveSocket.bind(ADDRESS)      # 绑定客户端口和地址

    # my_id = 'B'
    print('Listening to Initiator...')
    tcpSlaveSocket.listen(5)
    con, ADDR = tcpSlaveSocket.accept()
    print("waiting for message...")

    # 身份交换以及认证
    opp_id, ADDR = con.recvfrom(BUFSIZ)
    print("对方id: ", opp_id.decode())
    con.send(my_id.encode())

    # 曲线参数传递以及类型转换
    params, ADDR = con.recvfrom(BUFSIZ)
    params = params.decode()
    params = Parameters(param_string = params)
    pairing = Pairing(params)
    g_str, ADDR = con.recvfrom(BUFSIZ)
    g_str = g_str.decode()
    g = Element(pairing, G1, value = g_str)
    # print(g, type(g), type(g_str), pairing)


    my_private = Element.random(pairing, Zr) # 生成本方私钥
    my_public = g * my_private  # 生成本方公钥
    my_public_str = str(my_public)

    # ECDH 会话公钥传递
    con.send(my_public_str.encode())
    other_public, ADDR = con.recvfrom(BUFSIZ)
    other_public = Element(pairing, G1, value = other_public.decode())
    
    # 会话密钥计算
    session_key = other_public * my_private
    # print(session_key)
    key = (hashlib.sha256(str(session_key).encode()).digest())[:16]
    key = ''.join(map(lambda x:('' if len(hex(x))>=4 else '0')+hex(x)[2:],key))
    # print(key)

    decryptor2=aesCTR()
    Data = []
    while True:
        print("waiting for main message...")
        data, addr = con.recvfrom(BUFSIZ)
        data = decryptor2.decrypt_message(key,data)        
        # print("CTR解密后",data)
        print("接收到数据：", data.decode('utf-8'))
        if data.decode('utf-8') == 'exit':
            # con.close()
            break
        Data.append(data.decode('utf-8'))
        content = '[%s]' % (bytes(ctime(), 'utf-8'))
        con.send(content.encode('utf-8'))
        print('...received from and returned to:', addr)
    con.close()
    return Data 