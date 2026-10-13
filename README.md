# Mass Spec Proteomics FDR Agent

PSM-level target–decoy false discovery rate (FDR) analysis with a standalone browser calculator, Python CLI and optional REST API. The repository also retains its existing **separate**, rule-based alerting and orchestration pipelines.

## Browser calculator

Open `web/index.html` in a modern browser, load a CSV (or use the synthetic example), choose an FDR threshold, calculate q-values, and download the annotated CSV. All computation runs locally in JavaScript; uploaded files are **not transmitted** to a server. Works without Python, a backend, or external dependencies.

Input requires one **already-competed winning PSM per spectrum**, with columns:

```csv
psm_id,score,is_decoy
scan1,21.4,false
scan2,18.2,false
scan3,15.1,true
```

- `psm_id`: unique identifier, starting with a letter/digit; remaining characters may include `._:-`
- `score`: finite number, with **higher = better** (reverse lower-is-better scores before use)
- `is_decoy`: `true`/`false`, `1`/`0`, `yes`/`no`, or `decoy`/`target`

### Statistical method and scope

For score cutoffs, the calculator uses the conservative target–decoy competition estimator **TDC+**:

```text
estimated FDR = min(1, (cumulative decoy wins + 1) / cumulative target wins)
q-value(score) = minimum estimated FDR over cutoffs at or below this score
```

All PSMs sharing a score are processed as one tie group. A PSM is accepted only if it is a **target** winner with q-value ≤ the selected threshold (default 0.01, i.e. 1%). A lack of observed decoys never automatically implies zero FDR.

**Assumptions:** each spectrum contributes one pre-competed target/decoy winning match, the decoy search fairly models incorrect targets, target/decoy search spaces are comparable, and scoring direction is correct. This software does not search raw spectra, construct decoys, perform target/decoy competition, rescore PSMs, or control peptide-, protein-, or site-level FDR. No clinical claims or regulatory validation are made. Do not use it as a clinical decision tool.

## Python installation and CLI

Requires Python ≥ 3.9.

```bash
git clone https://github.com/abusuraihsakhri/mass-spec-proteomics-fdr-agent.git
cd mass-spec-proteomics-fdr-agent
python -m pip install -e ".[test]"
python -m pytest -q
```

Compute PSM q-values (independent of any audit-signing key):

```bash
python -m proteomics_fdr fdr -i psms.csv -o annotated_psms.csv --alpha 0.01
```

Output columns are `psm_id,score,is_decoy,q_value,accepted`. For programmatic use, import `analyze_psms` from `proteomics_fdr.fdr`.

### Separate legacy alerting workflows

The original clinical-like `agents/` and proteomics `proteomics_fdr/agents.py` routines assess arbitrary primary/secondary thresholds and descriptor flags. Their outputs are **alerts, not statistically derived target–decoy FDR or laboratory interpretations**.

They require a nondefault HMAC signing key:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python cli.py audit --task-id TASK-001 --target TARGET-01 --primary 28.5 --secondary 14.2
python cli.py batch -i sample.csv -o results.csv
python cli.py verify-audit
python cli.py serve --host 127.0.0.1 --port 8000
```

The legacy FastAPI application has `/health`, `/metrics`, `/api/audit`, `/api/chat`, and `/api/audit/logs`. The other FastAPI application, launched with `python -m proteomics_fdr serve`, offers `POST /api/fdr` for `{"psms":[...], "alpha":0.01}` plus the original alert endpoints. For local API deployments, install requirements using the commands above.

Audit events are signed with HMAC-SHA256 and linked in memory. Signature verification detects modification of stored signed entries, but the ledger is **not durable**: restarting the process loses it, and an attacker with the signing key can forge entries. The PHI regex filter is limited and **does not establish HIPAA compliance or comprehensive de-identification**. Do not submit protected clinical information to this utility.

## Docker

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
```

Docker serves the legacy FastAPI app on port 8000. Never commit signing keys or `.env` files. The browser calculator can also be hosted as static files from `web/`; GitHub Pages deployment uses `.github/workflows/pages.yml`.

## Development and checks

Run `python -m pytest -q` and `node --check web/app.js`. CI covers Python 3.10–3.12 and performs an audit verifier check. The Python FDR calculation uses only the standard library; the older orchestration package depends on Pydantic, FastAPI and Uvicorn.

The browser calculator uses native JavaScript, File API and Blob downloads; no Pyodide/WASM runtime is required. Compatible with modern desktop/mobile browsers implementing these APIs. Max browser input is 5 MB / 50,000 PSMs (Python CLI cap: 1,000,000).

## License

MIT — see [LICENSE](LICENSE).
