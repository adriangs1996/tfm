require 'digest'

# Generate a random prime number (for simplicity, we use small primes in this example)
def random_prime(bits)
  loop do
    candidate = rand(2**(bits - 1)..2**bits)
    return candidate if prime?(candidate)
  end
end

# Check if a number is prime
def prime?(number)
  return false if number < 2
  (2..Math.sqrt(number).to_i).none? { |i| number % i == 0 }
end

# Compute the greatest common divisor using the Euclidean algorithm
def gcd(a, b)
  while b != 0
    a, b = b, a % b
  end
  a
end

# Compute modular inverse using the Extended Euclidean Algorithm
def mod_inverse(a, m)
  t, new_t = 0, 1
  r, new_r = m, a
  while new_r != 0
    quotient = r / new_r
    t, new_t = new_t, t - quotient * new_t
    r, new_r = new_r, r - quotient * new_r
  end
  if r > 1
    raise 'No modular inverse'
  end
  if t < 0
    t += m
  end
  t
end

# Generate RSA key pair
def generate_keypair(bits)
  p = random_prime(bits / 2)
  q = random_prime(bits / 2)
  n = p * q
  phi = (p - 1) * (q - 1)
  e = 65537 # Commonly used prime number for public exponent
  d = mod_inverse(e, phi)
  {
    public_key: [e, n],
    private_key: [d, n]
  }
end

# Encrypt a message
def encrypt(message, public_key)
  e, n = public_key
  message.bytes.map { |byte| (byte**e % n).chr }.join
end

# Decrypt a message
def decrypt(encrypted_message, private_key)
  d, n = private_key
  encrypted_message.bytes.map { |byte| (byte**d % n).chr }.join
end

# Main script
bits = 64 # Small key size for demonstration

# Generate RSA key pair
keys = generate_keypair(bits)
public_key = keys[:public_key]
private_key = keys[:private_key]

puts "Public Key: #{public_key.inspect}"
puts "Private Key: #{private_key.inspect}"

# Encrypt a message
message = "Hello, RSA!"
encrypted_message = encrypt(message, public_key)
puts "Encrypted Message: #{encrypted_message.bytes.map { |b| b.chr }.join}"

# Decrypt the message
decrypted_message = decrypt(encrypted_message, private_key)
puts "Decrypted Message: #{decrypted_message}"
