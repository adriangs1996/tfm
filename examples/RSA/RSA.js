class RSA {
    constructor(bitLength = 512) {
        this.bitLength = bitLength;
        const { publicKey, privateKey } = this.generateKeypair(bitLength);
        this.publicKey = publicKey;
        this.privateKey = privateKey;
    }

    generatePrime(bits) {
        const min = BigInt(2) ** BigInt(bits - 1);
        const max = (BigInt(2) ** BigInt(bits)) - BigInt(1);

        while (true) {
            const p = this.randBetween(min, max);
            if (this.isPrime(p)) return p;
        }
    }

    randBetween(min, max) {
        const range = max - min;
        const rand = BigInt(`0x${crypto.getRandomValues(new Uint32Array(4)).map(x => x.toString(16).padStart(8, '0')).join('')}`);
        return min + (rand % (range + BigInt(1)));
    }

    isPrime(n, k = 20) {
        if (n === BigInt(2) || n === BigInt(3)) return true;
        if (n <= BigInt(1) || n % BigInt(2) === BigInt(0)) return false;

        let s = 0n, r = n - BigInt(1);
        while (r % BigInt(2) === BigInt(0)) {
            s++;
            r /= BigInt(2);
        }

        for (let i = 0; i < k; i++) {
            const a = this.randBetween(BigInt(2), n - BigInt(2));
            let x = this.modPow(a, r, n);
            if (x === BigInt(1) || x === n - BigInt(1)) continue;

            let continueLoop = false;
            for (let j = 0; j < s - 1; j++) {
                x = this.modPow(x, BigInt(2), n);
                if (x === n - BigInt(1)) {
                    continueLoop = true;
                    break;
                }
            }

            if (!continueLoop) return false;
        }

        return true;
    }

    modPow(base, exp, mod) {
        let result = BigInt(1);
        base = base % mod;
        while (exp > 0) {
            if (exp % BigInt(2) === BigInt(1)) {
                result = (result * base) % mod;
            }
            exp = exp >> BigInt(1);
            base = (base * base) % mod;
        }
        return result;
    }

    gcd(a, b) {
        while (b !== BigInt(0)) {
            [a, b] = [b, a % b];
        }
        return a;
    }

    modInverse(e, phi) {
        let [old_r, r] = [phi, e];
        let [old_s, s] = [BigInt(0), BigInt(1)];
        let [old_t, t] = [BigInt(1), BigInt(0)];

        while (r !== BigInt(0)) {
            const quotient = old_r / r;
            [old_r, r] = [r, old_r - quotient * r];
            [old_s, s] = [s, old_s - quotient * s];
            [old_t, t] = [t, old_t - quotient * t];
        }

        return old_s < BigInt(0) ? old_s + phi : old_s;
    }

    generateKeypair(bitLength) {
        const p = this.generatePrime(bitLength / 2);
        const q = this.generatePrime(bitLength / 2);
        const n = p * q;
        const phi = (p - BigInt(1)) * (q - BigInt(1));
        const e = BigInt(65537);
        const d = this.modInverse(e, phi);

        return {
            publicKey: { e, n },
            privateKey: { d, n }
        };
    }

    encrypt(plaintext) {
        const m = this.stringToBigInt(plaintext);
        const { e, n } = this.publicKey;
        const c = this.modPow(m, e, n);
        return c.toString();
    }

    decrypt(ciphertext) {
        const c = BigInt(ciphertext);
        const { d, n } = this.privateKey;
        const m = this.modPow(c, d, n);
        return this.bigIntToString(m);
    }

    stringToBigInt(str) {
        const hex = Array.from(str).map(c => c.charCodeAt(0).toString(16).padStart(2, '0')).join('');
        return BigInt(`0x${hex}`);
    }

    bigIntToString(bigInt) {
        const hex = bigInt.toString(16);
        let str = '';
        for (let i = 0; i < hex.length; i += 2) {
            str += String.fromCharCode(parseInt(hex.slice(i, i + 2), 16));
        }
        return str;
    }
}

// Example usage
const rsa = new RSA(512);

console.log('Public Key:', rsa.publicKey);
console.log('Private Key:', rsa.privateKey);

const message = "Hello, RSA!";
const encrypted = rsa.encrypt(message);
console.log('Encrypted:', encrypted);

const decrypted = rsa.decrypt(encrypted);
console.log('Decrypted:', decrypted);
