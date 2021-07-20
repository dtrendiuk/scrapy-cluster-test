import base64
from datetime import datetime as dt

import jwt
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes


class Crypt:
    """AES256 Encryption."""

    def __init__(self, secret):
        self.secret = secret

    def encrypt(self, raw):
        BS = AES.block_size
        pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)  # noqa: E731

        raw = base64.b64encode(pad(raw).encode("utf8"))
        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(key=self.secret, mode=AES.MODE_CFB, iv=iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        unpad = lambda s: s[: -ord(s[-1:])]  # noqa: E731

        enc = base64.b64decode(enc)
        iv = enc[: AES.block_size]
        cipher = AES.new(self.secret, AES.MODE_CFB, iv)
        return unpad(base64.b64decode(cipher.decrypt(enc[AES.block_size :])).decode("utf8"))  # noqa: E203


class CryptID:
    def __init__(self, secret):
        self.secret = secret
        self.crypt_obj = Crypt(secret)
        self.expiration = 600  # in secs

    def encryt(self, _id):
        encoded_jwt = jwt.encode({"_id": _id, "exp": dt.utcnow()}, self.secret, algorithm="HS256")
        encryted = self.crypt_obj.encrypt(encoded_jwt)
        return encryted.decode("utf-8")

    def decrypt(self, encryted):
        decryted = self.crypt_obj.decrypt(bytes(encryted, encoding="utf8"))
        decoded = jwt.decode(decryted, self.secret, leeway=self.expiration, algorithms=["HS256"])
        return decoded["_id"]
