from enum import Enum
from chromadb.utils import embedding_functions
from ollama import Client, Options
import chromadb


options = Options(
    temperature=0.0
)
client = Client(host="http://localhost:11434")


class OllamaEmbedding(chromadb.EmbeddingFunction):
    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        embeddings = []
        for doc in input:
            response = client.embeddings(
                model="nomic-embed-text",
                prompt=doc,
                options=options
            )
            embedding = response.get("embedding", None)
            if embedding is None:
                raise ValueError("Could not get embedding")
            embeddings.append(embedding)
        return embeddings


class Category(Enum):
    HASHING = "hashing"
    RSA = "RSA"
    DIFFIE_HELLMAN = "DiffieHellman"
    DSA = "DSA"
    ELIPTIC_CURVE = "ElipticCurves"
    ED448 = "ED448"
    ED25519 = "ED25519"
    AES = "AES"
    CAMELLIA = "Camellia"
    CHACHA20 = "ChaCha"
    DES = "DES"
    HMAC = "HMAC"
    MD5 = "MD5"
    SHA = "SHA"
    NOCRYPTO = "NOCRYPTO"
    USES_AES = "USES_AES"
    PASSWORD_PBKDF2_SHA256 = "PASSWORD_PBKDF2_SHA256"
    PASSWORD_BCRYPT = "PASSWORD_BCRYPT"


chroma_client = chromadb.PersistentClient('chroma.db')
collection = chroma_client.get_or_create_collection("CodeSamples", embedding_function=OllamaEmbedding())

if __name__ == '__main__':
    import sys
    import hashlib
    file_path = sys.argv[1]
    category = sys.argv[2]

    with open(file_path) as f:
        code = f.read()
        sha256 = hashlib.sha256(code.encode()).hexdigest()
        collection.upsert(
            ids=[sha256],
            metadatas=[{"category": category}],
            documents=[code]
        )
