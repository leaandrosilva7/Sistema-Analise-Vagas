"""Tela de login e cadastro (UC01/UC02)."""
import tkinter as tk
from tkinter import ttk

from core.servicos import ErroValidacao
from . import tema

DESTAQUES = ("Tecnologias e salários em alta", "Filtros, comparação e relatórios", "Seus dados ficam no seu computador")


class TelaLogin(ttk.Frame):
    def __init__(self, pai, servico, ao_entrar):
        super().__init__(pai)
        self.servico = servico
        self.ao_entrar = ao_entrar
        self.modo = "login"

        cartao = ttk.Frame(self, style="Card.TFrame")
        cartao.place(relx=0.5, rely=0.5, anchor="center")

        # ---- painel de marca (esquerda)
        marca = tk.Frame(cartao, bg=tema.ACENTO, padx=32, pady=36)
        marca.pack(side="left", fill="y")
        tk.Label(marca, text="AV", bg=tema.SUPERFICIE, fg=tema.ACENTO, font=(tema.FAMILIA, 13, "bold"),
                 width=3, pady=6).pack(anchor="w")
        tk.Label(marca, text="Análise de\nVagas Tech", bg=tema.ACENTO, fg=tema.SUPERFICIE, justify="left",
                 font=(tema.FAMILIA, 22, "bold")).pack(anchor="w", pady=(18, 6))
        tk.Label(marca, text="Explore o mercado de tecnologia.", bg=tema.ACENTO, fg="#dbe6ff",
                 font=tema.FONTE).pack(anchor="w")
        tk.Frame(marca, bg=tema.ACENTO, height=26).pack()
        for texto in DESTAQUES:
            tk.Label(marca, text=f"✓  {texto}", bg=tema.ACENTO, fg=tema.SUPERFICIE, font=tema.FONTE,
                     anchor="w").pack(anchor="w", pady=3)

        # ---- formulário (direita)
        form = ttk.Frame(cartao, style="Plano.TFrame", padding=(36, 32))
        form.pack(side="left", fill="both")
        form.columnconfigure(0, weight=1)

        self.var_nome = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_senha = tk.StringVar()
        self.var_conf = tk.StringVar()
        self.var_ver = tk.BooleanVar(value=False)

        self.lbl_titulo = ttk.Label(form, text="Entrar", style="Sub.TLabel", font=(tema.FAMILIA, 16, "bold"))
        self.lbl_titulo.grid(row=0, column=0, sticky="w")
        self.lbl_sub = ttk.Label(form, text="Acesse sua conta para continuar.", style="CardMuted.TLabel")
        self.lbl_sub.grid(row=1, column=0, sticky="w", pady=(2, 16))

        self.lbl_nome = ttk.Label(form, text="Nome", style="Campo.TLabel")
        self.ent_nome = ttk.Entry(form, textvariable=self.var_nome, width=34)
        self.lbl_email = ttk.Label(form, text="Email", style="Campo.TLabel")
        self.ent_email = ttk.Entry(form, textvariable=self.var_email, width=34)
        self.lbl_senha = ttk.Label(form, text="Senha", style="Campo.TLabel")
        self.ent_senha = ttk.Entry(form, textvariable=self.var_senha, show="•", width=34)
        self.lbl_conf = ttk.Label(form, text="Confirmar senha", style="Campo.TLabel")
        self.ent_conf = ttk.Entry(form, textvariable=self.var_conf, show="•", width=34)
        self.chk_ver = ttk.Checkbutton(form, text="Mostrar senha", variable=self.var_ver, style="Card.TCheckbutton",
                                       command=self._alternar_senha)

        linhas = [(2, self.lbl_nome, self.ent_nome), (4, self.lbl_email, self.ent_email),
                  (6, self.lbl_senha, self.ent_senha), (8, self.lbl_conf, self.ent_conf)]
        for r, lbl, ent in linhas:
            lbl.grid(row=r, column=0, sticky="w")
            ent.grid(row=r + 1, column=0, sticky="ew", pady=(3, 10))
        self.chk_ver.grid(row=10, column=0, sticky="w")
        for w in (self.lbl_nome, self.ent_nome, self.lbl_conf, self.ent_conf):
            w.grid_remove()

        self.lbl_erro = ttk.Label(form, text="", style="ErroCard.TLabel", wraplength=300)
        self.lbl_erro.grid(row=11, column=0, sticky="w", pady=(6, 0))
        self.btn = ttk.Button(form, text="Entrar", style="Primario.TButton", command=self.enviar)
        self.btn.grid(row=12, column=0, sticky="ew", pady=(12, 6), ipady=3)
        self.btn_alt = ttk.Button(form, text="Não tem conta? Cadastre-se", style="Link.TButton", command=self.alternar)
        self.btn_alt.grid(row=13, column=0, sticky="ew")

        for e in (self.ent_email, self.ent_senha, self.ent_nome, self.ent_conf):
            e.bind("<Return>", lambda _e: self.enviar())
        self.ent_email.focus_set()

    def _alternar_senha(self):
        mostrar = "" if self.var_ver.get() else "•"
        self.ent_senha.config(show=mostrar)
        self.ent_conf.config(show=mostrar)

    def alternar(self):
        self.modo = "registro" if self.modo == "login" else "login"
        self.lbl_erro.config(text="")
        reg = self.modo == "registro"
        self.lbl_titulo.config(text="Criar conta" if reg else "Entrar")
        self.lbl_sub.config(text="Leva menos de um minuto." if reg else "Acesse sua conta para continuar.")
        self.btn.config(text="Cadastrar" if reg else "Entrar")
        self.btn_alt.config(text="Já tenho conta" if reg else "Não tem conta? Cadastre-se")
        for w in (self.lbl_nome, self.ent_nome, self.lbl_conf, self.ent_conf):
            w.grid() if reg else w.grid_remove()
        (self.ent_nome if reg else self.ent_email).focus_set()

    def enviar(self):
        try:
            email, senha = self.var_email.get(), self.var_senha.get()
            if self.modo == "registro":
                if senha != self.var_conf.get():
                    raise ErroValidacao("As senhas não conferem.")
                self.servico.registrar(email, senha, self.var_nome.get())
            usuario = self.servico.login(email, senha)
        except ErroValidacao as e:
            self.lbl_erro.config(text=str(e))
            return
        self.ao_entrar(usuario)
