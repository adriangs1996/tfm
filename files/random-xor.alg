def random_func(msg):
    if msg == 1:
        return randint(10, 20)
    return xor(msg & msg ^ -1)