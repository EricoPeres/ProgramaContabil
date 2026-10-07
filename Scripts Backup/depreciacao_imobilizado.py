import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd


# ======================================================
# CONEXÕES COM BANCO DE DADOS
# ======================================================

def conectar_empresas():
    return sqlite3.connect("empresas.db")

def conectar_depreciacao():
    return sqlite3.connect("depreciacao.db")


# ======================================================
# CRIAÇÃO DAS TABELAS DE PREÇO (depreciacao.db)
# ======================================================

def criar_tabelas_depreciacao():
    conn = conectar_depreciacao()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS classificacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL UNIQUE,
        vida_util_anos INTEGER NOT NULL,
        taxa_depreciacao_anual REAL NOT NULL
    )
    """)

    # Criar classificações padrão
    cursor.execute("SELECT COUNT(*) FROM classificacoes")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
        INSERT INTO classificacoes (descricao, vida_util_anos, taxa_depreciacao_anual)
        VALUES (?, ?, ?)
        """, [
            ("Veículos", 5, 20.0),
            ("Computadores", 5, 20.0),
            ("Imóveis", 25, 4.0)
        ])
        print("✅ Classificações padrão criadas (Veículos, Computadores, Imóveis).")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        id_classificacao INTEGER NOT NULL,
        data_aquisicao TEXT NOT NULL,
        valor_aquisicao REAL NOT NULL,
        id_empresa INTEGER NOT NULL,
        FOREIGN KEY (id_classificacao) REFERENCES classificacoes (id)
    )
    """)

    conn.commit()
    conn.close()


# ======================================================
# CONSULTA DE EMPRESAS (empresas.db)
# ======================================================

def listar_empresas():
    """Carrega as empresas cadastradas no arquivo empresas.db."""
    conn = conectar_empresas()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT rowid, cnpj, razao_social, regime_tributario, atividade FROM empresas")
        empresas = cursor.fetchall()
    except sqlite3.OperationalError:
        print("⚠️ ERRO: O banco empresas.db não está no formato esperado!")
        print("Use APENAS o script de cadastro de empresas para criá-lo.")
        conn.close()
        return []

    conn.close()

    if not empresas:
        print("\n⚠️ Nenhuma empresa cadastrada no banco empresas.db.")
        return []

    print("\n===== EMPRESAS CADASTRADAS =====")
    for e in empresas:
        print(f"{e[0]} - {e[2]} | CNPJ: {e[1]} | Regime: {e[3]} | Atividade: {e[4]}")
    print("================================\n")

    return empresas


# ======================================================
# MANUTENÇÃO DE CLASSIFICAÇÕES
# ======================================================

def listar_classificacoes():
    conn = conectar_depreciacao()
    cursor = conn.cursor()
    cursor.execute("SELECT id, descricao, vida_util_anos, taxa_depreciacao_anual FROM classificacoes")
    registros = cursor.fetchall()
    conn.close()

    if not registros:
        print("⚠️ Nenhuma classificação cadastrada.")
    else:
        print("\n===== CLASSIFICAÇÕES =====")
        for c in registros:
            print(f"{c[0]} - {c[1]} | Vida útil: {c[2]} anos | Taxa: {c[3]}%")
        print("===========================\n")


def adicionar_classificacao():
    descricao = input("Descrição da classificação: ").strip()
    vida = int(input("Vida útil (anos): "))
    taxa = float(input("Taxa anual de depreciação (%): ").replace(",", "."))

    conn = conectar_depreciacao()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO classificacoes (descricao, vida_util_anos, taxa_depreciacao_anual) VALUES (?, ?, ?)",
                       (descricao, vida, taxa))
        conn.commit()
        print("✅ Classificação adicionada com sucesso!\n")
    except sqlite3.IntegrityError:
        print("⚠️ Já existe uma classificação com esse nome.\n")
    conn.close()


def menu_classificacoes():
    while True:
        print("""
==== MENU DE CLASSIFICAÇÕES ====
1 - Listar Classificações
2 - Adicionar Classificação
3 - Voltar
================================
""")
        opc = input("Escolha: ").strip()
        if opc == "1":
            listar_classificacoes()
        elif opc == "2":
            adicionar_classificacao()
        elif opc == "3":
            break
        else:
            print("Opção inválida.\n")


# ======================================================
# CADASTRO DE BENS
# ======================================================

def cadastrar_bem():
    empresas = listar_empresas()
    if not empresas:
        print("⚠️ Cadastre empresas usando o script adequado.\n")
        return

    id_empresa = int(input("Informe o ID da empresa proprietária: "))

    listar_classificacoes()
    id_class = int(input("Informe o ID da classificação: "))

    conn = conectar_depreciacao()
    cursor = conn.cursor()

    cursor.execute("SELECT descricao, vida_util_anos, taxa_depreciacao_anual FROM classificacoes WHERE id = ?", (id_class,))
    classif = cursor.fetchone()
    if not classif:
        print("⚠️ Classificação inválida.")
        conn.close()
        return

    nome = input("Nome do bem: ").strip()
    data_aquisicao = input("Data de aquisição (dd/mm/aaaa): ").strip()
    valor = float(input("Valor de aquisição (R$): ").replace(",", "."))

    cursor.execute("""
        INSERT INTO bens (nome, id_classificacao, data_aquisicao, valor_aquisicao, id_empresa)
        VALUES (?, ?, ?, ?, ?)
    """, (nome, id_class, data_aquisicao, valor, id_empresa))

    conn.commit()
    conn.close()

    print(f"✅ Bem '{nome}' cadastrado com sucesso!\n")


# ======================================================
# CÁLCULO DA DEPRECIAÇÃO
# ======================================================

def calcular_depreciacao():
    limite_str = input("Informe a data limite (mm/aaaa): ").strip()
    try:
        data_limite = datetime.strptime("01/" + limite_str, "%d/%m/%Y")
    except ValueError:
        print("⚠️ Data inválida! Use mm/aaaa.\n")
        return

    conn_d = conectar_depreciacao()
    cursor_d = conn_d.cursor()

    conn_e = conectar_empresas()
    cursor_e = conn_e.cursor()

    cursor_d.execute("""
        SELECT b.nome, c.descricao, c.vida_util_anos, c.taxa_depreciacao_anual,
               b.data_aquisicao, b.valor_aquisicao, b.id_empresa
        FROM bens b
        JOIN classificacoes c ON b.id_classificacao = c.id
    """)

    bens = cursor_d.fetchall()
    if not bens:
        print("⚠️ Nenhum bem cadastrado.\n")
        return

    dados_excel = []

    for (nome, classificacao, vida, taxa_anual, data_aq, valor, id_empresa) in bens:

        cursor_e.execute("SELECT razao_social, regime_tributario, atividade FROM empresas WHERE rowid = ?", (id_empresa,))
        empresa = cursor_e.fetchone()
        if not empresa:
            continue

        razao_social, regime, atividade = empresa

        data_aq_dt = datetime.strptime(data_aq, "%d/%m/%Y")

        taxa_mensal = taxa_anual / 12
        valor_mensal = valor * (taxa_mensal / 100)
        meses_total = vida * 12

        depreciacoes = {}
        valor_atual = valor

        for m in range(meses_total):
            data_mes = data_aq_dt + relativedelta(months=m)
            if data_mes > data_limite:
                break

            mes_ano = data_mes.strftime("%m/%Y")

            if m == 0:
                dias_uso = 30 - data_aq_dt.day + 1
                dep_mes = min(valor_mensal * (dias_uso / 30), valor_atual)
            else:
                dep_mes = min(valor_mensal, valor_atual)

            valor_atual -= dep_mes
            depreciacoes[mes_ano] = dep_mes

        linha = {
            "Empresa": razao_social,
            "Regime Tributário": regime,
            "Atividade": atividade,
            "Bem": nome,
            "Classificação": classificacao,
            "Data de Aquisição": data_aq,
            "Valor de Aquisição (R$)": valor,
        }

        linha.update(depreciacoes)
        dados_excel.append(linha)

    df = pd.DataFrame(dados_excel)
    nome_arquivo = f"relatorio_depreciacao_{limite_str.replace('/', '-')}.xlsx"
    df.to_excel(nome_arquivo, index=False)
    print(f"\n📊 Relatório '{nome_arquivo}' gerado com sucesso!\n")

    conn_d.close()
    conn_e.close()


# ======================================================
# MENU PRINCIPAL
# ======================================================

def menu():
    criar_tabelas_depreciacao()

    while True:
        print("""
========= MENU DEPRECIACAO =========
1 - Manter Classificações
2 - Cadastrar Bem
3 - Calcular Depreciação e Gerar Relatório
4 - Sair
====================================
""")
        opc = input("Escolha uma opção: ").strip()

        if opc == "1":
            menu_classificacoes()
        elif opc == "2":
            cadastrar_bem()
        elif opc == "3":
            calcular_depreciacao()
        elif opc == "4":
            print("Encerrando o sistema. 👋")
            break
        else:
            print("Opção inválida.\n")


if __name__ == "__main__":
    menu()