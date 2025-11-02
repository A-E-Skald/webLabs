from werkzeug.security import generate_password_hash

# пароль, который хочешь хэшировать
password = "Zalanet_514"

# создаём хэш
hashed = generate_password_hash(password)

print(hashed)
