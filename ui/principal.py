"""Janela principal: alterna entre login e o sistema (abas + menu)."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import db, exemplos, supabase_sync
from core.servicos import ErroValidacao, Servico
from . import tema
from .dashboard import AbaDashboard
from .login import TelaLogin
from .relatorio import AbaRelatorio
from .vagas import AbaVagas


class Aplicacao(tk.Tk):
    def __init__(self, caminho_db: str = db.DB_PADRAO):
        super().__init__()
        self.title("Sistema de Análise de Vagas Tech")
        tema.aplicar_tema(self)
        self.geometry(f"{int(1180 * tema.ESC)}x{int(760 * tema.ESC)}")
        self.minsize(int(1040 * tema.ESC), int(700 * tema.ESC))
        self.caminho_db = caminho_db
        self.conn = db.conectar(caminho_db)
        self.servico = Servico(self.conn)
        self.usuario = None
        self.conteudo = None
        self.protocol("WM_DELETE_WINDOW", self.sair)
        self.mostrar_login()

    def _trocar(self, frame):
        if self.conteudo is not None:
            self.conteudo.destroy()
        self.conteudo = frame
        frame.pack(fill="both", expand=True)

    def _cancelar_avisos(self):
        if getattr(self, "_aviso_id", None):
            self.after_cancel(self._aviso_id)
            self._aviso_id = None

    def mostrar_login(self):
        self._cancelar_avisos()
        self.usuario = None
        self.config(menu=tk.Menu(self))
        self._trocar(TelaLogin(self, self.servico, self.entrar))

    def entrar(self, usuario):
        self.usuario = usuario
        self._montar_menu()
        raiz = ttk.Frame(self)
        barra = ttk.Frame(raiz, style="Barra.TFrame", padding=(20, 8))
        barra.pack(fill="x")
        tk.Frame(raiz, bg=tema.BORDA, height=1).pack(fill="x")

        # marca
        tk.Label(barra, text="AV", bg=tema.ACENTO, fg=tema.SUPERFICIE, font=(tema.FAMILIA, 10, "bold"),
                 width=3, pady=4).pack(side="left")
        ttk.Label(barra, text="Análise de Vagas Tech", style="Barra.TLabel",
                  font=(tema.FAMILIA, 12, "bold")).pack(side="left", padx=(10, 14))

        # navegação (as abas nativas ficam ocultas; estes botões as selecionam)
        self.abas = ttk.Notebook(raiz, style="Oculto.TNotebook")
        self.dash = AbaDashboard(self.abas, self.servico)
        self.vagas = AbaVagas(self.abas, self.servico, ao_alterar=self.atualizar_tudo)
        self.rel = AbaRelatorio(self.abas, self.servico)
        self.nav = {}
        for rotulo, aba in (("Dashboard", self.dash), ("Vagas", self.vagas), ("Relatório", self.rel)):
            self.abas.add(aba, text=rotulo)
            b = ttk.Button(barra, text=rotulo, style="Nav.TButton", command=lambda a=aba: self.abas.select(a))
            b.pack(side="left", padx=1)
            self.nav[aba] = b

        # usuário e ações
        ttk.Button(barra, text="Sair", style="Ghost.TButton", command=self.mostrar_login).pack(side="right")
        nome = usuario["nome"] or usuario["email"]
        primeiro = nome.split()[0] if nome.split() else nome  # só o 1º nome (ou o início do e-mail) no cabeçalho
        nome_curto = primeiro if len(primeiro) <= 16 else primeiro[:15] + "…"
        ttk.Label(barra, text=nome_curto, style="Barra.TLabel").pack(side="right", padx=(8, 6))
        avatar = tk.Canvas(barra, width=30, height=30, bg=tema.SUPERFICIE, highlightthickness=0)
        avatar.create_oval(1, 1, 29, 29, fill=tema.ACENTO_CLARO, outline="")
        avatar.create_text(15, 15, text=(nome or "?")[0].upper(), fill=tema.ACENTO, font=tema.FONTE_NEGRITO)
        avatar.pack(side="right")
        self.btn_sync = ttk.Button(barra, text="⟳ Sincronizar", command=self.sincronizar)
        self.btn_sync.pack(side="right", padx=(0, 10))

        self.abas.pack(fill="both", expand=True)
        self.abas.bind("<<NotebookTabChanged>>", lambda _e: self._aba_mudou())
        self._marcar_nav()
        self._trocar(raiz)
        if self.servico.total_vagas() == 0:
            self._aviso_id = self.after(300, self._oferecer_exemplos)

    def _marcar_nav(self):
        atual = self.abas.nametowidget(self.abas.select())
        for aba, botao in self.nav.items():
            botao.config(style="NavAtivo.TButton" if aba is atual else "Nav.TButton")

    def _aba_mudou(self):
        self._marcar_nav()
        aba = self.abas.nametowidget(self.abas.select())
        if aba is self.dash:
            self.dash.atualizar()
        elif aba is self.rel:
            self.rel.atualizar()

    def atualizar_tudo(self):
        self.dash.atualizar()
        self.rel.atualizar()

    def _montar_menu(self):
        m = tk.Menu(self)
        arq = tk.Menu(m, tearoff=0)
        arq.add_command(label="Nova vaga…", command=lambda: (self.abas.select(self.vagas), self.vagas.nova()))
        arq.add_command(label="Importar vagas (CSV/JSON)…", command=self.importar)
        arq.add_command(label="Sincronizar com Supabase", command=self.sincronizar)
        arq.add_command(label="Carregar dados de exemplo", command=self.carregar_exemplos)
        arq.add_separator()
        arq.add_command(label="Sair", command=self.sair)
        m.add_cascade(label="Arquivo", menu=arq)
        aj = tk.Menu(m, tearoff=0)
        aj.add_command(label="Sobre", command=lambda: messagebox.showinfo(
            "Sobre", "Sistema de Análise de Vagas Tech\nRAD em Python • Tkinter • SQLite3\n"
                     "CRUD de vagas, dashboard, comparação e relatórios."))
        m.add_cascade(label="Ajuda", menu=aj)
        self.config(menu=m)

    # ----- ações de arquivo
    def importar(self):
        caminho = filedialog.askopenfilename(
            parent=self, title="Importar vagas",
            filetypes=[("Vagas (CSV ou JSON)", "*.csv *.json"), ("CSV", "*.csv"), ("JSON", "*.json")])
        if not caminho:
            return
        try:
            r = self.servico.importar_arquivo(caminho)
        except (ErroValidacao, OSError, ValueError) as e:
            return messagebox.showerror("Falha na importação", str(e), parent=self)
        msg = (f"Recebidas: {r['total_recebido']}\nInseridas: {r['inseridas']}\n"
               f"Já existentes (ignoradas): {r['duplicadas']}\nRejeitadas: {r['rejeitadas']}")
        if r["erros"]:
            msg += "\n\n" + "\n".join(r["erros"][:8])
        messagebox.showinfo("Importação concluída", msg, parent=self)
        self.vagas.carregar()
        self.atualizar_tudo()

    def sincronizar(self):
        """Baixa as vagas do Supabase em segundo plano (a tela não trava) e grava no SQLite."""
        if getattr(self, "_sync_ativo", False):
            return
        self._sync_ativo = True
        self.btn_sync.config(text="Sincronizando…", state="disabled")
        self.config(cursor="watch")
        fila = queue.Queue()
        url = supabase_sync.ler_env().get("DATABASE_URL")

        def trabalho():
            try:
                fila.put(("ok", supabase_sync.buscar_remoto(url)))
            except supabase_sync.ErroSync as e:
                fila.put(("erro", str(e)))
            except Exception as e:  # noqa: BLE001
                fila.put(("erro", f"Erro inesperado: {e}"))

        def checar():
            try:
                tipo, dado = fila.get_nowait()
            except queue.Empty:
                return self.after(150, checar)
            self._sync_ativo = False
            self.config(cursor="")
            try:
                self.btn_sync.config(text="⟳ Sincronizar", state="normal")
            except tk.TclError:
                return
            if tipo == "erro":
                return messagebox.showerror("Sincronização", dado, parent=self)
            r = supabase_sync.aplicar_remotos(self.conn, *dado)
            messagebox.showinfo("Sincronização concluída",
                                f"Vagas no Supabase: {r['recebidas']}\nNovas: {r['inseridas']}\n"
                                f"Atualizadas: {r['atualizadas']}\nIgnoradas (dados incompletos): {r['ignoradas']}",
                                parent=self)
            self.vagas.carregar()
            self.atualizar_tudo()

        threading.Thread(target=trabalho, daemon=True).start()
        self.after(150, checar)

    def carregar_exemplos(self):
        r = self.servico.importar_vagas(exemplos.gerar(80))
        messagebox.showinfo("Dados de exemplo", f"{r['inseridas']} vaga(s) de exemplo adicionadas.", parent=self)
        self.vagas.carregar()
        self.atualizar_tudo()

    def _oferecer_exemplos(self):
        if messagebox.askyesno("Banco vazio", "Ainda não há vagas cadastradas.\n"
                               "Deseja carregar dados de exemplo para conhecer o sistema?", parent=self):
            self.carregar_exemplos()

    def sair(self):
        self._cancelar_avisos()
        try:
            self.conn.close()
        finally:
            self.destroy()
