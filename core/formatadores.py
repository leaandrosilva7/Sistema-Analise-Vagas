"""Formatação e normalização de valores (porta de formatters.js)."""
import unicodedata
from datetime import date, datetime

class ErroValidacao(ValueError):
    """Dado inválido informado pelo usuário (mensagem pronta para exibir)."""


SENIORIDADES = {
    "estagio": "Estágio",
    "trainee": "Trainee",
    "junior": "Júnior",
    "pleno": "Pleno",
    "senior": "Sênior",
    "nao_informado": "Não informada",
}
MODALIDADES = {
    "remoto": "Remoto",
    "hibrido": "Híbrido",
    "presencial": "Presencial",
    "nao_informado": "Não informada",
}


def sem_acento(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in texto if not unicodedata.combining(c))


def _chave(texto) -> str:
    return sem_acento(texto).strip().lower().replace(" ", "_")


def normalizar_senioridade(valor) -> str:
    """'Sênior', 'senior', 'SÊNIOR' -> 'senior'; desconhecido -> 'nao_informado'."""
    k = _chave(valor)
    if k in ("nao_informada", "nao_informado", ""):
        return "nao_informado"
    if k in SENIORIDADES:
        return k
    if "senior" in k or k == "sr":
        return "senior"
    if "junior" in k or k == "jr":
        return "junior"
    if "estag" in k:
        return "estagio"
    return k if k in SENIORIDADES else "nao_informado"


def normalizar_modalidade(valor) -> str:
    k = _chave(valor)
    if k in MODALIDADES:
        return k
    if k in ("nao_informada", ""):
        return "nao_informado"
    if "remot" in k or k in ("home_office", "homeoffice"):
        return "remoto"
    if "hibrid" in k or k == "hybrid":
        return "hibrido"
    if "presenc" in k or k == "onsite":
        return "presencial"
    return "nao_informado"


def formatar_senioridade(valor) -> str:
    return SENIORIDADES.get(normalizar_senioridade(valor), "Não informada")


def formatar_modalidade(valor) -> str:
    return MODALIDADES.get(normalizar_modalidade(valor), "Não informada")


def formatar_moeda(valor, moeda: str = "BRL") -> str:
    """1234.5 -> 'R$ 1.234,50' (padrão pt-BR)."""
    try:
        if valor is None or valor == "":
            return "Não informado"
        n = float(valor)
    except (TypeError, ValueError):
        return "Não informado"
    texto = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    simbolo = {"BRL": "R$", "USD": "US$", "EUR": "€", "GBP": "£"}.get((moeda or "BRL").upper(), moeda or "R$")
    return f"{simbolo} {texto}"


def formatar_faixa(minimo, maximo, moeda="BRL") -> str:
    if minimo is None and maximo is None:
        return "Faixa salarial não informada"
    if minimo is None:
        return f"até {formatar_moeda(maximo, moeda)}"
    if maximo is None:
        return f"a partir de {formatar_moeda(minimo, moeda)}"
    return f"{formatar_moeda(minimo, moeda)} - {formatar_moeda(maximo, moeda)}"


def formatar_data(iso) -> str:
    """'2026-11-23' -> '23/11/2026'."""
    if not iso:
        return ""
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)


def parse_data(texto):
    """Aceita 'AAAA-MM-DD' ou 'DD/MM/AAAA'. Vazio -> None. Inválido -> ValueError."""
    t = str(texto or "").strip()
    if not t:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(t[:10], fmt).date().isoformat()
        except ValueError:
            continue
    raise ErroValidacao(f"Data inválida: '{t}'. Use DD/MM/AAAA.")


def parse_numero(texto):
    """'5.000,50' | '5000.50' | '5000' -> float. Vazio -> None."""
    t = str(texto if texto is not None else "").strip().replace("R$", "").replace(" ", "")
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        n = float(t)
    except ValueError:
        raise ErroValidacao(f"Valor numérico inválido: '{texto}'.")
    return n


def hoje() -> str:
    return date.today().isoformat()
