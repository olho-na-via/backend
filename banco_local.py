import copy
import json
import os
import re
from types import SimpleNamespace


def valor_do_campo(documento, caminho):
    for parte in caminho.split("."):
        documento = documento.get(parte) if isinstance(documento, dict) else None
    return documento


def confere_operadores(atual, operadores):
    for operador, argumento in operadores.items():
        match operador:
            case "$in":
                certo = atual in argumento
            case "$ne":
                certo = atual != argumento
            case "$gt":
                certo = atual is not None and atual > argumento
            case "$regex":
                opcoes = re.IGNORECASE if "i" in operadores.get("$options", "") else 0
                certo = re.search(argumento, str(atual or ""), opcoes) is not None
            case "$options":
                certo = True
            case _:
                raise ValueError(f"Operador não suportado no modo local: {operador}")
        if not certo:
            return False
    return True


def confere(documento, filtro):
    for chave, esperado in (filtro or {}).items():
        if chave == "$or":
            if not any(confere(documento, opcao) for opcao in esperado):
                return False
            continue
        atual = valor_do_campo(documento, chave)
        if isinstance(esperado, dict) and any(nome.startswith("$") for nome in esperado):
            if not confere_operadores(atual, esperado):
                return False
        elif isinstance(atual, list) and not isinstance(esperado, list):
            if esperado not in atual:
                return False
        elif atual != esperado:
            return False
    return True


def aplicar_mudancas(documento, mudancas):
    for operador, campos in mudancas.items():
        for caminho, valor in campos.items():
            *pais, ultimo = caminho.split(".")
            alvo = documento
            for parte in pais:
                if not isinstance(alvo.get(parte), dict):
                    alvo[parte] = {}
                alvo = alvo[parte]
            match operador:
                case "$set":
                    alvo[ultimo] = copy.deepcopy(valor)
                case "$inc":
                    alvo[ultimo] = alvo.get(ultimo, 0) + valor
                case "$push":
                    alvo.setdefault(ultimo, []).append(copy.deepcopy(valor))
                case "$addToSet":
                    lista = alvo.setdefault(ultimo, [])
                    if valor not in lista:
                        lista.append(valor)
                case "$pull":
                    alvo[ultimo] = [item for item in alvo.get(ultimo, []) if item != valor]
                case _:
                    raise ValueError(f"Operador não suportado no modo local: {operador}")


def projetar(documento, projecao):
    if not projecao:
        return documento
    if any(valor == 0 for valor in projecao.values()):
        return {chave: valor for chave, valor in documento.items() if projecao.get(chave, 1) != 0}
    return {chave: valor for chave, valor in documento.items() if chave == "_id" or projecao.get(chave)}


class Cursor:
    def __init__(self, documentos):
        self.documentos = documentos

    def sort(self, campo, direcao=1):
        self.documentos.sort(key=lambda documento: str(documento.get(campo) or ""), reverse=direcao == -1)
        return self

    def __iter__(self):
        return iter(self.documentos)


class ColecaoLocal:
    def __init__(self, pasta, nome):
        self.pasta = pasta
        self.caminho = os.path.join(pasta, f"{nome}.json")
        self.documentos = None

    def todos(self):
        # shortcut: lê o arquivo uma vez por processo; menu e API abertos juntos não veem as mudanças um do outro. Use o MongoDB nesse caso.
        if self.documentos is None:
            try:
                with open(self.caminho, encoding="utf-8") as arquivo:
                    self.documentos = json.load(arquivo)
            except FileNotFoundError:
                self.documentos = []
        return self.documentos

    def gravar(self):
        os.makedirs(self.pasta, exist_ok=True)
        temporario = self.caminho + ".tmp"
        with open(temporario, "w", encoding="utf-8") as arquivo:
            json.dump(self.documentos, arquivo, ensure_ascii=False, indent=1)
        os.replace(temporario, self.caminho)

    def encontrados(self, filtro):
        return [documento for documento in self.todos() if confere(documento, filtro)]

    def find(self, filtro=None, projecao=None):
        return Cursor([projetar(copy.deepcopy(documento), projecao) for documento in self.encontrados(filtro)])

    def find_one(self, filtro=None, projecao=None):
        return next(iter(self.find(filtro, projecao)), None)

    def count_documents(self, filtro):
        return len(self.encontrados(filtro))

    def insert_one(self, documento):
        self.todos().append(copy.deepcopy(documento))
        self.gravar()
        return SimpleNamespace(inserted_id=documento["_id"])

    def insert_many(self, documentos):
        self.todos().extend(copy.deepcopy(documentos))
        self.gravar()

    def atualizar(self, filtro, mudancas, limite):
        alterados = self.encontrados(filtro)[:limite]
        for documento in alterados:
            aplicar_mudancas(documento, mudancas)
        if alterados:
            self.gravar()
        return SimpleNamespace(matched_count=len(alterados), modified_count=len(alterados))

    def update_one(self, filtro, mudancas):
        return self.atualizar(filtro, mudancas, 1)

    def update_many(self, filtro, mudancas):
        return self.atualizar(filtro, mudancas, None)

    def remover(self, filtro, limite):
        removidos = self.encontrados(filtro)[:limite]
        self.documentos = [documento for documento in self.todos() if not any(documento is item for item in removidos)]
        if removidos:
            self.gravar()
        return SimpleNamespace(deleted_count=len(removidos))

    def delete_one(self, filtro):
        return self.remover(filtro, 1)

    def delete_many(self, filtro):
        return self.remover(filtro, None)

    def aggregate(self, etapas):
        documentos = self.todos()
        for etapa in etapas:
            if "$match" in etapa:
                documentos = [documento for documento in documentos if confere(documento, etapa["$match"])]
            elif "$group" in etapa:
                documentos = agrupar(documentos, etapa["$group"])
            else:
                raise ValueError(f"Etapa não suportada no modo local: {list(etapa)}")
        return iter(documentos)

    def create_index(self, *argumentos, **opcoes):
        pass

    def drop(self):
        self.documentos = []
        if os.path.exists(self.caminho):
            os.remove(self.caminho)


def valor_da_expressao(documento, expressao):
    if isinstance(expressao, str) and expressao.startswith("$"):
        return valor_do_campo(documento, expressao[1:])
    if isinstance(expressao, dict):
        return {chave: valor_da_expressao(documento, item) for chave, item in expressao.items()}
    return expressao


def agrupar(documentos, grupo):
    grupos = {}
    for documento in documentos:
        chave = valor_da_expressao(documento, grupo["_id"])
        item = grupos.setdefault(json.dumps(chave, sort_keys=True), {"_id": chave})
        for campo, acumulador in grupo.items():
            if campo == "_id":
                continue
            if "$sum" not in acumulador:
                raise ValueError(f"Acumulador não suportado no modo local: {list(acumulador)}")
            item[campo] = item.get(campo, 0) + valor_da_expressao(documento, acumulador["$sum"])
    return list(grupos.values())


class BancoLocal:
    """Guarda cada coleção em um arquivo JSON. Imita só a parte do PyMongo que o projeto usa."""

    def __init__(self, pasta):
        self.pasta = pasta
        self.colecoes = {}

    def __getitem__(self, nome):
        if nome not in self.colecoes:
            self.colecoes[nome] = ColecaoLocal(self.pasta, nome)
        return self.colecoes[nome]

    def __getattr__(self, nome):
        return self[nome]
