import time
import sympy

class PrimeAccumulator:
    def __init__(self):
        self.acc = 1

    def get_nonce(self):
        nonce = sympy.randprime(9223372036854775807, 18446744073709551614)
        self.acc  = self.acc * nonce
        return nonce

    def remove(self, nonce):
        if self.acc % nonce == 0:
            self.acc //= nonce

    def check(self, nonce):
        return self.acc % nonce == 0

# 测试代码
acc = PrimeAccumulator()
a = acc.get_nonce()
start_time = time.time()
for i in range(0, 100000):
    acc.get_nonce()
print('get',time.time()- start_time)
with open('acc100000.txt', 'w') as file:
    file.write(str(acc.acc))
start_time = time.time()
print(acc.check(a))
print('check',time.time()- start_time)
start_time = time.time()
acc.remove(a)
print('remove',time.time()- start_time)
with open('acc', 'w') as file:
    file.write(str(acc.acc))
print(acc.check(a))