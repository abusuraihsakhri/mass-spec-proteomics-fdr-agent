# Mass Spec Proteomics FDR Agent

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Reference Guidelines & Standards:** CAP / CLSI / ISO Standards, HUPO-PSI Proteomics Standards

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Mass Spec Proteomics FDR Agent is a multi-agent evaluation platform for clinical and proteomics data analysis. It processes task payloads through specialized worker agents that evaluate metrics against reference thresholds, generating consensus dossiers with cryptographic audit trails.

The system provides two parallel evaluation pipelines:

1. **Clinical/Biomedical Pipeline** (`agents/`): Evaluates task payloads using InvariantQCWorker, SafetyEscalationWorker, and ProtocolConformanceWorker
2. **Proteomics Pipeline** (`proteomics_fdr/`): Target-Decoy search and Peptide-Spectrum Match (PSM) evaluation using HUPO-PSI Proteomics Standards

---

## ⚙️ Key Capabilities & Algorithmic Modules

- **Multi-Agent Evaluation**: Distributed worker architecture for parallel metric assessment
- **Consensus Dossier Generation**: Aggregated urgency classification from multiple workers
- **Zero-PHI Outbound Interceptor**: AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **Tamper-Evident HMAC-SHA256 Audit Trail**: Chained, cryptographically signed logs for every evaluation
- **Input Validation**: Structural validation of identifiers and file paths to prevent injection attacks
- **Path Traversal Protection**: Secure file path validation for batch operations
- **FastAPI REST API**: OpenAPI 3.1 endpoints with Prometheus telemetry (`/metrics`)
- **Batch Processing**: CSV-based high-throughput task evaluation

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/mass-spec-proteomics-fdr-agent.git
cd mass-spec-proteomics-fdr-agent

# Install dependencies
pip install fastapi uvicorn pydantic pytest

# Set required environment variable for audit trail
export AUDIT_SECRET_KEY="your-secure-minimum-16-char-key-here"
```

---

## 💻 CLI Quickstart & Usage

### 1. Single Task Evaluation
```bash
python cli.py audit --task-id TASK-001 --target TARGET-01 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### 2. Supervisory Chat
```bash
python cli.py chat "What is the system status?"
```

### 3. Batch Processing
```bash
python cli.py batch -i sample.csv -o results.csv
```

### 4. Verify Audit Trail
```bash
python cli.py verify-audit
```

### 5. Launch REST API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Parameter Reference
| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `--task-id` | str | TASK-2026-001 | Unique task/case identifier |
| `--target` | str | KEY-TARGET-01 | Target entity identifier |
| `--primary` | float | 28.5 | Primary measurement value |
| `--secondary` | float | 14.2 | Secondary metric value |
| `--critical` | flag | False | Emergency escalation flag |
| `--status` | str | DISCORDANT | Status/phenotype descriptor |

### Input Data Schema (CSV Batch)

| Field | Type | Description |
|:------|:-----|:------------|
| `task_id` | str | Unique task identifier |
| `target_identifier` | str | Target entity identifier |
| `primary_metric` | float | Primary measurement value |
| `secondary_metric` | float | Secondary metric value |
| `is_critical_flag` | bool | Emergency escalation flag |
| `status_descriptor` | str | Status code descriptor |

---

## 🛡️ Security Architecture

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, emails, DOBs, and patient names.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition. Requires `AUDIT_SECRET_KEY` environment variable (minimum 16 characters).
* **Input Validation:** All identifiers validated against injection (control characters, path traversal, special characters).
* **Path Traversal Protection:** File paths validated to prevent directory traversal attacks (`..`, `~`, null bytes).

### Required Environment Variables
| Variable | Required | Description |
|:---------|:---------|:------------|
| `AUDIT_SECRET_KEY` | Yes | HMAC-SHA256 signing key (min 16 chars) |
| `MODEL_PROVIDER` | No | LLM provider: `mock`, `ollama`, `claude`, `openai` (default: mock) |

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

```bash
docker build -t mass-spec-proteomics-fdr-agent .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY="your-production-key-here" mass-spec-proteomics-fdr-agent
```

Or using Docker Compose:

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
mass-spec-proteomics-fdr-agent/
├── agents/                    # Clinical/Biomedical evaluation pipeline
│   ├── __init__.py
│   ├── api.py                 # FastAPI REST server
│   ├── base.py                # Security, PHI guard, audit trail
│   ├── learning.py            # Bayesian calibration engine
│   ├── llm_factory.py         # LLM provider factory
│   ├── metrics.py             # Prometheus metrics collector
│   ├── models.py              # Pydantic data models
│   ├── streamer.py            # WebSocket telemetry
│   ├── supervisor.py          # Multi-agent orchestrator
│   └── workers.py             # Specialized evaluation workers
├── proteomics_fdr/            # Proteomics FDR evaluation pipeline
│   ├── __init__.py
│   ├── __main__.py           # Module entry point
│   ├── agents.py             # Sub-agent implementations
│   ├── cli.py                # CLI for proteomics pipeline
│   ├── engine.py             # Core algorithmic engine
│   ├── models.py             # Data models
│   └── server.py             # FastAPI server factory
├── tests/                     # Pytest test suite
│   ├── conftest.py           # Test configuration
│   ├── test_enrichment.py
│   ├── test_mass_spec_proteomics_fdr_agent.py
│   ├── test_proteomics_fdr.py
│   └── test_security.py      # Security-focused tests
├── web/                       # Operations console UI
├── cli.py                     # Top-level CLI entry point
├── enrichment.py              # Domain enrichment features
├── simulator.py               # High-throughput stress tester
├── pyproject.toml             # Project metadata
├── Dockerfile
└── docker-compose.yml
```

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
