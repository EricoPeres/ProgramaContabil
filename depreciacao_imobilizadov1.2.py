import os
import sqlite3
from datetime import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta

# Define os caminhos apontando para dentro da pasta 'db'
DB_DIR = "db"
DB_EMPRESAS = os.path.join(DB_DIR, "empresas.db")
DB_DEPRECIACOAO = os.path.join(DB_DIR, "depreciacao.db")


# ======================================================
# CONEXÕES COM BANCO DE DADOS
# ======================================================

def criar_tabelas_depreciacao():
    """Garante que a pasta 'db' e as tabelas de depreciação existam."""
    # Cria a pasta 'db' se ela não existir (boa prática caso rode este script primeiro)
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    with sqlite3.connect(DB_DEPRECIACOAO) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS classificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL UNIQUE,
            vida_util_anos INTEGER NOT NULL,
            taxa_depreciacao_anual REAL NOT NULL
        )
        """)

        # Criar classificações padrão se estiver vazio
        cursor.execute("SELECT COUNT(*) FROM classificacoes")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                """
            INSERT INTO classificacoes (descricao, vida_util_anos, taxa_depreciacao_anual)
            VALUES (?, ?, ?)
            """,
                [("Veículos", 5, 20.0), ("Computadores", 5, 20.0), ("Imóveis", 25, 4.0)],
            )
            print(
                "✅ Classificações padrão criadas (Veículos, Computadores, Imóveis)."
            )

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            id_classificacao INTEGER NOT NULL,
            data_aquisicao TEXT NOT NULL,
            valor_aquisicao REAL NOT NULL,
            cnpj_empresa TEXT NOT NULL, 
            FOREIGN KEY (id_classificacao) REFERENCES classificacoes (id)
        )
        """)
        conn.commit()

# ======================================================
# VALIDADCÕES AUXILIARES
# ======================================================

def validar_data_completa(data_str: str) -> bool:
    """Valida formato DD/MM/AAAA."""
    try:
        datetime.strptime(data_str, "%d/%m/%Y")
        return True
    except ValueError:
        return False


def limpar_cnpj(cnpj: str) -> str:
    return "".join(filter(str.isdigit, cnpj))

# ======================================================
# CONSULTA DE EMPRESAS (Conecta no empresas.db)
# ======================================================

def listar_empresas():
    """Carrega as empresas cadastradas utilizando a nova estrutura por CNPJ."""
    try:
        with sqlite3.connect(DB_EMPRESAS) as conn:
            cursor = conn.cursor()
            # Removido o rowid, buscando o CNPJ real como identificador único
            cursor.execute(
                "SELECT cnpj, razao_social, regime_tributario, atividade FROM empresas"
            )
            empresas = cursor.fetchall()
    except sqlite3.OperationalError:
        print("\n⚠️ ERRO: O banco empresas.db não existe ou está corrompido!")
        print("Execute o script de cadastro de empresas primeiro.")
        return []

    if not empresas:
        print("\n⚠️ Nenhuma empresa cadastrada no banco empresas.db.")
        return []

    print("\n===== EMPRESAS CADASTRADAS =====")
    for idx, e in enumerate(empresas, start=1):
        print(
            f"{idx} - {e[1]} | CNPJ: {e[0]} | Regime: {e[2]} | Atividade: {e[3]}"
        )
    print("================================\n")

    return empresas

# ======================================================
# MANUTENÇÃO DE CLASSIFICAÇÕES
# ======================================================

def listar_classificacoes():
    with sqlite3.connect(DB_DEPRECIACOAO) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM classificacoes")
        registros = cursor.fetchall()

    if not registros:
        print("⚠️ Nenhuma classificação cadastrada.")
    else:
        print("\n===== CLASSIFICAÇÕES =====")
        for c in registros:
            print(f"{c[0]} - {c[1]} | Vida útil: {c[2]} anos | Taxa: {c[3]}%")
        print("===========================\n")

def adicionar_classificacao():
    descricao = input("Descrição da classificação: ").strip()
    try:
        vida = int(input("Vida útil (anos): "))
        taxa = float(input("Taxa anual de depreciação (%): ").replace(",", "."))
    except ValueError:
        print("⚠️ Erro: Vida útil e Taxa devem ser valores numéricos.\n")
        return

    try:
        with sqlite3.connect(DB_DEPRECIACOAO) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO classificacoes (descricao, vida_util_anos, taxa_depreciacao_anual) VALUES (?, ?, ?)",
                (descricao, vida, taxa),
            )
            conn.commit()
            print("✅ Classificação adicionada com sucesso!\n")
    except sqlite3.IntegrityError:
        print("⚠️ Já existe uma classificação com esse nome.\n")

def menu_classificacoes():
    while True:
        print(
            "\n==== MENU DE CLASSIFICAÇÕES ====\n1 - Listar Classificações\n2 - Adicionar Classificação\n3 - Voltar\n================================"
        )
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
        return

    # Validação da seleção da empresa pelo CNPJ
    cnpj_escolhido = limpar_cnpj(
        input("Informe o CNPJ da empresa proprietária: ")
    )
    empresa_valida = any(e[0] == cnpj_escolhido for e in empresas)

    if not empresa_valida:
        print("⚠️ CNPJ não corresponde a nenhuma empresa cadastrada.")
        return

    listar_classificacoes()
    try:
        id_class = int(input("Informe o ID da classificação: "))
    except ValueError:
        print("⚠️ ID inválido.")
        return

    with sqlite3.connect(DB_DEPRECIACOAO) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM classificacoes WHERE id = ?", (id_class,))
        if not cursor.fetchone():
            print("⚠️ Classificação inválida.")
            return

    nome = input("Nome do bem: ").strip()

    # Proteção: Impede que datas incorretas entrem no banco de dados
    while True:
        data_aquisicao = input("Data de aquisição (dd/mm/aaaa): ").strip()
        if validar_data_completa(data_aquisicao):
            break
        print("⚠️ Formato de data inválido! Use DD/MM/AAAA.")

    try:
        valor = float(input("Valor de aquisição (R$): ").replace(",", "."))
    except ValueError:
        print("⚠️ Valor de aquisição inválido.")
        return

    with sqlite3.connect(DB_DEPRECIACOAO) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bens (nome, id_classificacao, data_aquisicao, valor_aquisicao, cnpj_empresa)
            VALUES (?, ?, ?, ?, ?)
        """,
            (nome, id_class, data_aquisicao, valor, cnpj_escolhido),
        )
        conn.commit()

    print(f"✅ Bem '{nome}' cadastrado com sucesso!\n")

# ======================================================
# CÁLCULO DA DEPRECIAÇÃO E EXPORTAÇÃO
# ======================================================

def calcular_depreciacao():
    limite_str = input("Informe a data limite (mm/aaaa): ").strip()
    try:
        data_limite = datetime.strptime("01/" + limite_str, "%d/%m/%Y")
    except ValueError:
        print("⚠️ Data inválida! Use mm/aaaa.\n")
        return

    with sqlite3.connect(DB_DEPRECIACOAO) as conn_d:
        cursor_d = conn_d.cursor()
        cursor_d.execute("""
            SELECT b.nome, c.descricao, c.vida_util_anos, c.taxa_depreciacao_anual,
                   b.data_aquisicao, b.valor_aquisicao, b.cnpj_empresa
            FROM bens b
            JOIN classificacoes c ON b.id_classificacao = c.id
        """)
        bens = cursor_d.fetchall()

    if not bens:
        print("⚠️ Nenhum bem cadastrado.\n")
        return

    dados_excel = []

    # Abrindo conexão com o banco de empresas para buscar os metadados
    with sqlite3.connect(DB_EMPRESAS) as conn_e:
        cursor_e = conn_e.cursor()

        for (
            nome,
            classificacao,
            vida,
            taxa_anual,
            data_aq,
            valor,
            cnpj_empresa,
        ) in bens:

            # Busca baseada no CNPJ estável
            cursor_e.execute(
                "SELECT razao_social, regime_tributario, atividade FROM empresas WHERE cnpj = ?",
                (cnpj_empresa,),
            )
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
                    # Ajuste para evitar bugs com o dia 31
                    dia_aq = min(data_aq_dt.day, 30)
                    dias_uso = 30 - dia_aq + 1
                    dep_mes = min(valor_mensal * (dias_uso / 30), valor_atual)
                else:
                    dep_mes = min(valor_mensal, valor_atual)

                valor_atual -= dep_mes
                depreciacoes[mes_ano] = round(dep_mes, 2)

                if valor_atual <= 0:
                    break

            linha = {
                "Empresa": razao_social,
                "CNPJ": cnpj_empresa,
                "Regime Tributário": regime,
                "Atividade": atividade,
                "Bem": nome,
                "Classificação": classificacao,
                "Data de Aquisição": data_aq,
                "Valor de Aquisição (R$)": valor,
                "Valor Residual (R$)": round(max(valor_atual, 0), 2),
            }

            linha.update(depreciacoes)
            dados_excel.append(linha)

    if not dados_excel:
        print("⚠️ Nenhum dado gerado para o relatório.\n")
        return

    df = pd.DataFrame(dados_excel)

    # Reorganização das colunas para colocar os meses sempre no final do Excel
    colunas_fixas = [
        "Empresa",
        "CNPJ",
        "Regime Tributário",
        "Atividade",
        "Bem",
        "Classificação",
        "Data de Aquisição",
        "Valor de Aquisição (R$)",
        "Valor Residual (R$)",
    ]
    colunas_meses = [col for col in df.columns if col not in colunas_fixas]
    df = df[colunas_fixas + colunas_meses]

# --- NOVA ALTERAÇÃO: DIRETÓRIO PARA O EXCEL ---
    XLSX_DIR = "Excel"
    
    # Cria a pasta 'Excel' na raiz do projeto se ela não existir
    if not os.path.exists(XLSX_DIR):
        os.makedirs(XLSX_DIR)

    # Define o nome do arquivo e junta com o caminho da pasta
    nome_base_arquivo = f"relatorio_depreciacao_{limite_str.replace('/', '-')}.xlsx"
    caminho_salvamento = os.path.join(XLSX_DIR, nome_base_arquivo)

    # Salva o arquivo diretamente dentro da pasta /Excel
    df.to_excel(caminho_salvamento, index=False)
    print(f"\n📊 Relatório '{nome_base_arquivo}' gerado com sucesso dentro da pasta /{XLSX_DIR}!\n")    

    # nome_arquivo = f"relatorio_depreciacao_{limite_str.replace('/', '-')}.xlsx"
    # df.to_excel(nome_arquivo, index=False)
    # print(f"\n📊 Relatório '{nome_arquivo}' gerado com sucesso!\n")

# ======================================================
# MENU PRINCIPAL
# ======================================================

def menu():
    criar_tabelas_depreciacao()

    while True:
        print(
            "\n========= MENU DEPRECIACAO =========\n1 - Manter Classificações\n2 - Cadastrar Bem\n3 - Calcular Depreciação e Gerar Relatório\n4 - Sair\n===================================="
        )
        opc = input("Escolha uma opção: ").strip()

        if opc == "1":
            menu_classificacoes()
        elif opc == "2":
            cadastrar_bem()
        elif opc == "3":
            calcular_depreciacao()
        elif opc == "4":
            print("Encerrando o sistema de depreciação. 👋")
            break
        else:
            print("Opção inválida.\n")

if __name__ == "__main__":
    menu()