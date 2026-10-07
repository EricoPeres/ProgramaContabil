import os
import re
import sqlite3

from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

PATH_DB = "db"
EMPRESA_DB = os.path.join(PATH_DB, "empresas.db")

# ============================================
# GERENCIADOR DE BANCO DE DADOS (DB_MANAGER)
# ============================================

class DatabaseManager:

  @staticmethod
  def garantir_pasta_db():
    if not os.path.exists(PATH_DB):
      os.makedirs(PATH_DB)

  @staticmethod
  def inicializar_db_empresas():
    DatabaseManager.garantir_pasta_db()
    db_path = os.path.join(PATH_DB, "empresas.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj TEXT UNIQUE NOT NULL,
                razao_social TEXT NOT NULL,
                nome_fantasia TEXT
            )
        """)
    conn.commit()
    conn.close()

  @staticmethod
  def inicializar_db_empresa(cnpj):
    DatabaseManager.garantir_pasta_db()
    cnpj_limpo = re.sub(r"\D", "", cnpj)

    # 1. Banco do Plano de Contas
    db_plano = os.path.join(PATH_DB, f"plano_contas_{cnpj_limpo}.db")
    conn_plano = sqlite3.connect(db_plano)
    cursor_plano = conn_plano.cursor()
    cursor_plano.execute("""
            CREATE TABLE IF NOT EXISTS contas (
                resumida TEXT PRIMARY KEY,
                codigo TEXT NOT NULL,
                nome TEXT NOT NULL,
                natureza TEXT NOT NULL,
                tipo TEXT NOT NULL
            )
        """)

    # Popula contas padrão caso o plano de contas esteja vazio
    cursor_plano.execute("SELECT COUNT(*) FROM contas")
    if cursor_plano.fetchone()[0] == 0:
      contas_padrao = [
          ("1", "1.1.1.01", "CAIXA GERAL", "D", "A"),
          ("2", "1.1.1.02", "BANCO CONTA MOVIMENTO - ITAU", "D", "A"),
          ("10", "2.1.1.01", "FORNECEDORES NACIONAIS", "C", "A"),
          ("11", "2.1.2.01", "SALÁRIOS E ORDENADOS A PAGAR", "C", "A"),
          ("50", "4.1.1.01", "RECEITA DE VENDAS DE MERCADORIAS", "C", "A"),
          ("80", "3.1.1.01", "DESPESAS COM SALÁRIOS E ORDENADOS", "D", "A"),
          ("81", "3.1.1.02", "DESPESAS COM ALUGUEL", "D", "A"),
      ]
      cursor_plano.executemany(
          "INSERT INTO contas VALUES (?, ?, ?, ?, ?)", contas_padrao
      )
    conn_plano.commit()
    conn_plano.close()

    # 2. Banco dos Lançamentos Contábeis
    db_lanc = os.path.join(PATH_DB, f"lancamentos_{cnpj_limpo}.db")
    conn_lanc = sqlite3.connect(db_lanc)
    cursor_lanc = conn_lanc.cursor()
    cursor_lanc.execute("""
            CREATE TABLE IF NOT EXISTS lotes (
                numero TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                descricao TEXT
            )
        """)
    cursor_lanc.execute("""
            CREATE TABLE IF NOT EXISTS partidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_numero TEXT NOT NULL,
                item INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                conta TEXT NOT NULL,
                descricao_conta TEXT,
                valor REAL NOT NULL,
                historico TEXT,
                FOREIGN KEY (lote_numero) REFERENCES lotes(numero)
            )
        """)
    conn_lanc.commit()
    conn_lanc.close()

# ============================================
# JANELA DE SELEÇÃO / CADASTRO DE EMPRESAS
# ============================================

class JanelaSelecaoEmpresa(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Seleção de Empresa")
        self.geometry("550x350")
        self.resizable(False, False)

        # Variável para armazenar a empresa selecionada (CNPJ)
        self.empresa_selecionada = None

        # Configuração da Interface Gráfica
        self.criar_widgets()

        # Carregar a lista de empresas do banco de dados
        self.carregar_empresas()

    def criar_widgets(self):
        # Título principal
        lbl_titulo = ttk.Label(
            self,
            text="Selecione a Empresa para Lançamentos",
            font=("Arial", 14, "bold"),
        )
        lbl_titulo.pack(pady=15)

        # Frame para a tabela (Treeview)
        frame_tabela = ttk.Frame(self)
        frame_tabela.pack(padx=20, pady=10, fill="both", expand=True)

        # Scrollbar vertical
        scrollbar = ttk.Scrollbar(frame_tabela, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # Tabela das empresas
        cols = ("cnpj", "razao_social", "uf")
        self.tree = ttk.Treeview(
            frame_tabela,
            columns=cols,
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="browse",
        )
        scrollbar.config(command=self.tree.yview)

        # Configuração dos cabeçalhos e larguras das colunas
        self.tree.heading("cnpj", text="CNPJ")
        self.tree.heading("razao_social", text="Razão Social")
        self.tree.heading("uf", text="UF")

        self.tree.column("cnpj", width=140, anchor="center")
        self.tree.column("razao_social", width=280, anchor="w")
        self.tree.column("uf", width=50, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Evento de duplo clique na linha da tabela
        self.tree.bind("<Double-1>", lambda event: self.confirmar_selecao())

        # Frame dos botões inferiores
        frame_botoes = ttk.Frame(self)
        frame_botoes.pack(pady=15)

        btn_confirmar = ttk.Button(
            frame_botoes,
            text="Confirmar / Abrir",
            command=self.confirmar_selecao,
        )
        btn_confirmar.pack(side="left", padx=10)

        btn_cancelar = ttk.Button(
            frame_botoes, text="Sair", command=self.destroy
        )
        btn_cancelar.pack(side="left", padx=10)

    def carregar_empresas(self):
        """Busca as empresas cadastradas utilizando a estrutura oficial (cnpj, razao_social, uf)."""
        # Limpa dados anteriores da tabela
        for i in self.tree.get_children():
            self.tree.delete(i)

        try:
            with sqlite3.connect(EMPRESA_DB) as conn:
                cursor = conn.cursor()
                # Consulta ajustada: CNPJ como chave em vez de ID
                cursor.execute(
                    "SELECT cnpj, razao_social, uf FROM empresas ORDER BY"
                    " razao_social"
                )
                empresas = cursor.fetchall()

                if not empresas:
                    messagebox.showwarning(
                        "Aviso",
                        "Nenhuma empresa cadastrada encontrada no banco de"
                        " dados.",
                    )
                    return

                for emp in empresas:
                    cnpj, razao_social, uf = emp
                    # O 'iid' da linha passa a ser o próprio CNPJ
                    self.tree.insert(
                        "",
                        "end",
                        iid=cnpj,
                        values=(cnpj, razao_social, uf),
                    )

        except sqlite3.Error as e:
            messagebox.showerror(
                "Erro de Banco de Dados",
                f"Erro ao carregar lista de empresas:\n{e}",
            )

    def confirmar_selecao(self):
        """Captura o CNPJ da empresa selecionada e prossegue."""
        item_selecionado = self.tree.selection()

        if not item_selecionado:
            messagebox.showwarning(
                "Atenção", "Por favor, selecione uma empresa na lista!"
            )
            return

        # O 'iid' configurado no insert representa o CNPJ da empresa
        cnpj_selecionado = item_selecionado[0]
        dados_empresa = self.tree.item(cnpj_selecionado, "values")

        # Armazena os dados da empresa selecionada
        self.empresa_selecionada = {
            "cnpj": dados_empresa[0],
            "razao_social": dados_empresa[1],
            "uf": dados_empresa[2],
        }

        # Fecha a janela de seleção
        self.destroy()    

# ============================================
# JANELA POP-UP DE BUSCA DE CONTAS (F9)
# ============================================

class JanelaBuscaContas(tk.Toplevel):

  def __init__(self, parent, db_plano_path, callback_selecao):
    super().__init__(parent)
    self.title("Pesquisa do Plano de Contas - [F9]")
    self.geometry("700x450")
    self.configure(bg="#ece9d8")
    self.resizable(False, False)

    self.transient(parent)
    self.grab_set()

    self.db_plano_path = db_plano_path
    self.callback_selecao = callback_selecao

    frame_busca = ttk.LabelFrame(self, text=" Filtro de Pesquisa ")
    frame_busca.pack(fill="x", padx=10, pady=5)

    tk.Label(
        frame_busca,
        text="Pesquisar por (Nome, Código ou ID):",
        bg="#ece9d8",
        font=("Tahoma", 8, "bold"),
    ).pack(anchor="w", padx=5, pady=2)

    self.ent_busca = tk.Entry(frame_busca, font=("Tahoma", 10))
    self.ent_busca.pack(fill="x", padx=5, pady=5)
    self.ent_busca.bind("<KeyRelease>", self.filtrar_contas)
    self.ent_busca.focus()

    frame_grid = ttk.Frame(self)
    frame_grid.pack(fill="both", expand=True, padx=10, pady=5)

    colunas = ("resumida", "codigo", "nome", "nat", "tipo")
    self.tree = ttk.Treeview(
        frame_grid, columns=colunas, show="headings", height=12
    )

    self.tree.heading("resumida", text="ID Resumida")
    self.tree.heading("codigo", text="Código Estruturado")
    self.tree.heading("nome", text="Descrição da Conta")
    self.tree.heading("nat", text="Nat.")
    self.tree.heading("tipo", text="Tipo")

    self.tree.column("resumida", width=90, anchor="center")
    self.tree.column("codigo", width=120, anchor="center")
    self.tree.column("nome", width=350, anchor="w")
    self.tree.column("nat", width=50, anchor="center")
    self.tree.column("tipo", width=50, anchor="center")

    scrollbar = ttk.Scrollbar(
        frame_grid, orient="vertical", command=self.tree.yview
    )
    self.tree.configure(yscroll=scrollbar.set)
    self.tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    self.tree.bind("<Double-1>", self.confirmar_selecao)
    self.bind("<Return>", self.confirmar_selecao)
    self.bind("<Escape>", lambda event: self.destroy())

    self.filtrar_contas()

  def filtrar_contas(self, event=None):
    termo = f"%{self.ent_busca.get().strip().lower()}%"
    for item in self.tree.get_children():
      self.tree.delete(item)

    conn = sqlite3.connect(self.db_plano_path)
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT resumida, codigo, nome, natureza, tipo FROM contas
            WHERE LOWER(nome) LIKE ? OR LOWER(codigo) LIKE ? OR resumida LIKE ?
        """,
        (termo, termo, termo),
    )

    for row in cursor.fetchall():
      self.tree.insert("", "end", values=row)
    conn.close()

    children = self.tree.get_children()
    if children:
      self.tree.selection_set(children[0])
      self.tree.focus(children[0])

  def confirmar_selecao(self, event=None):
    selecao = self.tree.selection()
    if selecao:
      item = self.tree.item(selecao[0])["values"]
      self.callback_selecao(str(item[0]))
      self.destroy()

# ============================================
# TELA PRINCIPAL DE LANÇAMENTOS
# ============================================

class DominioLancamentoApp(tk.Tk):

  def __init__(self, cnpj, razao_social):
    super().__init__()
    self.cnpj = cnpj
    self.cnpj_limpo = re.sub(r"\D", "", cnpj)
    self.razao_social = razao_social

    # Caminhos dos bancos específicos da empresa
    self.db_plano_path = os.path.join(
        PATH_DB, f"plano_contas_{self.cnpj_limpo}.db"
    )
    self.db_lanc_path = os.path.join(
        PATH_DB, f"lancamentos_{self.cnpj_limpo}.db"
    )

    self.title(
        f"Lançamentos - [Domínio Contábil] - Empresa: {self.razao_social} ({self.cnpj})"
    )
    self.geometry("1020x720")
    self.configure(bg="#ece9d8")

    self.configurar_estilos()

    self.criar_abas()
    self.criar_cabecalho(self.tab_geral)
    self.criar_formulario_lancamento(self.tab_geral)
    self.criar_grid_lancamentos(self.tab_geral)
    self.criar_rodape_totais(self.tab_geral)
    self.criar_barra_botoes_principal()

    self.bind("<F8>", lambda event: self.gravar_lote())
    self.bind("<F9>", lambda event: self.abrir_busca_contas())
    self.bind("<Return>", self.navegar_com_enter)

  def configurar_estilos(self):
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TNotebook", background="#ece9d8", borderwidth=0)
    style.configure("TNotebook.Tab", background="#ece9d8", padding=[8, 4])
    style.configure("TFrame", background="#ece9d8")
    style.configure("TLabelframe", background="#ece9d8")
    style.configure(
        "TLabelframe.Label", background="#ece9d8", font=("Tahoma", 8, "bold")
    )

  def converter_valor_para_float(self, valor_str):
    if not valor_str:
      return 0.0
    try:
      limpo = str(valor_str).replace(".", "").replace(",", ".").strip()
      return float(limpo)
    except ValueError:
      return 0.0

  def formatar_float_para_moeda(self, valor_float):
    return (
        f"{valor_float:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

  def navegar_com_enter(self, event):
    focus = self.focus_get()
    if isinstance(focus, (tk.Entry, ttk.Combobox, ttk.Entry)):
      focus.tk_focusNext().focus()

  def abrir_busca_contas(self):
    JanelaBuscaContas(self, self.db_plano_path, self.preencher_conta_selecionada)

  def preencher_conta_selecionada(self, resumida):
    self.ent_conta.delete(0, tk.END)
    self.ent_conta.insert(0, resumida)
    self.atualizar_descricao_conta()
    self.ent_valor.focus()

  def criar_abas(self):
    self.notebook = ttk.Notebook(self)
    self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
    self.tab_geral = ttk.Frame(self.notebook)
    self.notebook.add(self.tab_geral, text="  Geral  ")

  def criar_cabecalho(self, parent):
    frame = ttk.LabelFrame(parent, text=" Dados do Lote ")
    frame.pack(fill="x", padx=5, pady=2)

    tk.Label(frame, text="Lote:", bg="#ece9d8").grid(
        row=0, column=0, padx=5, pady=5, sticky="e"
    )
    self.ent_lote = tk.Entry(frame, width=10, font=("Tahoma", 9, "bold"))
    self.ent_lote.insert(0, "000001")
    self.ent_lote.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame, text="Data:", bg="#ece9d8").grid(
        row=0, column=2, padx=5, pady=5, sticky="e"
    )
    self.ent_data = tk.Entry(frame, width=12)
    self.ent_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
    self.ent_data.grid(row=0, column=3, padx=5, pady=5)

    tk.Label(frame, text="Descrição:", bg="#ece9d8").grid(
        row=0, column=4, padx=5, pady=5, sticky="e"
    )
    self.ent_desc_lote = tk.Entry(frame, width=50)
    self.ent_desc_lote.insert(0, "MOVIMENTO CONTÁBIL DIÁRIO")
    self.ent_desc_lote.grid(row=0, column=5, padx=5, pady=5, sticky="we")

  def criar_formulario_lancamento(self, parent):
    frame = ttk.LabelFrame(parent, text=" Partida do Lançamento ")
    frame.pack(fill="x", padx=5, pady=2)

    tk.Label(frame, text="Tipo (D/C):", bg="#ece9d8").grid(
        row=0, column=0, padx=5, pady=2, sticky="e"
    )
    self.cmb_tipo = ttk.Combobox(
        frame, values=["D", "C"], width=3, state="readonly"
    )
    self.cmb_tipo.set("D")
    self.cmb_tipo.grid(row=0, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame, text="Conta Resumida:", bg="#ece9d8").grid(
        row=0, column=2, padx=5, pady=2, sticky="e"
    )
    self.ent_conta = tk.Entry(frame, width=10)
    self.ent_conta.grid(row=0, column=3, padx=5, pady=2, sticky="w")
    self.ent_conta.bind("<FocusOut>", self.atualizar_descricao_conta)
    self.ent_conta.bind("<F9>", lambda event: self.abrir_busca_contas())

    btn_f9 = tk.Button(
        frame,
        text="F9 Pesquisar",
        bg="#d4d0c8",
        relief="raised",
        font=("Tahoma", 7),
        command=self.abrir_busca_contas,
    )
    btn_f9.grid(row=0, column=4, padx=2, pady=2, sticky="w")

    self.lbl_nome_conta = tk.Label(
        frame,
        text="[Informe a Conta]",
        font=("Tahoma", 9, "bold"),
        fg="#000080",
        bg="#ece9d8",
    )
    self.lbl_nome_conta.grid(row=0, column=5, padx=5, pady=2, sticky="w")

    tk.Label(frame, text="Valor (R$):", bg="#ece9d8").grid(
        row=1, column=0, padx=5, pady=2, sticky="e"
    )
    self.ent_valor = tk.Entry(frame, width=15, justify="right")
    self.ent_valor.grid(
        row=1, column=1, columnspan=2, padx=5, pady=2, sticky="w"
    )

    tk.Label(frame, text="Histórico:", bg="#ece9d8").grid(
        row=1, column=3, padx=5, pady=2, sticky="e"
    )
    self.ent_historico = tk.Entry(frame, width=50)
    self.ent_historico.grid(
        row=1, column=4, columnspan=2, padx=5, pady=2, sticky="we"
    )

    btn_add = tk.Button(
        frame,
        text="Adicionar (Enter)",
        bg="#d4d0c8",
        relief="raised",
        command=self.adicionar_partida,
    )
    btn_add.grid(row=1, column=6, padx=5, pady=2)

  def atualizar_descricao_conta(self, event=None):
    resumida = self.ent_conta.get().strip()
    if not resumida:
      self.lbl_nome_conta.config(text="[Informe a Conta]")
      return

    conn = sqlite3.connect(self.db_plano_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT codigo, nome FROM contas WHERE resumida = ?", (resumida,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
      self.lbl_nome_conta.config(text=f"[{row[0]}] {row[1]}")
    else:
      self.lbl_nome_conta.config(text="[ CONTA NÃO ENCONTRADA ]")

  def criar_grid_lancamentos(self, parent):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=5, pady=2)

    colunas = ("item", "tipo", "conta", "descricao", "valor", "historico")
    self.tree = ttk.Treeview(frame, columns=colunas, show="headings", height=8)

    self.tree.heading("item", text="Item")
    self.tree.heading("tipo", text="D/C")
    self.tree.heading("conta", text="Conta")
    self.tree.heading("descricao", text="Descrição da Conta")
    self.tree.heading("valor", text="Valor (R$)")
    self.tree.heading("historico", text="Histórico")

    self.tree.column("item", width=50, anchor="center")
    self.tree.column("tipo", width=40, anchor="center")
    self.tree.column("conta", width=80, anchor="center")
    self.tree.column("descricao", width=220, anchor="w")
    self.tree.column("valor", width=120, anchor="e")
    self.tree.column("historico", width=350, anchor="w")

    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
    self.tree.configure(yscroll=scrollbar.set)
    self.tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

  def criar_rodape_totais(self, parent):
    frame = ttk.LabelFrame(parent, text=" Totais do Lote ")
    frame.pack(fill="x", padx=5, pady=2)

    tk.Label(frame, text="Total Débitos:", bg="#ece9d8").grid(
        row=0, column=0, padx=5, pady=5
    )
    self.ent_tot_deb = tk.Entry(
        frame,
        width=15,
        state="readonly",
        justify="right",
        font=("Tahoma", 9, "bold"),
    )
    self.ent_tot_deb.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame, text="Total Créditos:", bg="#ece9d8").grid(
        row=0, column=2, padx=5, pady=5
    )
    self.ent_tot_cred = tk.Entry(
        frame,
        width=15,
        state="readonly",
        justify="right",
        font=("Tahoma", 9, "bold"),
    )
    self.ent_tot_cred.grid(row=0, column=3, padx=5, pady=5)

    tk.Label(frame, text="Diferença:", bg="#ece9d8").grid(
        row=0, column=4, padx=5, pady=5
    )
    self.ent_diferenca = tk.Entry(
        frame,
        width=15,
        state="readonly",
        justify="right",
        font=("Tahoma", 9, "bold"),
        fg="red",
    )
    self.ent_diferenca.grid(row=0, column=5, padx=5, pady=5)

    self.recalcular_totais()

  def criar_barra_botoes_principal(self):
    frame = tk.Frame(self, bg="#d4d0c8", bd=1, relief="raised")
    frame.pack(fill="x", side="bottom", padx=2, pady=2)

    btn_gravar = tk.Button(
        frame,
        text="[F8] Gravar Lote no DB",
        bg="#ece9d8",
        relief="raised",
        command=self.gravar_lote,
    )
    btn_gravar.pack(side="left", padx=5, pady=3)

    btn_busca = tk.Button(
        frame,
        text="[F9] Buscar Conta",
        bg="#ece9d8",
        relief="raised",
        command=self.abrir_busca_contas,
    )
    btn_busca.pack(side="left", padx=5, pady=3)

    btn_limpar = tk.Button(
        frame,
        text="Novo / Limpar",
        bg="#ece9d8",
        relief="raised",
        command=self.limpar_formulario,
    )
    btn_limpar.pack(side="left", padx=5, pady=3)

    btn_sair = tk.Button(
        frame, text="Sair", bg="#ece9d8", relief="raised", command=self.destroy
    )
    btn_sair.pack(side="right", padx=5, pady=3)

  def adicionar_partida(self):
    tipo = self.cmb_tipo.get()
    conta = self.ent_conta.get().strip()
    desc = self.lbl_nome_conta.cget("text")
    val_str = self.ent_valor.get().strip()
    hist = self.ent_historico.get().strip()

    valor = self.converter_valor_para_float(val_str)

    if not conta or "NÃO ENCONTRADA" in desc or "[Informe" in desc:
      messagebox.showwarning("Aviso", "Informe uma conta contábil válida.")
      self.ent_conta.focus()
      return

    if valor <= 0:
      messagebox.showwarning("Aviso", "Informe um valor maior que zero.")
      self.ent_valor.focus()
      return

    item_idx = len(self.tree.get_children()) + 1
    val_formatado = self.formatar_float_para_moeda(valor)

    self.tree.insert(
        "", "end", values=(item_idx, tipo, conta, desc, val_formatado, hist)
    )

    self.ent_conta.delete(0, tk.END)
    self.ent_valor.delete(0, tk.END)
    self.lbl_nome_conta.config(text="[Informe a Conta]")
    self.cmb_tipo.focus()

    self.recalcular_totais()

  def recalcular_totais(self):
    total_deb, total_cred = 0.0, 0.0

    for item in self.tree.get_children():
      row = self.tree.item(item)["values"]
      tipo = str(row[1])
      val = self.converter_valor_para_float(row[4])

      if tipo == "D":
        total_deb += val
      elif tipo == "C":
        total_cred += val

    diferenca = abs(total_deb - total_cred)

    self.atualizar_campo_readonly(
        self.ent_tot_deb, self.formatar_float_para_moeda(total_deb)
    )
    self.atualizar_campo_readonly(
        self.ent_tot_cred, self.formatar_float_para_moeda(total_cred)
    )
    self.atualizar_campo_readonly(
        self.ent_diferenca, self.formatar_float_para_moeda(diferenca)
    )

  def atualizar_campo_readonly(self, campo, texto):
    campo.config(state="normal")
    campo.delete(0, tk.END)
    campo.insert(0, texto)
    campo.config(state="readonly")

  def gravar_lote(self):
    """Efetiva a gravação do Lote e das Partidas no banco SQLite individual da empresa."""
    if not self.tree.get_children():
      messagebox.showwarning(
          "Aviso", "Não existem partidas lançadas neste lote."
      )
      return

    diferenca = self.converter_valor_para_float(self.ent_diferenca.get())

    if diferenca != 0.0:
      messagebox.showerror(
          "Erro de Partida Dobrada",
          f"O lote está desbalanceado!\n\nDiferença: R$"
          f" {self.ent_diferenca.get()}",
      )
      return

    lote_num = self.ent_lote.get().strip()
    data_lote = self.ent_data.get().strip()
    desc_lote = self.ent_desc_lote.get().strip()

    conn = sqlite3.connect(self.db_lanc_path)
    cursor = conn.cursor()

    try:
      # Grava o cabeçalho do lote
      cursor.execute(
          "INSERT OR REPLACE INTO lotes (numero, data, descricao) VALUES (?, ?,"
          " ?)",
          (lote_num, data_lote, desc_lote),
      )

      # Grava cada uma das partidas
      for item in self.tree.get_children():
        row = self.tree.item(item)["values"]
        cursor.execute(
            """
                    INSERT INTO partidas (lote_numero, item, tipo, conta, descricao_conta, valor, historico)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
            (
                lote_num,
                row[0],
                row[1],
                str(row[2]),
                str(row[3]),
                self.converter_valor_para_float(row[4]),
                str(row[5]),
            ),
        )

      conn.commit()
      messagebox.showinfo(
          "Sucesso",
          f"Lote Nº {lote_num} gravado com sucesso no banco de dados!",
      )
      self.limpar_formulario()
    except Exception as e:
      conn.rollback()
      messagebox.showerror("Erro de Banco de Dados", f"Falha ao gravar: {e}")
    finally:
      conn.close()

  def limpar_formulario(self):
    for item in self.tree.get_children():
      self.tree.delete(item)
    self.ent_conta.delete(0, tk.END)
    self.ent_valor.delete(0, tk.END)
    self.ent_historico.delete(0, tk.END)
    self.lbl_nome_conta.config(text="[Informe a Conta]")
    self.recalcular_totais()

# ============================================
# PONTO DE ENTRADA DO SISTEMA
# ============================================

if __name__ == "__main__":
  app_inicio = JanelaSelecaoEmpresa()
  app_inicio.mainloop()