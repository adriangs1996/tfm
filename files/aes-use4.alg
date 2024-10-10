
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.util.Base64;

public class AESExample {

    public static void main(String[] args) throws Exception {
        // Generate a 256-bit AES key
        KeyGenerator keyGen = KeyGenerator.getInstance("AES");
        keyGen.init(256); // Key size
        SecretKey secretKey = keyGen.generateKey();

        // Generate a 128-bit IV
        byte[] iv = new byte[16];
        SecureRandom random = new SecureRandom();
        random.nextBytes(iv);
        IvParameterSpec ivSpec = new IvParameterSpec(iv);

        // Sample plaintext to encrypt
        String plaintext = "Secret Message! AES encryption in Java";

        System.out.println("Original plaintext: " + plaintext);

        // Encrypt the plaintext
        String ciphertext = encrypt(plaintext, secretKey, ivSpec);
        System.out.println("Ciphertext: " + ciphertext);

        // Decrypt the ciphertext
        String decryptedPlaintext = decrypt(ciphertext, secretKey, ivSpec);
        System.out.println("Decrypted plaintext: " + decryptedPlaintext);
    }

    public static String encrypt(String plaintext, SecretKey key, IvParameterSpec iv) throws Exception {
        // Create a Cipher object for AES in CBC mode with PKCS5 padding
        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");

        // Initialize the cipher for encryption
        cipher.init(Cipher.ENCRYPT_MODE, key, iv);

        // Encrypt the plaintext
        byte[] encrypted = cipher.doFinal(plaintext.getBytes());

        // Return the encrypted bytes as a Base64 encoded string
        return Base64.getEncoder().encodeToString(encrypted);
    }

    public static String decrypt(String ciphertext, SecretKey key, IvParameterSpec iv) throws Exception {
        // Create a Cipher object for AES in CBC mode with PKCS5 padding
        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");

        // Initialize the cipher for decryption
        cipher.init(Cipher.DECRYPT_MODE, key, iv);

        // Decrypt the ciphertext
        byte[] decrypted = cipher.doFinal(Base64.getDecoder().decode(ciphertext));

        // Return the decrypted bytes as a string
        return new String(decrypted);
    }
}
