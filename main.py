"""Sistema de Análise de Vagas Tech — RAD em Python + Tkinter + SQLite3.

Execução:  python main.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import tema  # noqa: E402
from ui.principal import Aplicacao  # noqa: E402

if __name__ == "__main__":
    tema.ativar_dpi()  # interface nítida em telas com escala > 100% (Windows)
    Aplicacao().mainloop()
