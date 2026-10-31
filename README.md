# GridSentinel / TrustFedGrid

GridSentinel is a research and demonstration platform for smart-meter analytics. It generates synthetic Bengaluru meter readings, trains anomaly, theft-classification and demand-forecasting models, and serves a live replay through a FastAPI application and browser dashboard. The repository also contains inspector workflows and a prototype coordinator/client workflow for federated-learning experiments.

**Treat this as a research prototype.** The default meter readings and theft labels are synthetic. CEEW data supplied for research has no verified theft labels. No score in this repository establishes real-world theft-detection accuracy, and dashboard alerts are leads for human review rather than proof of theft.

The project includes prototype research utilities for robust aggregation, trust scoring, privacy accounting, masked aggregation and audit ledgers. Their presence does not mean that the application provides end-to-end differential privacy, production secure aggregation, or a distributed blockchain. Read [implementation status](docs/IMPLEMENTATION_STATUS.md), [known limitations](docs/KNOWN_LIMITATIONS.md), and [privacy notes](docs/PRIVACY.md) before interpreting results.

## Contents

- [What the application does](#what-the-application-does)
- [Architecture and data flow](#architecture-and-data-flow)
- [Repository map](#repository-map)
- [Prerequisites](#prerequisites)
- [Install and run locally](#install-and-run-locally)
- [Generate data and models](#generate-data-and-models)
- [Configuration](#configuration)
- [Dashboard and user workflows](#dashboard-and-user-workflows)
- [HTTP API](#http-api)
- [Data and generated artifacts](#data-and-generated-artifacts)
- [Federated learning workflows](#federated-learning-workflows)
- [Optional CEEW and SGCC research](#optional-ceew-and-sgcc-research)
- [Docker](#docker)
- [Tests and evaluation](#tests-and-evaluation)
- [Limitations and security](#limitations-and-security)
- [Further documentation](#further-documentation)

## What the application does

### Smart-meter analytics

- Creates hourly synthetic readings for Bengaluru locations and usage profiles, including simulated weather, demand variation, and theft-like scenarios.
- Builds meter, pole and transformer relationships for meter-level and pole-level analysis.
- Trains an Isolation Forest anomaly detector and theft classifiers (Random Forest and XGBoost when available, with a fallback boosted classifier).
- Produces theft probabilities, anomaly indicators, risk categories, efficiency and estimated-loss measures, pole energy-balance indicators, drift summaries and human-readable prediction explanations.
- Trains LSTM and Transformer demand forecasters where the corresponding dependencies and model paths are available; fallback forecasting behavior is included.
- Replays a prepared time series in the API runtime, persists operational snapshots in SQLite, and updates the dashboard on a configurable interval.

### Operator and client workflows

- Admin login and summary views, client organization management, bounded research experiment controls, and federated update/audit views.
- Inspector accounts, area-scoped suspicious-meter views, task assignment and task completion.
- Separate client login and dashboard for organization identity, dataset metadata, federated rounds, submitted updates and trust history.
- A local CSV client agent that trains a binary logistic-regression model and sends model parameters and metadata to the coordinator. It does not upload raw meter rows.

These workflows are implemented in a primarily single-process application. They are useful for integration and research demonstrations, not a ready-made multi-utility production service.

## Architecture and data flow

```text
Synthetic generator or prepared data
        │
        ├── preprocessing and feature engineering
        ├── anomaly detection, theft classification and forecasting
        └── risk, efficiency, pole balance, explainability and drift analytics
                         │
                 FastAPI runtime (api/main.py)
                  ├── REST API and /ws/live
                  ├── SQLite operational snapshots and client registry
                  └── static HTML/CSS/JavaScript dashboards

Federated client CSV → local logistic training → signed parameter update
                                               → prototype coordinator
```

The federated client and coordinator components are separate from the centralized synthetic-meter training pipeline. All coordinator code and registered clients can still run within one application/database; this is not network-isolated federation. The central coordinator can inspect submitted parameter updates.

## Repository map

| Path | Purpose |
|---|---|
| `api/main.py` | FastAPI app, authentication, runtime loop, REST/WebSocket routes, dashboard serving and orchestration. |
| `src/` | Data generation and preprocessing, feature engineering, models, forecasting, scoring, alerts, reporting, drift, pole monitoring, investigations, security and federated research code. |
| `src/federated/` | Synthetic experiments, partitions, aggregators, attacks, trust logic, client registry/coordinator, checkpoint and ledger helpers. |
| `src/security/` | Privacy utilities, privacy accountant, reference secure-sum helper, TOTP and rate-limit adapter. These are not a complete production privacy/security stack. |
| `dashboard/` | Static front end: main operator dashboard, admin pages, inspector and client portals, reports and shared components. No Node build step is required. |
| `client_agent/` | Standalone client-side CSV training agent and its usage guide. |
| `utils/helpers.py` | Project paths, generation defaults, serialization and SQLite helpers. |
| `scripts/` | Dataset preparation, evaluation, experiment and validation command-line tools. |
| `tests/` | Pytest coverage for API, data, analytics, workflows and research components. |
| `data/raw/` | Place externally acquired raw data here; do not commit private/customer data. |
| `data/processed/` | Generated training/live datasets and normalized research inputs. |
| `data/labels/` | Provenance guidance and examples for externally sourced labeled data; no verified theft dataset is bundled. |
| `dataset/` | Generated synthetic meter dataset. |
| `models/` | Trained model files and metadata. |
| `database/` | SQLite runtime databases and local workflow state. |
| `reports/` and `maps/` | Generated PDF/JSON reports, experiment output and heatmaps. |
| `sample_outputs/` | Example API request/response payloads. |
| `docs/` | Architecture, methods, data cards, experiments, validation records, limitations and research notes. |
| `run_project.py` | Data/model/report bootstrap command; optionally starts the API. |
| `run.md` | Extended Windows PowerShell run guide. |
| `docker-compose.yml` | Local API/dashboard containers plus optional production-profile infrastructure services. |

## Prerequisites

- Python 3.11 is the version used by the Docker image and is a good local choice.
- Windows PowerShell commands below assume the repository root (the directory containing `run_project.py`). Other operating systems can use equivalent virtual-environment and environment-variable commands.
- A frontend toolchain is not required; the dashboard is static HTML, CSS and JavaScript.
- The default dataset is generated locally. Internet access and an OpenWeather key are optional; optional integrations and some model libraries may require additional packages or credentials.

## Install and run locally

### 1. Create an environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell does not allow activation, call the environment interpreter directly, for example `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, and use that interpreter for the remaining commands. Install test-only packages with `python -m pip install -r requirements-test.txt`. Install `requirements-advanced.txt` only for optional advanced workflows such as model optimization.

The requirements include substantial numerical, ML and visualization packages; installation and first model training can take time. Some forecasting/model features have fallback paths if optional model dependencies or artifacts are not available.

### 2. Configure local login and cookies

The API loads `.env` from the repository root when it starts; variables already present in the process environment take precedence. Start from `.env.example`, then replace the example admin password and session secret with your own values. Keep `.env`, credentials, client-agent secrets and private data out of version control.

For local HTTP development, set a session secret of at least 32 characters, an admin email/password, and disable secure-only cookies. For example, in PowerShell:

```powershell
$env:SMARTGRID_ADMIN_EMAIL = "admin@example.test"
$env:SMARTGRID_ADMIN_PASSWORD = "choose-a-local-password"
$env:SMARTGRID_SESSION_SECRET = (python -c "import secrets; print(secrets.token_urlsafe(48))")
$env:SMARTGRID_COOKIE_SECURE = "0"
$env:SMARTGRID_CORS_ORIGINS = "http://127.0.0.1:8000,http://localhost:8000"
```

Use the same PowerShell window to start the API so the variables are inherited. `SMARTGRID_COOKIE_SECURE=0` is only for local HTTP development; use HTTPS and secure cookies for a deployed service. Inspector accounts and federated client accounts are created through their respective admin workflows.

### 3. Generate data and models

For the default demonstration configuration (500 meters, 60 days):

```powershell
python run_project.py
```

For a smaller pipeline smoke run:

```powershell
python run_project.py --num-meters 20 --days 7 --forecast-epochs 1 --skip-report --skip-sample-export
```

The generator writes the synthetic dataset, processed training/live data and catalogs. Unless `--skip-training` is supplied, the command trains detection and forecasting models, builds the heatmap and may write report/sample artifacts. The quick run is for checking the pipeline; its scores are synthetic and are not evidence of real-world performance.

Common options:

| Option | Effect |
|---|---|
| `--num-meters N` | Override generated meter count. |
| `--days N` | Override simulated history length. |
| `--full-scale` | Select the larger 1,000-meter, 365-day configuration. Expect greater runtime and storage use. |
| `--forecast-epochs N` | Set LSTM forecasting training epochs (default 5). |
| `--skip-training` | Generate data but skip model training and downstream prediction/report workflow. |
| `--skip-report` | Skip PDF report generation. |
| `--skip-sample-export` | Skip sample API payload export. |
| `--optimize-models` | Run optional Optuna tuning before model training. |
| `--optimization-trials N` | Set tuning trial count (default 8). |
| `--start-api` | Start FastAPI after running the bootstrap with this command's settings (port 8000). |

The API startup checks for expected artifacts and can regenerate missing or mismatched defaults. A small custom generation run may therefore be replaced by default-sized artifacts when the API starts.

### 4. Start the API

Start it directly after generating artifacts:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Or bootstrap and start together with `python run_project.py --start-api`. Keep the terminal open while using the application; stop with `Ctrl+C`.

Open `http://127.0.0.1:8000/login` to sign in. The API serves the dashboard and portal assets on the same origin. Common local URLs:

- Login: `http://127.0.0.1:8000/login`
- Operator dashboard: `http://127.0.0.1:8000/dashboard/`
- Admin client management: `http://127.0.0.1:8000/dashboard/admin/clients.html`
- Inspector portal: `http://127.0.0.1:8000/inspector`
- Client portal: `http://127.0.0.1:8000/client`
- Health: `http://127.0.0.1:8000/health`
- Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`

Check health from another PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json -Depth 6
```

A degraded response indicates missing or unavailable runtime artifacts; inspect the payload and regenerate with `python run_project.py` when appropriate.

## Configuration

The main settings read by the application include:

| Variable | Default / behavior |
|---|---|
| `SMARTGRID_ADMIN_EMAIL` | Admin identity; configure for local use. |
| `SMARTGRID_ADMIN_PASSWORD` | Admin password; replace the example value. |
| `SMARTGRID_SESSION_SECRET` | Session-signing secret; at least 32 characters. |
| `SMARTGRID_COOKIE_SECURE` | Secure cookie flag; keep enabled behind HTTPS, set `0` only for local HTTP. |
| `SMARTGRID_CORS_ORIGINS` | Comma-separated exact allowed browser origins; configure to match the app origin(s). |
| `SMARTGRID_UPDATE_INTERVAL` | Live simulation tick interval in seconds; default 4. |
| `SMARTGRID_FULL_SCALE` | `1` selects larger API bootstrap generation defaults; default `0`. |
| `SMARTGRID_DEMO_MODE` | Enables demo-only behavior when set to `1`; default `0`. |
| `SMARTGRID_ENABLE_ALERTS` | Enables configured alert delivery when set to `1`; default `0`. Configure provider credentials before enabling. |
| `OPENWEATHER_API_KEY` | Optional weather integration key; simulated weather is used when unavailable. |
| `TRUSTFED_DB_PATH` | Federated client/coordinator SQLite database path (see `.env.example`). |
| `TRUSTFED_CASE_DB_PATH` | Optional investigation case database path. |

Email and Telegram settings are also listed in `.env.example`. Keep integrations disabled until their credentials and destinations are deliberately configured. Runtime SQLite tables, generated data and models are local files and need suitable persistence/backup arrangements if retained.

## Dashboard and user workflows

The main dashboard under `dashboard/` contains views for overview, live monitoring, theft detection, anomaly detection, demand forecasts, energy efficiency, pole monitoring, heatmaps, weather impact, alerts and reports. It reads API endpoints and the `/ws/live` stream. The live replay interval defaults to four seconds.

Other workflows:

- **Admin:** manage federated client organizations, start and aggregate rounds, inspect trust/audit information, review investigation records, and manage inspector accounts.
- **Inspector:** view area-filtered cases, inspect meter details, and record assigned inspection task completion.
- **Federated client:** review its organization profile, register dataset metadata, see rounds/update/trust history, and submit local model updates through the client agent.

The static dashboard can be previewed separately with `python -m http.server 8080 --directory dashboard`, but authentication and same-origin routes are intended to be used through the FastAPI-served application. For a separate origin, configure `SMARTGRID_CORS_ORIGINS` and the frontend API base deliberately.

## HTTP API

The interactive API schema at `/docs` is the authoritative request/response reference. The main route groups are:

| Routes | Purpose |
|---|---|
| `GET /health` | Runtime and artifact health. |
| `POST /auth/login`, `POST /auth/logout`, `GET /auth/session` | Admin/inspector session workflow. |
| `GET /overview`, `/meters`, `/anomalies`, `/theft`, `/weather-impact`, `/forecast`, `/risk-scores`, `/efficiency`, `/drift-report` | Operational analytics. |
| `GET /api/pole-status`, `/api/pole-tamper-alerts`, `/api/pole-energy-balance` | Pole monitoring results. |
| `POST /predict` | Score one meter reading or a list of readings using the centralized inference pipeline. |
| `GET /artifacts/daily-report`, `/artifacts/drift-report`, `/artifacts/sample-overview`, `/artifacts/heatmap` | Download generated outputs. |
| `GET /ws/live` | Authenticated live snapshot WebSocket. |
| `/api/inspectors`, `/api/inspector/*` | Inspector management and task workflow; authorization is role-scoped. |
| `/api/clients`, `/api/client/*`, `/api/federated/*`, `/api/admin/trust`, `/api/admin/audit` | Federated client portal/coordinator workflow; authorization is role-scoped. |
| `/api/admin/investigations/*`, `/api/admin/analytics/summary` | Admin investigation and summary operations. |
| `/api/research/experiments` | Bounded admin research experiment submission and result retrieval. |

Operational data and artifact routes require an authenticated session. Use `/docs` for schemas, limits and exact response fields. Prediction inputs are validated and reject unexpected fields; the numeric constraints are defined by the `MeterReading` model in `api/main.py`.

## Data and generated artifacts

### Default synthetic data

`src/data_generator.py` creates a synthetic history and live replay using Bengaluru area locations and meter profiles. Generation defaults are in `utils/helpers.py`:

| Mode | Meters | History | Sample rows | Live replay |
|---|---:|---:|---:|---:|
| Default | 500 | 60 days | 45,000 | 10 days, up to 425 meters |
| Full scale | 1,000 | 365 days | 120,000 | 14 days, up to 80 meters |

Expected outputs include:

- `dataset/smart_meter_data.csv`: full generated synthetic readings.
- `data/processed/smart_meter_sample.csv`: model training sample.
- `data/processed/live_simulation.csv`: API replay data.
- `data/processed/meter_catalog.csv`, `pole_catalog.csv`: generated entity catalogs.
- `data/processed/generation_summary.json`: generation settings and summary.
- `models/`: trained anomaly/classification/forecast artifacts and metadata.
- `database/meter_data.db`: operational simulation snapshots.
- `database/trustfed_phase2.sqlite3`: federated client, round and audit state (path configurable).
- `reports/`: PDF reports, drift reports and research result files.
- `maps/theft_heatmap.html`: generated spatial heatmap.

Generated artifacts may be regenerated by bootstrap/startup commands. Keep source datasets and important experiment outputs separately backed up when needed.

### Feature and prediction overview

Raw meter fields include voltage, current, power, consumption, power factor, weather, location, timestamp and usage profile. Preprocessing and feature engineering derive temporal consumption summaries, peak/night ratios, weather relationships, voltage/current irregularities and power gaps. Runtime enrichment adds anomaly and theft model outputs, risk and efficiency measures, estimated losses, and pole-level signals. The synthetic generator's seeded theft metadata is not used as a direct inference feature for the theft probability.

The model families and fallbacks are described in [method](docs/METHOD.md). Forecasts and classification should be interpreted within the limits of their training data and evaluation split; synthetic labels can make demo metrics look much stronger than transfer to real meters would be.

## Federated learning workflows

### In-process research simulation

`src/federated/experiment.py` supports generated classification fixtures, client partitioning, local training, FedAvg and robust/trust-oriented aggregation comparisons, and controlled simulated attacks. For example:

```powershell
python -c "from src.federated.experiment import run_experiment; result = run_experiment({'samples': 400, 'features': 10, 'clients': 4, 'rounds': 3, 'local_epochs': 2, 'partition': 'severe', 'attack': 'sign', 'seed': 42}, output_dir='reports/research_runs/smoke'); print(result['metrics'])"
python scripts/run_trust_validation.py
```

The generated fixture is not electricity data. Trust scores and HATTA are experimental heuristics; their behavior varies by attack and data distribution. The trust study report documents false accusation and missed attack cases. Do not use the score as sole evidence for punitive actions.

### Multi-client coordinator prototype

The Phase-II workflow is described in [the multi-client architecture note](docs/PHASE_II_MULTI_CLIENT_ARCHITECTURE.md). An administrator creates client organizations and a round. Each organization runs `client_agent/client_agent.py` against its local CSV and submits a signed parameter update; the coordinator then validates and aggregates accepted updates. The client agent supports a binary logistic regression baseline with shared, ordered numeric features. The coordinator stores and can inspect submitted parameter vectors; no raw CSV rows are sent by the agent.

Follow [the client agent guide](client_agent/README.md) for the exact command and feature requirements. Use HTTPS outside localhost, agree on feature names/order/units and label semantics across clients, and treat secrets as credentials. Dataset registration records metadata; it does not independently verify the dataset's contents.

This prototype is not network-isolated federation, cryptographic secure aggregation, or complete end-to-end differential privacy. The application-level federated agent path does not enforce a formal privacy budget. See the limitations documents before handling real utility data.

### Research components

Additional modules include FedProx and Multi-Krum experiment primitives, SCAFFOLD control-variate helpers, Gaussian privacy accounting utilities, pairwise-mask secure-sum reference code, checkpoint helpers and a local hash-linked ledger. Integration and guarantees vary by component. In particular, the reference secure-sum helper is not production cryptography, the local ledger is not a distributed blockchain, and the accountant does not establish application-wide DP. See [implementation updates](docs/IMPLEMENTATION_UPDATES_2026-10-30.md) and [extended validation](docs/EXTENDED_IMPLEMENTATION_AND_VALIDATION_2026-10-30.md).

## Optional CEEW and SGCC research

### CEEW consumption data

The supplied CEEW Mathura/Bareilly files support consumption profiling, forecasting and unlabeled analysis. They do not contain verified theft labels. To profile source CSVs without normalizing them:

```powershell
python scripts/prepare_ceew_dataset.py --profile-only --chunksize 200000 --output reports/research_runs/ceew_profile --input "C:\path\to\source.csv" "C:\path\to\another.csv"
```

To normalize the daily aggregates and run the documented forecast experiment, use the commands and file names in [dataset sources](docs/DATASETS.md) and [dataset card](docs/DATASET_CARD.md). High-frequency sources may be too large for the current in-memory forecast runner. The recorded CEEW results are consumption forecasting results, not theft detection; the trained approaches did not outperform the persistence baseline in the documented evaluation.

### SGCC theft dataset

No SGCC files are bundled and no SGCC benchmark was run. The loader and experiment require a separately acquired, licensed/authorized dataset. See [labeled data instructions](data/labels/README.md) and [dataset sources](docs/DATASETS.md), including provenance, licensing and validation requirements. Do not infer an Indian utility result from a Chinese dataset.

## Docker

The default Compose services run the API on port 8000 and a separate Nginx static dashboard on port 8080. The API also serves its own dashboard and authentication routes. Persistent local directories are mounted for data, database, dataset, maps, models, reports and sample outputs.

```powershell
$env:POSTGRES_PASSWORD = "use-a-long-local-secret"
docker compose up --build
```

The default Compose invocation starts the `api` and `dashboard` services. PostgreSQL, Redis and the PostgreSQL worker are under the `production` profile (`docker compose --profile production up --build`). Their presence is infrastructure scaffolding; the main application persistence and workflows are not fully migrated to PostgreSQL/Redis or a distributed worker architecture. Configure and review secrets before using any deployment profile. The container exposes the API on all interfaces; restrict network access appropriately.

## Tests and evaluation

Install test dependencies if needed, then run from the repository root:

```powershell
python -m pytest -q
```

Useful focused evaluation scripts include:

```powershell
python scripts/check_model_compatibility.py
python scripts/evaluate_theft_models.py --help
python scripts/evaluate_forecasting.py --help
python scripts/run_robustness_suite.py --help
```

Consult each script's help for required inputs and output paths. Test success covers implemented code paths; it does not prove theft label validity, real-world model performance, production security, cryptographic security or privacy guarantees. Validation reports document which checks were actually run and their limitations.

## Limitations and security

- Synthetic electricity readings and labels are used in the default end-to-end demo; they are not utility observations.
- CEEW data is unlabeled for theft. No independently verified Indian theft-labeled dataset is bundled.
- The live service, coordinator, and local databases are primarily single-process/local-development components.
- Federated client updates are visible to the coordinator; secure aggregation and end-to-end differential privacy are not implemented on the client workflow.
- Trust and poisoning scores are heuristic research signals and may penalize legitimate non-IID client behavior.
- The local hash-linked audit log is not a distributed blockchain network. Fabric chaincode under `blockchain/fabric-chaincode/` is a separate artifact and is not evidence of an integrated Fabric deployment.
- Browser controls and session checks do not replace security review, deployment hardening, TLS, CSRF defenses, centralized rate limiting, secret lifecycle management, backups or production monitoring.
- Do not use model outputs alone to accuse a customer or take enforcement action. Require evidence and human review.
- Do not commit `.env`, credentials, customer readings, dataset archives, client secrets or other private information.

## Further documentation

- [Architecture](docs/ARCHITECTURE.md) · [Method](docs/METHOD.md) · [Experiments](docs/EXPERIMENTS.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md) · [Known limitations](docs/KNOWN_LIMITATIONS.md) · [Privacy](docs/PRIVACY.md) · [Threat model](docs/THREAT_MODEL.md)
- [Dataset sources](docs/DATASETS.md) · [Dataset card](docs/DATASET_CARD.md) · [Reproducibility](docs/REPRODUCIBILITY.md)
- [Phase-II client architecture](docs/PHASE_II_MULTI_CLIENT_ARCHITECTURE.md) · [Trust validation results](docs/TRUST_VALIDATION.md)
- [Windows setup details](run.md) · [Client agent instructions](client_agent/README.md)
#   T r u s t - F e d - G r i d - X - U p d a t e d  
 