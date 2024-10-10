 from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os

# Generate a random 256-bit (32-byte) key for AES-256
key = os.urandom(32)

# Generate a random 128-bit (16-byte) IV for CBC mode
iv = os.urandom(16)

# Function to encrypt plaintext
def encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    # Create a Cipher object using the key and IV
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

    # Create an encryptor object
    encryptor = cipher.encryptor()

    # Pad the plaintext to be a multiple of the block size (16 bytes)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_plaintext = padder.update(plaintext) + padder.finalize()

    # Encrypt the padded plaintext
    ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

    return ciphertext

# Function to decrypt ciphertext
def decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    # Create a Cipher object using the key and IV
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())

    # Create a decryptor object
    decryptor = cipher.decryptor()

    # Decrypt the ciphertext
    decrypted_padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # Unpad the decrypted plaintext
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    plaintext = unpadder.update(decrypted_padded_plaintext) + unpadder.finalize()

    return plaintext

# Example usage
if __name__ == "__main__":
    # Sample plaintext to encrypt
    plaintext = b"Secret Message! AES encryption in Python"

    print("Original plaintext:", plaintext)

    # Encrypt the plaintext
    ciphertext = encrypt(plaintext, key, iv)
    print("Ciphertext:", ciphertext.hex())

    # Decrypt the ciphertext
    decrypted_plaintext = decrypt(ciphertext, key, iv)
    print("Decrypted plaintext:", decrypted_plaintext)

