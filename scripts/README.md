# scripts

Script Python standalone usati per risolvere i livelli dei wargame. Ogni script è un
file singolo, indipendente e distinguibile per scopo.

## Dipendenze

`requirements.txt` raccoglie le dipendenze di **tutti** gli script della cartella, così
un unico ambiente virtuale basta per eseguirli tutti. Il `.venv` resta locale (non
versionato); si ricrea da `requirements.txt`:

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
```

Aggiungendo un nuovo script, aggiornare `requirements.txt` con le eventuali nuove
dipendenze, mantenendo i version floor (es. `requests>=2.32`).

## Script

- **`natas15_blind_sqli.py`** — Blind SQL injection boolean-based per natas15: estrae la
  password di natas16 un byte alla volta sfruttando l'oracolo booleano ("This user
  exists." / "…doesn't exist."). Nessuna credenziale hardcoded: la password di accesso
  al livello va passata con `--password`.

  ```bash
  python natas15_blind_sqli.py --password <password_natas15> --verbose
  ```
