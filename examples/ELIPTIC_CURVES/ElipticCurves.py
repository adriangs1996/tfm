class EllipticCurve:
    def __init__(self, a, b, p):
        self.a = a  # Curve coefficient a
        self.b = b  # Curve coefficient b
        self.p = p  # Finite field prime p

        # Check if the curve is valid (i.e., discriminant is not zero)
        if (4 * a**3 + 27 * b**2) % p == 0:
            raise ValueError("The curve is singular, choose different parameters.")

    def is_on_curve(self, x, y):
        """Check if the point (x, y) is on the curve."""
        return (y**2 - (x**3 + self.a * x + self.b)) % self.p == 0

    def inverse_mod(self, x):
        """Compute the modular inverse of x modulo p."""
        return pow(x, self.p - 2, self.p)

    def point_addition(self, P, Q):
        """Add two points P and Q on the curve."""
        if P == (None, None):
            return Q
        if Q == (None, None):
            return P

        x1, y1 = P
        x2, y2 = Q

        if x1 == x2 and y1 != y2:
            return (None, None)  # The points cancel each other out

        if x1 == x2:
            m = (3 * x1**2 + self.a) * self.inverse_mod(2 * y1) % self.p
        else:
            m = (y2 - y1) * self.inverse_mod(x2 - x1) % self.p

        x3 = (m**2 - x1 - x2) % self.p
        y3 = (m * (x1 - x3) - y1) % self.p

        return (x3, y3)

    def point_doubling(self, P):
        """Double a point P on the curve."""
        return self.point_addition(P, P)

    def scalar_multiplication(self, k, P):
        """Multiply a point P by a scalar k."""
        result = (None, None)  # Neutral element (identity element)
        addend = P

        while k:
            if k & 1:
                result = self.point_addition(result, addend)
            addend = self.point_doubling(addend)
            k >>= 1

        return result

# Example usage
if __name__ == "__main__":
    # Define the curve parameters for y^2 = x^3 + ax + b over F_p
    a = 2
    b = 3
    p = 97  # Prime number

    # Initialize the elliptic curve
    curve = EllipticCurve(a, b, p)

    # Define a point on the curve
    P = (3, 6)

    # Check if the point is on the curve
    if not curve.is_on_curve(P[0], P[1]):
        raise ValueError("The point is not on the curve.")

    # Perform point addition
    Q = curve.point_addition(P, P)
    print(f"2P = {Q}")

    # Perform scalar multiplication (e.g., 10 * P)
    k = 10
    R = curve.scalar_multiplication(k, P)
    print(f"{k}P = {R}")
