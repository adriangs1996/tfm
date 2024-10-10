class EllipticCurve
  attr_reader :a, :b, :p

  def initialize(a, b, p)
    @a = a  # Curve coefficient a
    @b = b  # Curve coefficient b
    @p = p  # Finite field prime p

    # Check if the curve is valid (i.e., discriminant is not zero)
    if (4 * a**3 + 27 * b**2) % p == 0
      raise "The curve is singular, choose different parameters."
    end
  end

  def on_curve?(x, y)
    # Check if the point (x, y) is on the curve.
    (y**2 - (x**3 + @a * x + @b)) % @p == 0
  end

  def inverse_mod(x)
    # Compute the modular inverse of x modulo p using the extended Euclidean algorithm.
    x = x % @p
    y, m, n = @p, 0, 1
    while x > 0
      t = y / x
      y, x = x, y % x
      m, n = n, m - t * n
    end
    raise "Modular inverse does not exist" if y != 1
    m % @p
  end

  def point_addition(p1, p2)
    # Add two points p1 and p2 on the curve.
    return p2 if p1.nil? || p1 == [nil, nil]
    return p1 if p2.nil? || p2 == [nil, nil]

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 && y1 != y2
      return [nil, nil]  # The points cancel each other out (result is the identity element)
    end

    if x1 == x2
      m = (3 * x1**2 + @a) * inverse_mod(2 * y1) % @p
    else
      m = (y2 - y1) * inverse_mod(x2 - x1) % @p
    end

    x3 = (m**2 - x1 - x2) % @p
    y3 = (m * (x1 - x3) - y1) % @p

    [x3, y3]
  end

  def point_doubling(p)
    # Double a point p on the curve.
    point_addition(p, p)
  end

  def scalar_multiplication(k, p)
    # Multiply a point p by a scalar k.
    result = [nil, nil]  # Identity element
    addend = p

    while k > 0
      result = point_addition(result, addend) if k.odd?
      addend = point_doubling(addend)
      k >>= 1
    end

    result
  end
end

# Example usage
if __FILE__ == $PROGRAM_NAME
  # Define the curve parameters for y^2 = x^3 + ax + b over F_p
  a = 2
  b = 3
  p = 97  # Prime number

  # Initialize the elliptic curve
  curve = EllipticCurve.new(a, b, p)

  # Define a point on the curve
  P = [3, 6]

  # Check if the point is on the curve
  raise "The point is not on the curve." unless curve.on_curve?(P[0], P[1])

  # Perform point addition
  Q = curve.point_addition(P, P)
  puts "2P = #{Q}"

  # Perform scalar multiplication (e.g., 10 * P)
  k = 10
  R = curve.scalar_multiplication(k, P)
  puts "#{k}P = #{R}"
end
