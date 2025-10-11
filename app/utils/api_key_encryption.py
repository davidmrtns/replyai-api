from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64


MASTER_KEY = os.getenv('MASTER_KEY')
if MASTER_KEY is None:
    raise ValueError('MASTER_KEY environment variable is not set')

MASTER_KEY_BYTES = bytes.fromhex(MASTER_KEY)


def encrypt_api_key(api_key: str) -> str:
    try:
        aesgcm = AESGCM(MASTER_KEY_BYTES)
        iv = os.urandom(12)
        encrypted_key = aesgcm.encrypt(iv, api_key.encode(), None)
        return base64.b64encode(iv + encrypted_key).decode()
    except Exception:
        raise ValueError('Failed to encrypt API key') # TODO: log the exception


def decrypt_api_key(encrypted_api_key: str) -> str:
    try:
        aesgcm = AESGCM(MASTER_KEY_BYTES)
        encrypted_data = base64.b64decode(encrypted_api_key)
        iv = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        decrypted_key = aesgcm.decrypt(iv, ciphertext, None)
        return decrypted_key.decode()
    except Exception:
        raise ValueError('Failed to decrypt API key') # TODO: log the exception
