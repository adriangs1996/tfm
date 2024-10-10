 import * as crypto from 'crypto';

// AES key (32 bytes for AES-256)
const key = crypto.randomBytes(32);

// AES IV (16 bytes for AES-CBC mode)
const iv = crypto.randomBytes(16);

// Function to encrypt plaintext
function encrypt(plaintext: string, key: Buffer, iv: Buffer): string {
    // Create a Cipher object using the key and IV
    const cipher = crypto.createCipheriv('aes-256-cbc', key, iv);

    // Encrypt the plaintext
    let encrypted = cipher.update(plaintext, 'utf8', 'hex');
    encrypted += cipher.final('hex');

    return encrypted;
}

// Function to decrypt ciphertext
function decrypt(ciphertext: string, key: Buffer, iv: Buffer): string {
    // Create a Decipher object using the key and IV
    const decipher = crypto.createDecipheriv('aes-256-cbc', key, iv);

    // Decrypt the ciphertext
    let decrypted = decipher.update(ciphertext, 'hex', 'utf8');
    decrypted += decipher.final('utf8');

    return decrypted;
}

// Example usage
const plaintext = "Secret Message! AES encryption in TypeScript";

console.log("Original plaintext:", plaintext);

// Encrypt the plaintext
const ciphertext = encrypt(plaintext, key, iv);
console.log("Ciphertext:", ciphertext);

// Decrypt the ciphertext
const decryptedPlaintext = decrypt(ciphertext, key, iv);
console.log("Decrypted plaintext:", decryptedPlaintext);

