import random
import math
import secrets
from random import randrange

def fastExpMod(b, e, m):  # 底数，幂，大数N
    result = 1
    e = int(e)
    while e != 0:
        if e % 2 != 0:
            e -= 1
            result = (result * b) % m
            continue
        e >>= 1
        b = (b * b) % m
    return result

def is_probably_prime_miller_rabin(n: int, k: int = 10) -> bool:
    if n == 2 or n == 3:
        return True
    if not n & 1:
        return False

    def check(a: int, s: int, d: int, n: int) -> bool:
        x = pow(a, d, n)
        if x == 1:
            return True
        for _ in range(s - 1):
            if x == n - 1:
                return True
            x = pow(x, 2, n)
        return x == n - 1

    s: int = 0
    d: int = n - 1

    while d % 2 == 0:
        d >>= 1
        s += 1

    for _ in range(k):
        a: int = randrange(2, n - 1)
        if not check(a, s, d, n):
            return False

    return True

def get_big_prime(nbits: int = 512) -> int:
    while True:
        p: int = 2 ** (nbits - 1) | secrets.randbits(nbits)
        if p % 2 == 0:
            p = p + 1
        if is_probably_prime_miller_rabin(p):
            return p

def create_keys(keyLength):
    p = get_big_prime(keyLength)
    q = get_big_prime(keyLength)
    n = p * q
    fn = (p - 1) * (q - 1)
    e = selectE(fn)
    d = match_d(e, fn)
    return n, e, d


def selectE(fn):
    while True:
        e = random.randint(0, fn)
        if math.gcd(e, fn) == 1:
            return e


def match_d(e, fn):
    d = 0
    while True:
        if (e * d) % fn == 1:
            return d
        d += 1

def encrypt(M, e, n):
    return fastExpMod(M, e, n)

def decrypt(C, d, m):
    return fastExpMod(C, d, m)


def encrypt_m(in_mess):
    c = ''
    for ch in in_mess:
        s = str(encrypt(ord(ch), e, n))
        c += s
    return c


def decrypt_m(in_cipher):
    p = ''
    for ch in in_cipher:
        c: str = str(decrypt(ord(ch), d, n))
        p += c
    return p