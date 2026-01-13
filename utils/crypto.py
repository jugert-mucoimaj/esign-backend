import base64
import os
import re
import binascii
from hashlib import pbkdf2_hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key


def generate_encryption_key(password: str, salt: bytes) -> bytes:
    """Generate a stable 256-bit encryption key using PBKDF2."""
    return pbkdf2_hmac("sha256", password.encode(), salt, 100000)


def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return public_pem, private_pem

def derive_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(password.encode())


def encrypt_private_key(private_key: str, password: str, salt: bytes) -> str:
    """Encrypt private key using PBKDF2-derived key."""
    key = generate_encryption_key(password, salt)
    iv = os.urandom(12)

    print(f"Encrypting Private Key: {private_key[:30]}...")  # Print first 30 chars
    print(f"Encryption Key: {key}")

    cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(private_key.encode()) + encryptor.finalize()

    encrypted_data = base64.b64encode(salt + iv + encryptor.tag + ciphertext).decode()
    print(f"Final Encrypted Private Key: {encrypted_data[:60]}...")  # Print snippet

    return encrypted_data



def decrypt_private_key(encrypted_private_key: str, password: str, salt: bytes) -> bytes:
    """Decrypts private key using the same PBKDF2-derived key."""
    encrypted_data = base64.b64decode(encrypted_private_key)
    stored_salt, iv, tag, ciphertext = encrypted_data[:16], encrypted_data[16:28], encrypted_data[28:44], encrypted_data[44:]

    print(f"Stored Salt from Encrypted Data: {stored_salt}")
    print(f"Provided Salt from DB: {salt}")

    if stored_salt != salt:
        raise ValueError("Salt mismatch. Decryption key derivation failed.")

    key = generate_encryption_key(password, stored_salt)

    print(f"Derived Key for Decryption: {key}")
    print(f"Derived Key Length: {len(key)} bytes")
    print(f"Ciphertext Before Decryption: {ciphertext[:30]}...")  # Print snippet

    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
    decryptor = cipher.decryptor()

    try:
        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
        print(f"Decryption Successful: {decrypted_data[:30]}...")  # Print first 30 bytes
        return decrypted_data
    except Exception as e:
        print(f"Decryption failed: {str(e)}")  # Print exact error
        raise




def sign_document(document_bytes, private_key_pem):
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None
        )
        hasher = hashes.Hash(hashes.SHA256())
        hasher.update(document_bytes)
        document_hash = hasher.finalize()
        signature = private_key.sign(
            document_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode("utf-8").strip()
    except Exception as e:
        raise ValueError(f"Signing failed: {str(e)}")



def verify_signature(document_bytes, signature, public_key_pem):
    try:
        # Load Public Key
        public_key = load_pem_public_key(public_key_pem.encode())

        # Decode Signature (Ensure it's Base64 valid)
        try:
            signature_bytes = base64.b64decode(signature.strip(), validate=True)
        except binascii.Error:
            raise ValueError("Invalid Base64 encoding in signature.")

        # Hash the Document
        digest = hashes.Hash(hashes.SHA256())
        digest.update(document_bytes)
        document_hash = digest.finalize()

        # Verify the Signature
        public_key.verify(
            signature_bytes,
            document_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return {"message": "Signature is valid", "verified": True}

    except binascii.Error:
        return {"error": "Base64 decoding failed", "verified": False}
    except ValueError as ve:
        return {"error": str(ve), "verified": False}
    except Exception as e:
        return {"error": f"Signature verification failed: {str(e)}", "verified": False}


def extract_signature(file_content: bytes):
    try:
        content_str = file_content.decode(errors="ignore")

        match = re.search(r"--- SIGNATURE START ---\n(.*?)\n--- SIGNATURE END ---", content_str, re.DOTALL)
        if not match:
            return None, None

        signature_b64 = match.group(1).strip()
        print(f"Extracted Signature (Base64): {repr(signature_b64)}")

        original_content = content_str.replace(match.group(0), "").encode()

        return original_content, signature_b64

    except Exception as e:
        print(f"Signature Extraction Failed: {e}")
        return None, None
