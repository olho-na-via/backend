import os

# Os testes nunca falam com o Atlas: o endereço aponta para uma porta fechada e o banco é trocado por um falso.
os.environ["MONGODB_URI"] = "mongodb://127.0.0.1:1/"
os.environ["OLHO_MODO_DEMONSTRACAO"] = "1"
