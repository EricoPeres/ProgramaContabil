import os
import sqlite3
from datetime import datetime
import pandas as pd

# ============================================
# CONFIGURAÇÃO DE DIRETÓRIOS E BANCOS
# ============================================

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DB = os.path.join(DIRETORIO_BASE, "db")
PASTA_EXCEL = os.path.join(DIRETORIO_BASE, "excel")

# Garantia da existência dos diretórios físicos
os.makedirs(PASTA_DB, exist_ok=True)
os.makedirs(PASTA_EXCEL, exist_ok=True)

# Definição dos caminhos para cada arquivo de banco de dados
BANCO_EMPRESAS = os.path.join(PASTA_DB, "empresas.db")
BANCO_HISTORICO = os.path.join(PASTA_DB, "historico_simples.db")

# Conexão 1: Banco de Cadastro de Empresas
def conectar_empresas():
    return sqlite3.connect(BANCO_EMPRESAS)

# Conexão 2: Banco de Histórico de Apurações
def conectar_historico():
    return sqlite3.connect(BANCO_HISTORICO)

# ============================================
# INICIALIZAÇÃO DO BANCO DE HISTÓRICO
# ============================================

def criar_tabela_historico():
    """Cria o arquivo 'historico_simples.db' e a tabela interna (caso não existam)."""
    try:
        conn = conectar_historico()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_simples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT NOT NULL,
                mes_ano TEXT NOT NULL,
                faturamento REAL NOT NULL,
                rbt12 REAL NOT NULL,
                atividade TEXT NOT NULL,
                aliquota_nominal REAL NOT NULL,
                parcela_deduzir REAL NOT NULL,
                aliquota_efetiva REAL NOT NULL,
                valor_das REAL NOT NULL,
                data_processamento TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Erro ao criar o banco de histórico: {e}")

# ============================================
# CONSULTA DAS EMPRESAS (empresas.db)
# ============================================

def listar_empresas_simples():
    """Busca o cadastro no arquivo 'empresas.db'."""
    try:
        conn = conectar_empresas()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT cnpj, razao_social, regime_tributario, atividade
            FROM empresas
            WHERE regime_tributario = 'Simples Nacional'
        """)

        empresas = cursor.fetchall()
        conn.close()

        if not empresas:
            print("⚠️ Nenhuma empresa cadastrada no Simples Nacional.")
            return []

        print("\n===== EMPRESAS DO SIMPLES NACIONAL =====")
        for e in empresas:
            print(f"CNPJ: {e[0]} | {e[1]} | Atividade: {e[3]}")
        print("========================================\n")

        return empresas
    except sqlite3.Error as e:
        print(f"❌ Erro ao ler 'empresas.db': {e}")
        return []

# ============================================
# TABELAS DO SIMPLES NACIONAL
# ============================================

TABELAS = {
    "Comércio": [
        (180000.00, 0.04, 0.00),
        (360000.00, 0.073, 5940.00),
        (720000.00, 0.095, 13860.00),
        (1800000.00, 0.107, 22500.00),
        (3600000.00, 0.143, 87300.00),
        (4800000.00, 0.19, 378000.00),
    ],
    "Indústria": [
        (180000.00, 0.045, 0.00),
        (360000.00, 0.078, 5940.00),
        (720000.00, 0.10, 13860.00),
        (1800000.00, 0.112, 22500.00),
        (3600000.00, 0.147, 85500.00),
        (4800000.00, 0.30, 720000.00),
    ],
    "Serviços": [
        (180000.00, 0.06, 0.00),
        (360000.00, 0.112, 9360.00),
        (720000.00, 0.135, 17640.00),
        (1800000.00, 0.16, 35640.00),
        (3600000.00, 0.21, 125640.00),
        (4800000.00, 0.33, 648000.00),
    ],
}

# ============================================
# PERSISTÊNCIA (historico_simples.db)
# ============================================

def salvar_historico(
    cnpj,
    mes_ano,
    faturamento,
    rbt12,
    atividade,
    aliq_nominal,
    deducao,
    aliq_efetiva,
    das,
):
    """Grava o registro diretamente no arquivo 'historico_simples.db'."""
    try:
        conn = conectar_historico()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO historico_simples (
                cnpj, mes_ano, faturamento, rbt12, atividade,
                aliquota_nominal, parcela_deduzir, aliquota_efetiva,
                valor_das, data_processamento
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                cnpj,
                mes_ano,
                faturamento,
                rbt12,
                atividade,
                aliq_nominal,
                deducao,
                aliq_efetiva,
                das,
                datetime.now().strftime("%d/%m/%Y %H:%M"),
            ),
        )

        conn.commit()
        conn.close()
        print("💾 Registro salvo no arquivo 'historico_simples.db'!")
    except sqlite3.Error as e:
        print(f"❌ Erro ao gravar no histórico: {e}")

# ============================================
# CONSULTA E EXPORTAÇÃO (historico_simples.db)
# ============================================

def consulta_anual():
    ano = input("Informe o ano para consultar (AAAA): ").strip()

    try:
        conn = conectar_historico()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cnpj, mes_ano, faturamento, rbt12, atividade, aliquota_efetiva, valor_das, data_processamento
            FROM historico_simples
            WHERE substr(mes_ano, 4, 4) = ?
            ORDER BY cnpj, mes_ano
        """,
            (ano,),
        )

        dados = cursor.fetchall()
        conn.close()

        if not dados:
            print(f"⚠️ Nenhum registro encontrado para o ano {ano}.")
            return

        colunas = [
            "CNPJ",
            "Mês/Ano",
            "Faturamento (R$)",
            "RBT12 (R$)",
            "Atividade",
            "Alíq. Efetiva",
            "DAS (R$)",
            "Data Processamento",
        ]

        df = pd.DataFrame(dados, columns=colunas)

        print("\n===== RELATÓRIO ANUAL =====")
        print(df.to_string(index=False))
        print("===========================\n")

        exportar = (
            input("Deseja exportar este relatório para Excel? (s/n): ")
            .strip()
            .lower()
        )
        if exportar == "s":
            nome_arquivo = f"Relatorio_Simples_{ano}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            caminho_excel = os.path.join(PASTA_EXCEL, nome_arquivo)

            df.to_excel(caminho_excel, index=False, engine="openpyxl")
            print(f"✅ Relatório salvo na pasta excel: {caminho_excel}\n")

    except Exception as e:
        print(f"❌ Erro na consulta do histórico: {e}")

# ============================================
# CÁLCULO PRINCIPAL
# ============================================

def calcular_simples():
    empresas = listar_empresas_simples()
    if not empresas:
        return

    cnpj = input("Informe o CNPJ da empresa para cálculo: ").strip()

    try:
        conn = conectar_empresas()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT razao_social, regime_tributario, atividade
            FROM empresas
            WHERE cnpj = ?
        """,
            (cnpj,),
        )

        empresa = cursor.fetchone()
        conn.close()

        if not empresa:
            print("⚠️ Empresa não encontrada em 'empresas.db'.")
            return

        razao, trib, atividade = empresa

        print(f"\n🧾 Empresa selecionada: {razao} | {trib}")

        mes_ano = input("Informe o mês/ano (mm/aaaa): ").strip()
        faturamento = float(
            input("Faturamento bruto do mês (R$): ").replace(",", ".")
        )
        rbt12 = float(
            input("RBT12 (últimos 12 meses) (R$): ").replace(",", ".")
        )

        if atividade not in TABELAS:
            print("⚠️ Tipo de atividade não reconhecido nas tabelas do Simples.")
            return

        tabela = TABELAS[atividade]

        faixa = None
        for limite, aliq, deduz in tabela:
            if rbt12 <= limite:
                faixa = (limite, aliq, deduz)
                break
        if not faixa:
            faixa = tabela[-1]

        limite, aliq_nominal, deducao = faixa

        if rbt12 <= 0:
            aliquota_efetiva = aliq_nominal
        else:
            aliquota_efetiva = ((rbt12 * aliq_nominal) - deducao) / rbt12

        imposto_mensal = faturamento * aliquota_efetiva

        print("\n===== RESULTADO DO CÁLCULO =====")
        print(f"Empresa: {razao}")
        print(f"CNPJ: {cnpj}")
        print(f"Atividade: {atividade}")
        print(f"Alíquota nominal: {aliq_nominal*100:.2f}%")
        print(f"Parcela a deduzir: R$ {deducao:,.2f}")
        print(f"Alíquota efetiva: {aliquota_efetiva*100:.2f}%")
        print(f"DAS a pagar: R$ {imposto_mensal:,.2f}")
        print("================================\n")

        salvar_historico(
            cnpj,
            mes_ano,
            faturamento,
            rbt12,
            atividade,
            aliq_nominal,
            deducao,
            aliquota_efetiva,
            imposto_mensal,
        )

    except ValueError:
        print("❌ Digitação inválida para valores numéricos.")
    except Exception as e:
        print(f"❌ Falha durante o processamento: {e}")

# ============================================
# MENU PRINCIPAL
# ============================================

def menu():
    while True:
        print("""
========= MENU =========
1 - Calcular Simples Nacional
2 - Consultar Relatório Anual (Exibir/Exportar Excel)
0 - Sair
========================
""")

        opc = input("Escolha: ").strip()

        if opc == "1":
            calcular_simples()
        elif opc == "2":
            consulta_anual()
        elif opc == "0":
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    # Cria a estrutura do histórico no arquivo dedicado 'historico_simples.db'
    criar_tabela_historico()
    menu()