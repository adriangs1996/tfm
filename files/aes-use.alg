from Crypto.Cipher import AES
import base64


class PrpCrypt(object):

    def __init__(self, key, iv):
        self.key = key
        self.iv = iv
        self.mode = AES.MODE_CBC

    @staticmethod
    def pkcs7_padding(in_bytes: str):
        pad_len: int = 16 - len(in_bytes) % 16
        if pad_len == 0:
            pad_len = 16
        in_str: str = str(in_bytes) + str(hex(pad_len) * pad_len).replace('0x', '')
        return in_str

    @staticmethod
    def pkcs7_unpadding(in_hex_str: str) -> str:
        end_str: str = in_hex_str[-2:]
        if end_str == '01':
            end_str: str = in_hex_str[0:-2]
        else:
            num: int = int(end_str[-2:], 16)
            end_str: str = in_hex_str[0:-(2 * num)]
        return end_str

    def encrypt(self, text: bytes):
        # Encrypt the padded plaintext bytes with the key and IV.
        ciphertext = AES.new(self.key, self.mode, self.iv)
        output_bytes: bytes = ciphertext.encrypt(bytes(text))
        return output_bytes

    def decrypt(self, text: bytes):
        plaintext = AES.new(self.key, self.mode, self.iv)
        output_bytes = plaintext.decrypt(bytes(text))
        return output_bytes