
package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
)

// Function to encrypt plaintext
func encrypt(plaintext string, key []byte, iv []byte) (string, error) {
	// Create a new AES cipher block
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}

	// Ensure that the plaintext length is a multiple of the block size
	padding := aes.BlockSize - len(plaintext)%aes.BlockSize
	paddedPlaintext := append([]byte(plaintext), byte(padding))

	// Create a new CBC mode encrypter
	mode := cipher.NewCBCEncrypter(block, iv)

	// Encrypt the plaintext
	ciphertext := make([]byte, len(paddedPlaintext))
	mode.CryptBlocks(ciphertext, paddedPlaintext)

	// Return the ciphertext as a hex-encoded string
	return hex.EncodeToString(ciphertext), nil
}

// Function to decrypt ciphertext
func decrypt(ciphertextHex string, key []byte, iv []byte) (string, error) {
	// Decode the hex-encoded ciphertext
	ciphertext, err := hex.DecodeString(ciphertextHex)
	if err != nil {
		return "", err
	}

	// Create a new AES cipher block
	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}

	// Create a new CBC mode decrypter
	mode := cipher.NewCBCDecrypter(block, iv)

	// Decrypt the ciphertext
	plaintext := make([]byte, len(ciphertext))
	mode.CryptBlocks(plaintext, ciphertext)

	// Remove padding from the decrypted plaintext
	padding := int(plaintext[len(plaintext)-1])
	unpaddedPlaintext := plaintext[:len(plaintext)-padding]

	// Return the decrypted plaintext as a string
	return string(unpaddedPlaintext), nil
}

func main() {
	// Sample plaintext to encrypt
	plaintext := "Secret Message! AES encryption in Go"

	// Generate a 256-bit key (32 bytes) and a 128-bit IV (16 bytes)
	key := make([]byte, 32)
	iv := make([]byte, 16)
	if _, err := io.ReadFull(rand.Reader, key); err != nil {
		fmt.Println("Error generating random key:", err)
		return
	}
	if _, err := io.ReadFull(rand.Reader, iv); err != nil {
		fmt.Println("Error generating random IV:", err)
		return
	}

	// Encrypt the plaintext
	ciphertext, err := encrypt(plaintext, key, iv)
	if err != nil {
		fmt.Println("Error encrypting:", err)
		return
	}
	fmt.Println("Original plaintext:", plaintext)
	fmt.Println("Ciphertext (hex):", ciphertext)

	// Decrypt the ciphertext
	decryptedPlaintext, err := decrypt(ciphertext, key, iv)
	if err != nil {
		fmt.Println("Error decrypting:", err)
		return
	}
	fmt.Println("Decrypted plaintext:", decryptedPlaintext)
}
