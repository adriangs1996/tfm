package main

import (
	"fmt"
	"math/big"
)

// EllipticCurve represents an elliptic curve over a finite field.
type EllipticCurve struct {
	a, b, p *big.Int // Curve coefficients and the prime p defining the finite field
}

// NewEllipticCurve initializes a new elliptic curve.
func NewEllipticCurve(a, b, p *big.Int) *EllipticCurve {
	curve := &EllipticCurve{a: a, b: b, p: p}

	// Check if the curve is singular (i.e., discriminant is zero)
	discriminant := new(big.Int)
	discriminant.Mul(new(big.Int).Mul(big.NewInt(4), new(big.Int).Mul(a, a, a)), big.NewInt(27).Mul(b, b))
	discriminant.Mod(discriminant, p)

	if discriminant.Cmp(big.NewInt(0)) == 0 {
		panic("The curve is singular, choose different parameters.")
	}

	return curve
}

// IsOnCurve checks if the point (x, y) is on the curve.
func (curve *EllipticCurve) IsOnCurve(x, y *big.Int) bool {
	lhs := new(big.Int).Mul(y, y)                    // y^2
	rhs := new(big.Int).Add(new(big.Int).Mul(x, x, x), new(big.Int).Add(new(big.Int).Mul(curve.a, x), curve.b)) // x^3 + ax + b
	lhs.Mod(lhs, curve.p)
	rhs.Mod(rhs, curve.p)

	return lhs.Cmp(rhs) == 0
}

// ModInverse computes the modular inverse of x modulo p.
func ModInverse(x, p *big.Int) *big.Int {
	return new(big.Int).ModInverse(x, p)
}

// PointAddition adds two points P and Q on the curve.
func (curve *EllipticCurve) PointAddition(P, Q [2]*big.Int) [2]*big.Int {
	if P[0] == nil && P[1] == nil {
		return Q
	}
	if Q[0] == nil && Q[1] == nil {
		return P
	}

	x1, y1 := P[0], P[1]
	x2, y2 := Q[0], Q[1]

	if x1.Cmp(x2) == 0 && y1.Cmp(y2) != 0 {
		return [2]*big.Int{nil, nil} // The points cancel each other out (identity element)
	}

	var m *big.Int
	if x1.Cmp(x2) == 0 {
		m = new(big.Int).Mul(big.NewInt(3), new(big.Int).Mul(x1, x1)) // 3 * x1^2 + a
		m.Add(m, curve.a)
		m.Mul(m, ModInverse(new(big.Int).Mul(big.NewInt(2), y1), curve.p)) // / 2 * y1
		m.Mod(m, curve.p)
	} else {
		m = new(big.Int).Sub(y2, y1)
		m.Mul(m, ModInverse(new(big.Int).Sub(x2, x1), curve.p)) // (y2 - y1) / (x2 - x1)
		m.Mod(m, curve.p)
	}

	x3 := new(big.Int).Mul(m, m)
	x3.Sub(x3, x1)
	x3.Sub(x3, x2)
	x3.Mod(x3, curve.p)

	y3 := new(big.Int).Sub(x1, x3)
	y3.Mul(m, y3)
	y3.Sub(y3, y1)
	y3.Mod(y3, curve.p)

	return [2]*big.Int{x3, y3}
}

// PointDoubling doubles a point P on the curve.
func (curve *EllipticCurve) PointDoubling(P [2]*big.Int) [2]*big.Int {
	return curve.PointAddition(P, P)
}

// ScalarMultiplication multiplies a point P by a scalar k.
func (curve *EllipticCurve) ScalarMultiplication(k *big.Int, P [2]*big.Int) [2]*big.Int {
	result := [2]*big.Int{nil, nil} // Identity element
	addend := P

	for k.Sign() > 0 {
		if new(big.Int).And(k, big.NewInt(1)).Cmp(big.NewInt(1)) == 0 {
			result = curve.PointAddition(result, addend)
		}
		addend = curve.PointDoubling(addend)
		k.Rsh(k, 1)
	}

	return result
}

func main() {
	// Define the curve parameters for y^2 = x^3 + ax + b over F_p
	a := big.NewInt(2)
	b := big.NewInt(3)
	p := big.NewInt(97) // Prime number

	// Initialize the elliptic curve
	curve := NewEllipticCurve(a, b, p)

	// Define a point on the curve
	P := [2]*big.Int{big.NewInt(3), big.NewInt(6)}

	// Check if the point is on the curve
	if !curve.IsOnCurve(P[0], P[1]) {
		panic("The point is not on the curve.")
	}

	// Perform point addition
	Q := curve.PointAddition(P, P)
	fmt.Printf("2P = (%s, %s)\n", Q[0].String(), Q[1].String())

	// Perform scalar multiplication (e.g., 10 * P)
	k := big.NewInt(10)
	R := curve.ScalarMultiplication(k, P)
	fmt.Printf("%dP = (%s, %s)\n", k, R[0].String(), R[1].String())
}
