class SHA256
  K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
  ]

  H = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
  ]

  def self.right_rotate(value, amount)
    (value >> amount) | (value << (32 - amount)) & 0xFFFFFFFF
  end

  def self.sha256(message)
    message = message.bytes
    bit_length = message.size * 8

    # Padding
    message << 0x80
    while (message.size * 8) % 512 != 448
      message << 0x00
    end

    # Append original length
    message += [bit_length >> 56 & 0xFF, bit_length >> 48 & 0xFF,
                bit_length >> 40 & 0xFF, bit_length >> 32 & 0xFF,
                bit_length >> 24 & 0xFF, bit_length >> 16 & 0xFF,
                bit_length >> 8 & 0xFF, bit_length & 0xFF]

    chunks = message.each_slice(64).to_a
    h = H.dup

    chunks.each do |chunk|
      w = Array.new(64, 0)

      (0..15).each do |i|
        w[i] = (chunk[i * 4] << 24) | (chunk[i * 4 + 1] << 16) |
               (chunk[i * 4 + 2] << 8) | (chunk[i * 4 + 3])
      end

      (16..63).each do |i|
        s0 = right_rotate(w[i - 15], 7) ^ right_rotate(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = right_rotate(w[i - 2], 17) ^ right_rotate(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & 0xFFFFFFFF
      end

      a, b, c, d, e, f, g, hh = h

      (0..63).each do |i|
        s1 = right_rotate(e, 6) ^ right_rotate(e, 11) ^ right_rotate(e, 25)
        ch = (e & f) ^ (~e & g)
        temp1 = (hh + s1 + ch + K[i] + w[i]) & 0xFFFFFFFF
        s0 = right_rotate(a, 2) ^ right_rotate(a, 13) ^ right_rotate(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        temp2 = (s0 + maj) & 0xFFFFFFFF

        hh = g
        g = f
        f = e
        e = (d + temp1) & 0xFFFFFFFF
        d = c
        c = b
        b = a
        a = (temp1 + temp2) & 0xFFFFFFFF
      end

      h[0] = (h[0] + a) & 0xFFFFFFFF
      h[1] = (h[1] + b) & 0xFFFFFFFF
      h[2] = (h[2] + c) & 0xFFFFFFFF
      h[3] = (h[3] + d) & 0xFFFFFFFF
      h[4] = (h[4] + e) & 0xFFFFFFFF
      h[5] = (h[5] + f) & 0xFFFFFFFF
      h[6] = (h[6] + g) & 0xFFFFFFFF
      h[7] = (h[7] + hh) & 0xFFFFFFFF
    end

    h.map { |x| x.to_s(16).rjust(8, '0') }.join
  end
end

# Example usage
message = "hello world"
puts "SHA-256: #{SHA256.sha256(message)}"
