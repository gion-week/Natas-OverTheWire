# OverTheWire – Natas

Writeup personale dei livelli del wargame **Natas** di [OverTheWire](https://overthewire.org/wargames/natas/).

Natas è pensato per chi si avvicina alla sicurezza delle applicazioni web: ogni livello espone una pagina web vulnerabile e richiede di sfruttare una debolezza reale per ottenere la password del livello successivo. Gli argomenti spaziano dall'ispezione del sorgente HTML fino a SQL injection, Local File Inclusion, command injection, deserializzazione insicura e altro.

---

## Struttura della repo

```
natas-overthewire/
├── README.md          ← questo file
├── level-00/          ← Natas Level 0 → 1
│   ├── README.md      ← writeup del livello
│   └── screenshots/   ← screenshot di supporto
├── level-01/          ← Natas Level 1 → 2
│   └── ...
└── ...
```

Ogni cartella `level-XX` rappresenta la risoluzione del livello XX, ovvero i passi necessari per trovare la password che consente l'accesso al livello successivo (XX+1).

---

## Progressione

| Livello | Argomento principale | Completato |
|---------|----------------------|:----------:|
| [Level 0](./level-00/README.md) | Ispezione sorgente HTML | ✅ |
| [Level 1](./level-01/README.md) | Ispezione sorgente HTML, tasto destro disabilitato | ✅ |
| [Level 2](./level-02/README.md) | Directory listing, file nascosti sul server web | ✅ |
| [Level 3](./level-03/README.md) | `robots.txt`, directory listing | ✅ |
| [Level 4](./level-04/README.md) | HTTP Referer header, controllo accessi lato server | ✅ |
| [Level 5](./level-05/README.md) | Cookie manipulation | ✅ |
| [Level 6](./level-06/README.md) | Inclusione file PHP (`include`), ispezione sorgente | ✅ |
| [Level 7](./level-07/README.md) | Local File Inclusion (LFI) | ✅ |
| [Level 8](./level-08/README.md) | Decodifica multi-step (`base64`, `strrev`, `bin2hex`) | ✅ |
| [Level 9](./level-09/README.md) | Command injection tramite `passthru()` e `grep` | ✅ |
| [Level 10](./level-10/README.md) | Command injection con filtro su caratteri speciali | ✅ |
| [Level 11](./level-11/README.md) | XOR cipher, manipolazione cookie cifrati | ✅ |
| [Level 12](./level-12/README.md) | Upload file, PHP webshell, estensione arbitraria | ✅ |
| [Level 13](./level-13/README.md) | Upload con controllo magic bytes (`exif_imagetype`), bypass | ✅ |
| [Level 14](./level-14/README.md) | SQL injection, bypass autenticazione | ✅ |
| [Level 15](./level-15/README.md) | Blind SQL injection (boolean-based) | ✅ |
| [Level 16](./level-16/README.md) | Blind OS command injection, bypass blacklist con `$(...)` | ✅ |
| Level 17 |  | ☐ |
| Level 18 |  | ☐ |
| Level 19 |  | ☐ |
| Level 20 |  | ☐ |
| Level 21 |  | ☐ |
| Level 22 |  | ☐ |
| Level 23 |  | ☐ |
| Level 24 |  | ☐ |
| Level 25 |  | ☐ |
| Level 26 |  | ☐ |
| Level 27 |  | ☐ |
| Level 28 |  | ☐ |
| Level 29 |  | ☐ |
| Level 30 |  | ☐ |
| Level 31 |  | ☐ |
| Level 32 |  | ☐ |
| Level 33 |  | ☐ |
| Level 34 |  | ☐ |

---

## Accesso ai livelli

Ogni livello è raggiungibile tramite browser all'URL:

```
http://natas<N>.natas.labs.overthewire.org
```

Le credenziali di accesso sono:

| Campo | Valore |
|-------|--------|
| Username | `natas<N>` |
| Password | password trovata al livello precedente |

Il livello 0 fa eccezione: username `natas0`, password `natas0`.

> I livelli Natas usano HTTP semplice (non HTTPS). Strumenti come `curl` e Burp Suite permettono di ispezionare e manipolare le richieste in modo più preciso rispetto al solo browser.

---

## Strumenti utilizzati

| Strumento | Utilizzo principale |
|-----------|---------------------|
| Browser (Firefox/Chromium) | Navigazione, DevTools (sorgente, cookie, rete) |
| `curl` | Invio richieste HTTP con header e cookie personalizzati |
| Burp Suite Community | Intercettazione e modifica di richieste HTTP |
| Python 3 | Script per brute force, encoding/decoding, automazione |
| `php` (CLI) | Verifica rapida di logica PHP lato client |

---

## Disclaimer

- L'obiettivo di questa repository non è fornire un tutorial su come si risolvono i livelli, ma descrivere il percorso personale che mi ha portato alle soluzioni. Natas è un progetto nato **per imparare le basi della sicurezza web** e l'apprendimento è la vera essenza dell'esperienza.
- Le password trovate **non vengono pubblicate** e **non sono visibili** negli screenshot per rispetto delle linee guida di OverTheWire.
- I writeup descrivono il ragionamento seguito, i comandi usati e le vulnerabilità sfruttate durante i test.
- Ogni livello include screenshot del browser e/o del terminale come supporto visivo alla lettura.
- Nella sezione **"Note e osservazioni"** di ogni README si trovano ulteriori insight sui concetti e le vulnerabilità affrontate nel livello.
