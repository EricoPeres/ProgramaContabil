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

os.makedirs(PASTA_DB, exist_ok=True)
os.makedirs(PASTA_EXCEL, exist_ok=True)

BANCO_EMPRESAS = os.path.join(PASTA_DB, "empresas.db")
BANCO_LALUR = os.path.join(PASTA_DB, "lalur_lucro_real.db")

def conectar_empresas():
    return sqlite3.connect(BANCO_EMPRESAS)

def conectar_lalur():
    return sqlite3.connect(BANCO_LALUR)

# ============================================
# INICIALIZAÇÃO E CRIAÇÃO DAS TABELAS
# ============================================

def inicializar_banco_lalur():
    """Cria a tabela da Parte A e da Parte B no arquivo lalur_lucro_real.db."""
    try:
        conn = conectar_lalur()
        cursor = conn.cursor()

        # Parte A - Apurações por Trimestre
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lalur_parte_a (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT NOT NULL,
                ano INTEGER NOT NULL,
                trimestre TEXT NOT NULL,
                lucro_liquido REAL NOT NULL,
                adicoes REAL NOT NULL,
                exclusoes REAL NOT NULL,
                lucro_antes_compensacao REAL NOT NULL,
                prejuizo_compensado_irpj REAL NOT NULL,
                base_negativa_compensada_csll REAL NOT NULL,
                lucro_real_final REAL NOT NULL,
                base_csll_final REAL NOT NULL,
                irpj_normal REAL NOT NULL,
                irpj_adicional REAL NOT NULL,
                irpj_total REAL NOT NULL,
                csll_total REAL NOT NULL,
                data_processamento TEXT NOT NULL
            )
        """)

        # Parte B - Saldo e Movimentação do Prejuízo Fiscal / Base Negativa
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lalur_parte_b (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT NOT NULL,
                saldo_prejuizo_irpj REAL NOT NULL,
                saldo_base_negativa_csll REAL NOT NULL,
                data_atualizacao TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Erro ao inicializar o banco LALUR: {e}")

# ============================================
# CONTROLE DA PARTE B (SALDOS)
# ============================================

def obter_saldo_parte_b(cnpj):
    """Retorna os saldos atuais de Prejuízo Fiscal (IRPJ) e Base Negativa (CSLL)."""
    conn = conectar_lalur()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT saldo_prejuizo_irpj, saldo_base_negativa_csll 
        FROM lalur_parte_b 
        WHERE cnpj = ?
    """,
        (cnpj,),
    )

    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        return resultado[0], resultado[1]
    return 0.0, 0.0

def atualizar_saldo_parte_b(
    cnpj, novo_saldo_irpj, novo_saldo_csll, cursor_existente=None
):
    """Atualiza ou insere o saldo da Parte B."""
    cursor_proprio = False
    if cursor_existente is None:
        conn = conectar_lalur()
        cursor = conn.cursor()
        cursor_proprio = True
    else:
        cursor = cursor_existente

    cursor.execute("SELECT id FROM lalur_parte_b WHERE cnpj = ?", (cnpj,))
    existe = cursor.fetchone()

    data_agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    if existe:
        cursor.execute(
            """
            UPDATE lalur_parte_b
            SET saldo_prejuizo_irpj = ?, saldo_base_negativa_csll = ?, data_atualizacao = ?
            WHERE cnpj = ?
        """,
            (novo_saldo_irpj, novo_saldo_csll, data_agora, cnpj),
        )
    else:
        cursor.execute(
            """
            INSERT INTO lalur_parte_b (cnpj, saldo_prejuizo_irpj, saldo_base_negativa_csll, data_atualizacao)
            VALUES (?, ?, ?, ?)
        """,
            (cnpj, novo_saldo_irpj, novo_saldo_csll, data_agora),
        )

    if cursor_proprio:
        conn.commit()
        conn.close()

def menu_gestao_parte_b():
    """Permite informar ou consultar o saldo inicial de prejuízos fiscais."""
    print("\n===== PARTE B - CONTROLE DE PREJUÍZOS FISCAIS / BASE NEGATIVA =====")
    cnpj = input("Informe o CNPJ da empresa: ").strip()

    saldo_irpj, saldo_csll = obter_saldo_parte_b(cnpj)
    print(f"\nSaldo Atual (Parte B) - Prejuízo Fiscal IRPJ: R$ {saldo_irpj:,.2f}")
    print(
        f"Saldo Atual (Parte B) - Base Negativa CSLL:   R$"
        f" {saldo_csll:,.2f}\n"
    )

    alterar = (
        input("Deseja alterar/cadastrar o saldo inicial da Parte B? (s/n): ")
        .strip()
        .lower()
    )
    if alterar == "s":
        try:
            novo_irpj = float(
                input(
                    "Novo saldo de Prejuízo Fiscal acumulado IRPJ (R$): "
                ).replace(",", ".")
            )
            novo_csll = float(
                input(
                    "Novo saldo de Base Negativa acumulada CSLL (R$): "
                ).replace(",", ".")
            )

            atualizar_saldo_parte_b(cnpj, novo_irpj, novo_csll)
            print("✅ Saldo da Parte B atualizado com sucesso!")
        except ValueError:
            print("❌ Valor numérico inválido.")

# ============================================
# CÁLCULO DO LALUR E PROVISÃO DE IMPOSTOS
# ============================================

def listar_empresas_lucro_real():
    """Busca no empresas.db as empresas tributadas pelo Lucro Real."""
    try:
        conn = conectar_empresas()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT cnpj, razao_social, regime_tributario 
            FROM empresas 
            WHERE regime_tributario = 'Lucro Real'
        """)

        empresas = cursor.fetchall()
        conn.close()

        if not empresas:
            print(
                "⚠️ Nenhuma empresa cadastrada no Lucro Real em 'empresas.db'."
            )
            return []

        print("\n===== EMPRESAS (LUCRO REAL) =====")
        for e in empresas:
            print(f"CNPJ: {e[0]} | Razão Social: {e[1]}")
        print("==================================\n")

        return empresas
    except sqlite3.Error as e:
        print(f"❌ Erro ao acessar 'empresas.db': {e}")
        return []

def calcular_lalur():
    empresas = listar_empresas_lucro_real()
    if not empresas:
        return

    cnpj = input("Informe o CNPJ da empresa para o LALUR: ").strip()

    try:
        conn_e = conectar_empresas()
        cursor_e = conn_e.cursor()
        cursor_e.execute(
            "SELECT razao_social FROM empresas WHERE cnpj = ? AND regime_tributario = 'Lucro Real'",
            (cnpj,),
        )
        empresa = cursor_e.fetchone()
        conn_e.close()

        if not empresa:
            print(
                "⚠️ CNPJ não encontrado ou empresa não é do regime Lucro Real."
            )
            return

        razao_social = empresa[0]

        ano = int(input("Informe o Ano (ex: 2026): "))
        trimestre_num = int(input("Informe o Trimestre (1, 2, 3 ou 4): "))

        if trimestre_num not in [1, 2, 3, 4]:
            print("❌ Trimestre inválido.")
            return

        trimestre_str = f"{trimestre_num}º Trimestre"

        print(
            f"\n--- APURAÇÃO LALUR/LACS ({trimestre_str}/{ano}) - {razao_social} ---"
        )
        lucro_liquido = float(
            input("1. Lucro Líquido Contábil antes do IRPJ/CSLL (R$): ").replace(
                ",", "."
            )
        )
        adicoes = float(
            input("2. Total de Adições à base de cálculo (R$): ").replace(
                ",", "."
            )
        )
        exclusoes = float(
            input("3. Total de Exclusões da base de cálculo (R$): ").replace(
                ",", "."
            )
        )

        # PARTE A: Cálculo do Lucro Real Antes das Compensações
        lucro_antes_comp = lucro_liquido + adicoes - exclusoes

        # Obter saldos da Parte B
        saldo_prej_irpj, saldo_base_csll = obter_saldo_parte_b(cnpj)

        comp_irpj = 0.0
        comp_csll = 0.0

        if lucro_antes_comp > 0:
            # Trava dos 30% do Lucro Real/Base CSLL antes da compensação
            limite_compensacao = lucro_antes_comp * 0.30

            # Compensação IRPJ
            comp_irpj = min(saldo_prej_irpj, limite_compensacao)

            # Compensação CSLL
            comp_csll = min(saldo_base_csll, limite_compensacao)

            lucro_real_final = lucro_antes_comp - comp_irpj
            base_csll_final = lucro_antes_comp - comp_csll
        else:
            # Em caso de prejuízo no período
            lucro_real_final = 0.0
            base_csll_final = 0.0

            # O prejuízo gerado no trimestre é ADICIONADO à Parte B
            novo_prej_gerado = abs(lucro_antes_comp)
            saldo_prej_irpj += novo_prej_gerado
            saldo_base_csll += novo_prej_gerado
            print(
                f"\nℹ️ Prejuízo Apurado no Período: R$ {novo_prej_gerado:,.2f}."
                " Adicionado à Parte B."
            )

        # Atualizar saldos Parte B pós-compensação
        if lucro_antes_comp > 0:
            saldo_prej_irpj -= comp_irpj
            saldo_base_csll -= comp_csll

        # PROVISÃO DOS TRIBUTOS
        # IRPJ Normal: 15%
        irpj_normal = lucro_real_final * 0.15

        # Adicional IRPJ: 10% sobre o excedente de R$ 60.000,00 no trimestre
        irpj_adicional = 0.0
        if lucro_real_final > 60000.0:
            irpj_adicional = (lucro_real_final - 60000.0) * 0.10

        irpj_total = irpj_normal + irpj_adicional

        # CSLL Normal: 9%
        csll_total = base_csll_final * 0.09

        # IMPRESSÃO DO DEMONSTRATIVO
        print("\n================ DEMONSTRATIVO LALUR / LACS ================")
        print(f"Empresa: {razao_social} | CNPJ: {cnpj}")
        print(f"Período: {trimestre_str} / {ano}")
        print("-" * 60)
        print(f" Lucro Líquido Contábil:         R$ {lucro_liquido:,.2f}")
        print(f" (+) Adições:                   R$ {adicoes:,.2f}")
        print(f" (-) Exclusões:                 R$ {exclusoes:,.2f}")
        print(f" (=) Lucro Antes das Comp.:     R$ {lucro_antes_comp:,.2f}")
        print("-" * 60)
        print(f" (-) Comp. Prejuízo IRPJ (30%): R$ {comp_irpj:,.2f}")
        print(f" (=) LUCRO REAL FINAL (IRPJ):   R$ {lucro_real_final:,.2f}")
        print("-" * 60)
        print(f" (-) Comp. Base Neg. CSLL (30%): R$ {comp_csll:,.2f}")
        print(f" (=) BASE DE CÁLCULO CSLL:       R$ {base_csll_final:,.2f}")
        print("=" * 60)
        print(f" IRPJ Normal (15%):             R$ {irpj_normal:,.2f}")
        print(f" Adicional IRPJ (10% > 60k):    R$ {irpj_adicional:,.2f}")
        print(f" 📌 TOTAL IRPJ PROVISIONADO:    R$ {irpj_total:,.2f}")
        print(f" 📌 TOTAL CSLL PROVISIONADA:    R$ {csll_total:,.2f}")
        print("=" * 60)
        print(f" Saldo Atualizado Parte B IRPJ: R$ {saldo_prej_irpj:,.2f}")
        print(f" Saldo Atualizado Parte B CSLL: R$ {saldo_base_csll:,.2f}")
        print("============================================================\n")

        # GRAVAÇÃO NO BANCO DE DADOS E ATUALIZAÇÃO DA PARTE B
        conn_l = conectar_lalur()
        cursor_l = conn_l.cursor()

        cursor_l.execute(
            """
            INSERT INTO lalur_parte_a (
                cnpj, ano, trimestre, lucro_liquido, adicoes, exclusoes,
                lucro_antes_compensacao, prejuizo_compensado_irpj, base_negativa_compensada_csll,
                lucro_real_final, base_csll_final, irpj_normal, irpj_adicional,
                irpj_total, csll_total, data_processamento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                cnpj,
                ano,
                trimestre_str,
                lucro_liquido,
                adicoes,
                exclusoes,
                lucro_antes_comp,
                comp_irpj,
                comp_csll,
                lucro_real_final,
                base_csll_final,
                irpj_normal,
                irpj_adicional,
                irpj_total,
                csll_total,
                datetime.now().strftime("%d/%m/%Y %H:%M"),
            ),
        )

        # Atualiza a Parte B na mesma transação
        atualizar_saldo_parte_b(
            cnpj, saldo_prej_irpj, saldo_base_csll, cursor_existente=cursor_l
        )

        conn_l.commit()
        conn_l.close()

        print(
            "💾 Apuração gravada na Parte A e saldos atualizados na Parte B com"
            " sucesso!"
        )

    except ValueError:
        print("❌ Digitação inválida para valores numéricos.")
    except Exception as e:
        print(f"❌ Ocorreu um erro no processamento: {e}")

# ============================================
# CONSULTA E EXPORTAÇÃO EXCEL
# ============================================

def consultar_relatorio_lalur():
    ano = input("Informe o Ano do LALUR para consulta (AAAA): ").strip()

    try:
        conn = conectar_lalur()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cnpj, trimestre, lucro_liquido, adicoes, exclusoes, lucro_real_final, 
                   irpj_total, csll_total, data_processamento
            FROM lalur_parte_a
            WHERE ano = ?
            ORDER BY cnpj, trimestre
        """,
            (ano,),
        )

        dados = cursor.fetchall()
        conn.close()

        if not dados:
            print(f"⚠️ Nenhuma apuração encontrada no LALUR para o ano {ano}.")
            return

        colunas = [
            "CNPJ",
            "Trimestre",
            "Lucro Líquido",
            "Adições",
            "Exclusões",
            "Lucro Real Final",
            "IRPJ Total",
            "CSLL Total",
            "Data Proc.",
        ]

        df = pd.DataFrame(dados, columns=colunas)

        print(f"\n===== RELATÓRIO LALUR / LACS - ANO {ano} =====")
        print(df.to_string(index=False))
        print("=============================================\n")

        exportar = (
            input("Deseja exportar para planilha Excel? (s/n): ")
            .strip()
            .lower()
        )
        if exportar == "s":
            nome_arquivo = f"Relatorio_LALUR_{ano}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            caminho_excel = os.path.join(PASTA_EXCEL, nome_arquivo)

            df.to_excel(caminho_excel, index=False, engine="openpyxl")
            print(f"✅ Arquivo salvo com sucesso em: {caminho_excel}\n")

    except Exception as e:
        print(f"❌ Erro ao gerar o relatório: {e}")

# ============================================
# MENU PRINCIPAL
# ============================================

def menu():
    while True:
        print("""
========= MENU LALUR / LUCRO REAL =========
1 - Apurar LALUR / LACS do Trimestre (Parte A)
2 - Gerenciar Saldo de Prejuízos Fiscais (Parte B)
3 - Consultar e Exportar Relatório Anual
0 - Sair
===========================================
""")

        opc = input("Escolha uma opção: ").strip()

        if opc == "1":
            calcular_lalur()
        elif opc == "2":
            menu_gestao_parte_b()
        elif opc == "3":
            consultar_relatorio_lalur()
        elif opc == "0":
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    inicializar_banco_lalur()
    menu()