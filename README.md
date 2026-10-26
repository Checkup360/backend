# Checkup360 Backend API

Core API service for **Checkup360**, built with **FastAPI**, **SQLAlchemy** (async), and **PostgreSQL**, managed by **uv**.

It coordinates unified authentication, medical user profiles, organization and department multi-tenant hierarchies, clinical health forms, consent management, audit trails, and delegation to the risk scoring microservice (`engine`).

---

## 1. Architecture

The backend strictly adheres to **Hexagonal Architecture (Ports and Adapters)** and tactical **Domain-Driven Design (DDD)**:

```text
Presentation ──> Application ──> Domain
Infrastructure ──> Application ──> Domain
Infrastructure ──────────────────> Domain
```

```
┌────────────────────────────────────────────────────────┐
│                      PRESENTATION                      │
│   FastAPI Routers, Request/Response Pydantic Models,   │
│   Dependency Composition (dependencies.py)             │
│   app/presentation/                                    │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                      APPLICATION                       │
│   Use Cases, Internal DTOs, Outbound Port Interfaces   │
│   (EmailSender, TokenProvider, UnitOfWork)             │
│   app/application/                                     │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                        DOMAIN                          │
│   Pure Entities, Value Objects, Domain Services,       │
│   Repository Interfaces, Business Rules                │
│   (100% Framework Agnostic — No FastAPI/SQLAlchemy)    │
│   app/domain/                                          │
└────────────────────────────────────────────────────────┘
                           ▲
┌──────────────────────────┴─────────────────────────────┐
│                     INFRASTRUCTURE                     │
│   SQLAlchemy Models, Concrete Repositories,            │
│   FastAPI Users, OAuth, SMTP Email, Settings           │
│   app/infrastructure/                                  │
└────────────────────────────────────────────────────────┘
```

- **Domain (`app/domain`):** Pure Python entities (`Organization`, `User`, `MemberHealthData`, `RiskScore`, `LegalDocument`), value objects, domain services, and repository contracts (`app/domain/repositories/`). Framework-independent (no FastAPI, SQLAlchemy, or HTTP imports).
- **Application (`app/application`):** Feature use cases organized under `use_cases/` (`assessments/`, `organizations/`, `consents/`, `members/`, `authentication/`), application DTOs, and outbound port contracts (`app/application/interfaces/`).
- **Infrastructure (`app/infrastructure`):** Concrete implementations of domain and application ports: async SQLAlchemy repositories (`persistence/repositories/`), ORM tables (`persistence/models/`), SMTP adapters (`email/`), and external HTTP clients (`external/engine_api_adapter.py`).
- **Presentation (`app/presentation`):** Thin HTTP controllers (`api/routers/`), request/response schemas, and the composition root (`api/dependencies.py`). Routers validate, authenticate, invoke a single Use Case, and map domain results to response DTOs.

Architectural boundaries are enforced continuously by [`tests/unit/architecture/test_dependency_rules.py`](tests/unit/architecture/test_dependency_rules.py).

---

## 2. Core Business Domains & Persistence Model

### Multi-Tenancy & Access Control
- **Organizations & Departments:** Multi-tenant hierarchy where client companies own department subdivisions and configurable risk scoring weights.
- **Memberships & RBAC:** Users hold scoped roles within an organization (`MEMBER`, `ADMIN`, `SUPERADMIN`), or platform-wide privileges (`SYSADMIN` / superuser).

### Health Data Dual Storage
To balance fast questionnaire pre-filling with clinical auditability:
1. **`member_health_data`:** Single-row active snapshot per user. Reflects their latest anthropometrics, lifestyle habits, and clinical biomarkers.
2. **`assessment_submissions`:** Append-only, immutable historical log. Records every form submission with timestamps, form versions, answers snapshot, and the associated consent record ID.

### Health Index & Scoring System
- All health indicators in Checkup360 follow the **Health Index convention (0–100, where higher is healthier)**:
  - `100`: Optimal health / lowest risk.
  - `0`: Severe health risk / critical attention.
- When an employee submits a form, the backend invokes the **Scoring Engine** microservice via `HttpEngineScoringAdapter`.
- Scores are stored in `risk_scores` (with individual `health_index`, contributing factors, and clinical attention flags) and aggregated into `member_overall_scores` (`overall_health_index`) weighted by organization-level preferences.

### Consents, Compliance & Habeas Data
- **Two-tier Consent:**
  - *Onboarding:* Terms and Conditions, Privacy Policy, and General Health Data Processing.
  - *Per-form:* Specific informed consent prior to completing any of the 9 clinical questionnaires.
- **Habeas Data & Portability:** Self-service data export endpoint (`GET /members/me/export`) allows employees to download their full medical history and consent logs in JSON format.
- **Immutable Audit Trail:** Sensitive events (consents granted/revoked, data exports, employee role changes) are appended to `audit_logs`.

---

## 3. Key API Modules

| Router Scope | File | Description |
|---|---|---|
| **`/auth`** | `auth.py` | JWT authentication, refresh tokens, Google OAuth2, password reset flows. |
| **`/members/me`** | `members.py` | Profile intake, 9 clinical forms (`biometrics`, `sleep`, `habits`, `metabolic`, `eoss`, `mood`, `nordic_nmq`, `audit_c`, `pss10`), data export. |
| **`/assessments`** | `assessments.py` | Submission inspection, immediate risk score evaluations. |
| **`/organizations`** | `organizations.py` | Tenant administration, department management, employee directory, risk weight configurations. |
| **`/consents`** | `consents.py` | Active legal documents, consent granting, and revocation. |
| **`/admin`** | `admin.py` | Platform-level sysadmin operations, global audit logs. |

Interactive API documentation is generated at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 4. Prerequisites

- **Python**: `>=3.12`
- **uv**: Fast package and virtual environment manager (`curl -Ls https://astral.sh/uv/install.sh | sh`)
- **PostgreSQL**: Running instance (e.g. on port `5432`)
- **Scoring Engine**: Running `engine` microservice (port `8001`)

---

## 5. Getting Started

### 1. Environment & Dependencies

```bash
cd backend
uv venv
uv sync
```

### 2. Environment Variables

Create your local `.env` configuration from the provided template:

```bash
cp .env.example .env
```

All configurable environment parameters are documented directly inside `.env.example`.

### 3. Database Migrations

Apply database schema migrations via Alembic:

```bash
make migrate
```
*(Equivalent to: `uv run alembic upgrade head`)*

### 4. Seed Superuser Account

Create the initial platform administrator:

```bash
uv run python scripts/seed_superuser.py
```
*(Optionally override defaults using `SUPERUSER_EMAIL` and `SUPERUSER_PASSWORD` environment variables).*

### 5. Running the Development Server

Start FastAPI with live reload:

```bash
make dev
```
*(Equivalent to: `uv run fastapi dev app/presentation/main.py --port 8000`)*

---

## 6. Testing & Code Quality

```bash
# Run unit & integration tests with coverage
make test

# Lint code (Ruff)
make lint

# Format code (Ruff)
make format

# Run pre-commit checks across all files
uv run pre-commit run --all-files
```

---

## 7. Releases

Tagging a commit with a semantic version (e.g., `git tag v0.5.4 && git push origin v0.5.4`) automatically triggers the GitHub Actions CI/CD workflow to build and publish the backend container image to GitHub Container Registry (GHCR).
