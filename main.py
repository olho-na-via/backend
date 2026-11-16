import json
import logging
import os
from datetime import datetime
from getpass import getpass

from pymongo.errors import PyMongoError

from banco import colecao, para_json
from config import PASTA_DO_PROJETO
from erros import ErroDaApi
from regras import CATEGORIAS, pesquisa_binaria
from registro import configurar_logs
from seed import popular_banco
from servicos import acesso, painel
from servicos.chamados import com_prioridade

PASTA_DE_EXPORTACOES = os.path.join(PASTA_DO_PROJETO, "exportacoes")
OPCOES = (
    ("1", "Ver a fila do dia"),
    ("2", "Buscar chamado pelo protocolo"),
    ("3", "Despachar chamado para uma equipe"),
    ("4", "Descartar chamado (falso positivo)"),
    ("5", "Reabrir chamado"),
    ("6", "Resumo por categoria e faixa"),
    ("7", "Exportar chamados para JSON"),
    ("8", "Restaurar dados de demonstração"),
    ("0", "Sair"),
)
NOMES_DAS_FAIXAS = {"critico": "Crítico", "alto": "Alto", "programado": "Programado"}

logger = logging.getLogger(__name__)


def linha(caractere="─", tamanho=72):
    print(caractere * tamanho)


def ler_texto(mensagem, obrigatorio=True):
    while True:
        valor = input(mensagem).strip()
        if valor or not obrigatorio:
            return valor
        print("Este campo é obrigatório.")


def ler_inteiro(mensagem, minimo, maximo):
    while True:
        try:
            valor = int(input(mensagem))
        except ValueError:
            print("Digite um número inteiro.")
            continue
        if minimo <= valor <= maximo:
            return valor
        print(f"Escolha um número de {minimo} a {maximo}.")


def confirmar(mensagem):
    while True:
        resposta = input(f"{mensagem} (s/n) ").strip().lower()
        if resposta in ("s", "n"):
            return resposta == "s"
        print("Responda s ou n.")


def entrar():
    print("Entre com a sua conta de gestor (demonstração: carla@demo.olhonavia.com.br, senha olhonavia).")
    for tentativa in range(3):
        email = ler_texto("E-mail: ")
        senha = getpass("Senha: ")
        try:
            return acesso.entrar({"email": email, "senha": senha, "area": "painel"})
        except ErroDaApi as erro:
            print(erro.mensagem)
            for campo, mensagem in erro.campos.items():
                print(f"  {campo}: {mensagem}")
    return None


def mostrar_fila(gestor):
    dados = painel.fila_do_dia(gestor)
    totais = dados["totais"]
    print(f"\nFila do dia · Subprefeitura do {dados['subprefeitura']}")
    print(
        f"{totais['naFila']} na fila · {totais['porFaixa']['critico']} críticos · "
        f"{totais['vencidos']} vencidos · {totais['criticosVencemHoje']} críticos vencem hoje"
    )
    linha()
    print(f"{'Protocolo':<10}{'IPV':>6}  {'Faixa':<11}{'Prazo':<18}{'Ação':<11}Local")
    linha()
    for chamado in dados["fila"][:15]:
        print(
            f"{chamado['protocolo']:<10}{chamado['ipv']:>6.1f}  {NOMES_DAS_FAIXAS[chamado['faixa']]:<11}"
            f"{chamado['situacaoDoPrazo']:<18}{chamado['acaoSugerida']:<11}{chamado['endereco'][:28]}"
        )
    if len(dados["fila"]) > 15:
        print(f"... e mais {len(dados['fila']) - 15} chamados.")


def buscar_por_protocolo():
    protocolo = ler_inteiro("Protocolo: ", 1, 9_999_999)
    chamados = [
        chamado for chamado in colecao("chamados").find({}, {"protocolo": 1})
        if str(chamado["protocolo"]).isdigit()
    ]
    chamados.sort(key=lambda chamado: int(chamado["protocolo"]))
    posicao = pesquisa_binaria(chamados, protocolo, lambda chamado: int(chamado["protocolo"]))
    if posicao is None:
        print("Não encontramos esse protocolo.")
        return None
    return painel.detalhar_chamado(chamados[posicao]["_id"])


def mostrar_chamado(chamado):
    linha()
    print(f"Chamado #{chamado['protocolo']} · {chamado['titulo']}")
    print(f"{chamado['endereco']} · {chamado['bairro']} · Subprefeitura do {chamado['subprefeitura']}")
    print(f"Status: {chamado['statusParaGestor']} · {chamado['situacaoDoPrazo']}")
    print(f"IPV {chamado['ipv']:.1f} ({NOMES_DAS_FAIXAS[chamado['faixa']]})")
    for chave, valor in chamado["contribuicoes"].items():
        print(f"  {chave.upper()} = {chamado[chave]:<4} contribui {valor:>5.1f}")
    print("Linha do tempo:")
    for evento in chamado["linhaDoTempo"]:
        print(f"  {evento['em'][:16].replace('T', ' ')}  {evento['texto']}")
    linha()


def despachar(gestor):
    chamado = buscar_por_protocolo()
    if chamado is None:
        return
    mostrar_chamado(chamado)
    equipes = chamado["equipesCompativeis"]
    if not equipes:
        print("Nenhuma equipe atende esse órgão. Use o painel para encaminhar o chamado.")
        return
    for numero, equipe in enumerate(equipes, start=1):
        print(f"{numero}. {equipe['nome']}")
    escolha = ler_inteiro("Equipe: ", 1, len(equipes))
    resposta = painel.despachar(gestor, chamado["id"], {"equipeId": equipes[escolha - 1]["id"]})
    print(resposta["aviso"])


def descartar(gestor):
    chamado = buscar_por_protocolo()
    if chamado is None:
        return
    mostrar_chamado(chamado)
    motivo = ler_texto("Motivo do descarte: ")
    if confirmar("Descartar este chamado?"):
        print(painel.descartar(gestor, chamado["id"], {"motivo": motivo})["aviso"])


def reabrir(gestor):
    chamado = buscar_por_protocolo()
    if chamado is None:
        return
    mostrar_chamado(chamado)
    motivo = ler_texto("Por que o chamado volta para a fila? ")
    print(painel.reabrir_pela_gestao(gestor, chamado["id"], {"motivo": motivo})["aviso"])


def resumo_por_categoria_e_faixa(gestor):
    contagem = {}
    for chamado in colecao("chamados").find({"subprefeitura": gestor["subprefeitura"], "status": {"$ne": "descartado"}}):
        faixa = com_prioridade(chamado)["faixa"]
        por_faixa = contagem.setdefault(chamado["categoria"], {"critico": 0, "alto": 0, "programado": 0})
        por_faixa[faixa] += 1

    print(f"\nChamados da Subprefeitura do {gestor['subprefeitura']} por categoria e faixa")
    linha()
    print(f"{'Categoria':<22}{'Crítico':>9}{'Alto':>9}{'Programado':>12}{'Total':>8}")
    linha()
    for categoria, por_faixa in sorted(contagem.items(), key=lambda item: -sum(item[1].values())):
        print(
            f"{CATEGORIAS[categoria]:<22}{por_faixa['critico']:>9}{por_faixa['alto']:>9}"
            f"{por_faixa['programado']:>12}{sum(por_faixa.values()):>8}"
        )


def exportar_chamados(gestor):
    os.makedirs(PASTA_DE_EXPORTACOES, exist_ok=True)
    nome = f"chamados_{datetime.now():%Y%m%d_%H%M%S}.json"
    caminho = os.path.join(PASTA_DE_EXPORTACOES, nome)
    chamados = [com_prioridade(chamado) for chamado in colecao("chamados").find({"subprefeitura": gestor["subprefeitura"]})]
    try:
        with open(caminho, "w", encoding="utf-8") as arquivo:
            json.dump(chamados, arquivo, ensure_ascii=False, indent=2)
    except OSError as erro:
        print(f"Não conseguimos gravar o arquivo: {erro}")
        return
    logger.info("%s exportou %d chamados para %s", gestor["id"], len(chamados), nome)
    print(f"{len(chamados)} chamados exportados para exportacoes/{nome}")


def restaurar_dados():
    if confirmar("Isto apaga os dados atuais e grava os de demonstração. Continuar?"):
        contagem = popular_banco()
        print(f"Dados restaurados: {contagem['chamados']} chamados e {contagem['usuarios']} personas.")
        return True
    return False


def executar(opcao, gestor):
    match opcao:
        case "1":
            mostrar_fila(gestor)
        case "2":
            chamado = buscar_por_protocolo()
            if chamado:
                mostrar_chamado(chamado)
        case "3":
            despachar(gestor)
        case "4":
            descartar(gestor)
        case "5":
            reabrir(gestor)
        case "6":
            resumo_por_categoria_e_faixa(gestor)
        case "7":
            exportar_chamados(gestor)
        case "8":
            restaurar_dados()
        case _:
            print("Opção inválida. Escolha um número do menu.")


def main():
    configurar_logs()
    linha("═")
    print("OLHO NA VIA · Painel do gestor no terminal")
    linha("═")
    try:
        sessao = entrar()
    except PyMongoError:
        print("Não conseguimos falar com o banco de dados. Confira a internet e o MONGODB_URI.")
        return
    if sessao is None:
        print("Não foi possível entrar. Até logo.")
        return
    gestor = sessao["pessoa"]
    gestor["_id"] = gestor["id"]
    print(f"\nOlá, {gestor['nome']} · {gestor['cargo']} · Subprefeitura do {gestor['subprefeitura']}")

    while True:
        print()
        for codigo, descricao in OPCOES:
            print(f"  {codigo}. {descricao}")
        opcao = input("Escolha uma opção: ").strip()
        if opcao == "0":
            acesso.sair(sessao["token"])
            print("Até logo.")
            break
        try:
            executar(opcao, gestor)
        except ErroDaApi as erro:
            print(f"Não foi possível: {erro.mensagem}")
        except PyMongoError:
            logger.exception("Falha no banco durante o menu")
            print("Não conseguimos falar com o banco de dados. Tente de novo.")
        except KeyboardInterrupt:
            print("\nOperação cancelada.")


if __name__ == "__main__":
    main()
