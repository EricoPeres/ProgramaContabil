import os
import sqlite3
from datetime import datetime

DB_NAME = "empresas.db"

# =====================================================================
# FUNÇÕES DE BANCO DE DADOS E INFRAESTRUTURA
# =====================================================================

def inicializar_banco():
    """Garante que o banco e a tabela existam com a estrutura correta."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Criando a tabela atualizada com os novos campos solicitados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                cnpj TEXT PRIMARY KEY,
                razao_social TEXT NOT NULL,
                regime_tributario TEXT NOT NULL,
                atividade TEXT NOT NULL,
                data_inicio TEXT NOT NULL,
                inscricao_estadual TEXT,
                inscricao_municipal TEXT,
                endereco TEXT NOT NULL,
                cidade TEXT NOT NULL,
                uf TEXT NOT NULL,
                cep TEXT NOT NULL
            )
        """)
        conn.commit()

def limpar_cnpj(cnpj: str) -> str:
    """Remove caracteres especiais de CNPJ ou CEP."""
    return "".join(filter(str.isdigit, cnpj))

def validar_data(data_str: str) -> bool:
    """Valida se a data digitada está no formato DD/MM/AAAA."""
    try:
        datetime.strptime(data_str, "%d/%m/%Y")
        return True
    except ValueError:
        return False

# =====================================================================
# MENUS DE SELEÇÃO AUXILIARES
# =====================================================================

def escolher_regime():
    print("\nSelecione o regime tributário:")
    print("1 - Simples Nacional\n2 - Lucro Presumido\n3 - Lucro Real")
    opcoes = {"1": "Simples Nacional", "2": "Lucro Presumido", "3": "Lucro Real"}
    while True:
        op = input("Opção: ").strip()
        if op in opcoes:
            return opcoes[op]
        print("Opção inválida, tente novamente.")

def escolher_atividade():
    print("\nSelecione a atividade principal:")
    print("1 - Comércio\n2 - Indústria\n3 - Serviços")
    opcoes = {"1": "Comércio", "2": "Indústria", "3": "Serviços"}
    while True:
        op = input("Opção: ").strip()
        if op in opcoes:
            return opcoes[op]
        print("Opção inválida, tente novamente.")

# =====================================================================
# FLUXOS PRINCIPAIS DE TELA (INTERFACE CLI)
# =====================================================================

def cadastrar_empresa():
    print("\n=== CADASTRAR NOVA EMPRESA ===")
    cnpj = input("CNPJ: ").strip()
    razao = input("Razão Social: ").strip()

    # Novas Validações e Inputs Solicitados
    while True:
        data_inicio = (
            input("Data de Início das Atividades (DD/MM/AAAA): ").strip()
        )
        if validar_data(data_inicio):
            break
        print("Formato de data inválido! Use o formato DD/MM/AAAA.")

    ie = input("Inscrição Estadual (Apenas números ou 'Isento'): ").strip()
    im = input("Inscrição Municipal (Apenas números): ").strip()

    print("\n--- Dados de Endereço ---")
    endereco = input("Logradouro, Nº, Bairro: ").strip()
    cidade = input("Cidade: ").strip()
    uf = input("UF (Estado - ex: SP): ").strip().upper()
    cep = limpar_cnpj(input("CEP: ").strip())

    regime = escolher_regime()
    atividade = escolher_atividade()

    cnpj_padronizado = limpar_cnpj(cnpj)

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO empresas (
                    cnpj, razao_social, regime_tributario, atividade, 
                    data_inicio, inscricao_estadual, inscricao_municipal, 
                    endereco, cidade, uf, cep
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    cnpj_padronizado,
                    razao,
                    regime,
                    atividade,
                    data_inicio,
                    ie,
                    im,
                    endereco,
                    cidade,
                    uf,
                    cep,
                ),
            )
            print("\nEmpresa cadastrada com sucesso!")
    except sqlite3.IntegrityError:
        print("\nERRO: Já existe uma empresa cadastrada com este CNPJ.")

def listar_empresas():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cnpj, razao_social, cidade, uf FROM empresas")
        empresas = cursor.fetchall()

    if not empresas:
        print("\nNenhuma empresa cadastrada.")
    else:
        print("\n=== EMPRESAS CADASTRADAS ===")
        for cnpj, razao, cidade, uf in empresas:
            print(f"CNPJ: {cnpj} | Razão Social: {razao} | Localidade: {cidade}-{uf}")

def consultar_e_editar_empresa(cnpj_busca=None):
    """Exibe todos os dados da empresa e abre opções para Editar ou Excluir."""
    if cnpj_busca is None:
        cnpj_busca = input("Informe o CNPJ para consulta: ").strip()

    cnpj_padronizado = limpar_cnpj(cnpj_busca)

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM empresas WHERE cnpj = ?", (cnpj_padronizado,)
        )
        empresa = cursor.fetchone()

    if not empresa:
        print("\nEmpresa não encontrada.")
        return None

    # Exibição rica com todos os novos campos organizados
    print("\n========================================")
    print("           DADOS DA EMPRESA             ")
    print("========================================")
    print(f"CNPJ:                {empresa[0]}")
    print(f"Razão Social:        {empresa[1]}")
    print(f"Regime Tributário:   {empresa[2]}")
    print(f"Atividade Principal: {empresa[3]}")
    print(f"Início Atividades:   {empresa[4]}")
    print(f"Inscrição Estadual:  {empresa[5]}")
    print(f"Inscrição Municipal: {empresa[6]}")
    print(f"Endereço:            {empresa[7]}")
    print(f"Cidade/UF:           {empresa[8]} - {empresa[9]}")
    print(f"CEP:                 {empresa[10]}")
    print("========================================")

    # Nova seção de Gerenciamento (Edição / Exclusão)
    print("\nO que deseja fazer com este registro?")
    print("1 - Editar Razão Social")
    print("2 - Excluir Empresa definitivamente")
    print("3 - Voltar ao Menu")

    opcao = input("Escolha uma opção: ").strip()

    if opcao == "1":
        nova_razao = input("Digite a nova Razão Social: ").strip()
        if nova_razao:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE empresas SET razao_social = ? WHERE cnpj = ?",
                    (nova_razao, cnpj_padronizado),
                )
                print("\nRazão Social alterada com sucesso!")
        else:
            print("\nAlteração cancelada (campo vazio).")

    elif opcao == "2":
        # Confirmação de segurança para exclusão
        confirmar = (
            input(
                f"Tem certeza que deseja EXCLUIR a empresa {empresa[1]}? (S/N): "
            )
            .strip()
            .upper()
        )
        if confirmar == "S":
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM empresas WHERE cnpj = ?", (cnpj_padronizado,)
                )
                print("\nEmpresa excluída do banco de dados com sucesso!")
        else:
            print("\nExclusão cancelada.")

    return empresa

# =====================================================================
# LOOP PRINCIPAL DO SISTEMA
# =====================================================================

def menu():
    inicializar_banco()

    while True:
        print("\n=== MENU CENTRAL DE EMPRESAS ===")
        print("1 - Cadastrar Empresa")
        print("2 - Listar Empresas (Resumo)")
        print("3 - Consultar / Editar / Excluir por CNPJ")
        print("4 - Sair")

        op = input("Escolha a opção: ").strip()

        if op == "1":
            cadastrar_empresa()
        elif op == "2":
            listar_empresas()
        elif op == "3":
            consultar_e_editar_empresa()
        elif op == "4":
            print("\nEncerrando o sistema...")
            break
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    menu()