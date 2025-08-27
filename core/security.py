from passlib.context import CryptContext

crypt = CryptContext(schemes=["bcrypt"])


def encrypt_password(password: str):
    password_encoded = password.encode()
    return crypt.hash(password_encoded)
