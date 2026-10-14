# JurisLink

An AI-assisted legal case intake and lawyer allocation platform. A user describes a
legal problem in plain language, the system classifies it into a legal category using
a trained NLP model, matches an eligible lawyer from the existing MongoDB dataset,
and lets the user book an available appointment slot. Lawyers get a separate
role-scoped dashboard.

**Important:** the classification is an automated routing aid, **not legal advice**.

---

## 1. Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Vite 7, JavaScript, plain CSS, React Router 7, Axios, Lucide React |
| Backend | Python 3.14, FastAPI, Uvicorn, Pydantic v2 |
| Database | MongoDB 8 (existing `jurislink` database) via PyMongo |
| NLP | scikit-learn — TF-IDF (word unigrams + bigrams) + Logistic Regression |
| Auth | JWT (PyJWT, HS256) |

---

## 2. Project structure

```
fullstack/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, lifespan, /health
│   │   ├── config.py               # env-driven settings
│   │   ├── database.py             # Mongo connection + index management
│   │   ├── dependencies/auth.py    # JWT bearer + role enforcement
│   │   ├── models/                 # Pydantic request/response models
│   │   ├── routers/                # auth, cases, lawyers, appointments, dashboard, admin
│   │   ├── services/
│   │   │   ├── classification.py   # NLP training + prediction
│   │   │   ├── lawyer_matching.py  # specialization + workload assignment
│   │   │   ├── case_service.py     # case submission/persistence
│   │   │   └── appointment_service.py  # booking + collision prevention
│   │   └── utils/                  # serialization, JWT helpers
│   ├── tests/                      # pytest suite (31 tests)
│   ├── train_model.py              # controlled (re)training CLI
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env / .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js           # axios instance + interceptors
│   │   ├── context/                # AuthContext, ToastContext
│   │   ├── components/             # Layout, ProtectedRoute, StatusBadge, …
│   │   ├── pages/                  # Login, dashboards, cases, appointments
│   │   └── styles/global.css       # design system
│   ├── package.json
│   ├── vite.config.js
│   ├── .env / .env.example
└── README.md
```

---

## 3. Prerequisites

- **Node.js** ≥ 20 (verified with v22.20.0)
- **Python** ≥ 3.11 (verified with 3.14.0)
- **MongoDB** running locally on `mongodb://localhost:27017` (verified with 8.2.5)
- The five imported collections in the `jurislink` database (see §6)

---

## 4. Verify the imported MongoDB data

The app requires these collections to already exist (it never re-imports or recreates them):

| Collection | Expected ≈ count |
| --- | --- |
| `legal_categories_temp` | 25 |
| `lawyer_temp` | 50 |
| `case_training_data_temp` | 250 |
| `case_temp` | 1 |
| `appointment_temp` | 1 |

Check from MongoDB Compass (connect to `mongodb://localhost:27017` → `jurislink`), or run:

```powershell
python -c "import pymongo; db=pymongo.MongoClient('mongodb://localhost:27017')['jurislink']; [print(c, db[c].count_documents({})) for c in ['legal_categories_temp','lawyer_temp','case_training_data_temp','case_temp','appointment_temp']]"
```

If MongoDB is not running, start it (e.g. the MongoDB service, or `mongod`). The backend
reports a clear error via `GET /health` and does **not** fall back to in-memory data.

---

## 5. Environment configuration

Both `.env.example` files document every setting. Local `.env` files are pre-filled for
local development.

`backend/.env` (the important values):

```env
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=jurislink
JWT_SECRET_KEY=<a local random secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
FRONTEND_URL=http://localhost:5173
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
DEMO_LAWYER_ID=LAW-FAM01-01
DEMO_USER_ID=demo-user
```

`DEMO_LAWYER_ID` maps the `lawyer` demo login to a real `lawyer_temp` record (see §9).

`frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## 6. Setup — backend (Windows)

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

PowerShell activation:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the API:

```bat
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Interactive docs: http://127.0.0.1:8000/docs
- Health + DB status: http://127.0.0.1:8000/health

---

## 7. Setup — frontend (Windows)

```bat
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## 8. NLP model training

The model trains automatically on first use (lazy) and at startup, and re-trains when
the training data or category mapping changes (detected via a content signature). The
model + vectorizer are cached under `backend/app/services/.model_cache/`.

To (re)train explicitly:

```bat
cd backend
python train_model.py
```

Diagnostics: `GET /admin/model-info` (training metrics, category count, signature) and
`POST /admin/retrain` (force retrain).

**Training-data mapping** (inspect before assuming — verified against the real data):

| Concern | Field used |
| --- | --- |
| Example text | `case_training_data_temp.text` |
| Label | `case_training_data_temp.category_id` |
| Category id → name | `legal_categories_temp.category_id` → `.name` |
| Lawyer specialization | `lawyer_temp.specializations` (array of `category_id`) |

Pipeline: lowercase + punctuation/whitespace normalization → TF-IDF (word unigrams +
bigrams) → multinomial Logistic Regression (`predict_proba` for confidence). Deterministic
stratified 75/25 train/test split (seed 42). On the imported 250 examples it reaches
≈ 90% accuracy / 0.90 macro-F1.

---

## 9. Demo accounts

| Role | Username | Password | Maps to |
| --- | --- | --- | --- |
| User | `user` | `user` | `user_id = demo-user` |
| Lawyer | `lawyer` | `lawyer` | `lawyer_temp.lawyer_id = LAW-FAM01-01` (configurable via `DEMO_LAWYER_ID`) |

These are hardcoded demo credentials (per spec). They are **not** a real auth store and
must not be used outside a demo. The backend is the sole source of truth for identity —
the frontend never supplies a lawyer/user id as proof of authorization.

To see cases appear on the lawyer dashboard, submit a case in the demo lawyer's
specialization (e.g. a marriage/family dispute → `FAM01`), or point `DEMO_LAWYER_ID` at
the lawyer whose specialization you want to demo.

### Seeding a sample invitation (for the demo)

To guarantee a pending invitation is waiting for the demo lawyer at the start of a
presentation, run the idempotent demo seed (creates a labelled `demo_only` FAM01 case
plus a pending invitation for `DEMO_LAWYER_ID`; re-running is a no-op):

```bat
cd backend
python seed_demo.py
```

Or, with the backend running: `POST /admin/seed-demo` (gated by `ENABLE_DEMO_ENDPOINTS`,
default `true` in local dev — set `false` in production).

### Full demo walkthrough

1. Log in as `lawyer` / `lawyer` — the dashboard shows invitation and case counts.
2. Log in as `user` / `user`, submit a marriage/family dispute (→ `FAM01`). The NLP model
   classifies it and the backend creates a **pending invitation** to the demo lawyer
   (`LAW-FAM01-01`, the deterministic lowest-workload match).
3. Log back in as `lawyer` — the invitation appears under **Invitations**.
4. Open it, review the full case, and **Accept** (or **Decline**, which re-offers it).
5. The invitation moves to *accepted* and the case appears under **Active cases**.
6. Back as `user`, the case now shows *assigned*; book an available appointment slot.
7. Back as `lawyer`, the appointment appears under **Appointments**.

---

## 10. API endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | — | DB + model health |
| POST | `/auth/login` | — | Demo login → JWT |
| GET | `/auth/me` | any | Current principal |
| POST | `/cases/demo/submit-and-classify` | user | Submit, classify, assign, persist |
| GET | `/cases/mine` | user | Current user's cases |
| GET | `/cases/assigned-to-me` | lawyer | Assigned cases |
| GET | `/cases/{case_id}` | owner/assigned | Case detail |
| PATCH | `/cases/{case_id}/status` | lawyer | Update own case status |
| GET | `/cases/{case_id}/slots` | user | Assigned lawyer's available slots |
| GET | `/lawyers/available?category_id=` | any | Eligible lawyers |
| GET | `/lawyers/me` | lawyer | Own profile |
| GET | `/lawyers/me/slots` | lawyer | Own slots + bookings |
| POST | `/appointments` | user | Book a slot |
| GET | `/appointments/mine` | user | Own appointments |
| GET | `/appointments/for-me` | lawyer | Appointments with me |
| PATCH | `/appointments/{id}/status` | any (scoped) | Status transition |
| GET | `/dashboard/user` | user | User dashboard summary |
| GET | `/dashboard/lawyer` | lawyer | Lawyer dashboard summary |
| GET | `/invitations` | lawyer | List my invitations |
| GET | `/invitations/{id}` | lawyer | Invitation detail + case |
| POST | `/invitations/{id}/accept` | lawyer | Accept a pending invitation |
| POST | `/invitations/{id}/decline` | lawyer | Decline (re-offers the case) |
| GET | `/admin/model-info` | — | NLP diagnostics |
| POST | `/admin/retrain` | — | Force retrain |
| POST | `/admin/seed-demo` | dev-gated | Idempotent demo-invitation seeding |

`POST /cases/demo/submit-and-classify` is preserved exactly as specified.

### Case invitation lifecycle

A submitted case starts as `pending_assignment`. The backend creates a **single pending
invitation** for the best eligible lawyer (specialization → workload → stable
`lawyer_id` tie-break). Accepting assigns the case (`status = assigned`); declining
re-offers it to the next eligible lawyer who has not already been invited. Invitations
carry `pending` / `accepted` / `declined` / `cancelled` statuses and are persisted in the
application-managed `case_invitation_temp` collection.

---

## 11. Data model (verified against the imported data)

Key facts discovered while inspecting the collections, and honored by the code:

- `_id` fields are **`ObjectId`** values (all responses convert them to strings via `id`).
- Case → lawyer join key is `case_temp.assigned_lawyer_id` = `lawyer_temp.lawyer_id`
  (e.g. `LAW-PRO01-01`), **not** `_id`. The backend also persists `assigned_lawyer_doc_id`
  (the lawyer's `ObjectId` as a string) for an unambiguous back-reference.
- Lawyer availability is embedded: `lawyer_temp.available_slots[]` with `{slot_id, date,
  start_time, end_time, status}`.
- New cases store: `case_id`, `user_id`, `title`, `description`, `supporting_info`,
  `preferred_date`, `predicted_category_id/name`, `prediction_confidence`, `status`,
  `assigned_lawyer_id/name`, timestamps, and optional `client_request_id`.
- New appointments store: `appointment_id`, `case_id`, `user_id`, `lawyer_id`, `slot_id`,
  `date`, `start_time`, `end_time`, `status`, `notes`, timestamps.
- **`case_invitation_temp`** (application-managed) stores case invitations:
  `invitation_id`, `case_id`, `case_title`, `case_summary`, `lawyer_id`, `lawyer_doc_id`,
  `lawyer_name`, `user_id`, `predicted_category_id/name`, `status`, `created_at`,
  `responded_at`, `decline_reason`.

Indexes are created idempotently on startup, including a **partial unique index** on
`appointment_temp.slot_id` for active statuses (prevents double-booking) and a **partial
unique index** on `case_invitation_temp.case_id` for `pending` invitations (enforces the
single-active-offer model) — both atomic guards that work without MongoDB transactions.

---

## 12. Tests

Backend (from `backend/`):

```bat
python -m pytest -q
```

Result: **43 passed**. The suite covers auth (correct/incorrect credentials, token
required, role enforcement, demo-lawyer mapping), classification (valid/empty/short text,
missing-data diagnostic), the case workflow (submit → classify → create invitation →
persist → dashboards → ownership isolation), the invitation lifecycle (accept, decline +
reassignment, cross-lawyer isolation, accept/decline conflicts), demo seeding
(idempotency, endpoint gating), and appointments (slots, booking, double-booking
rejection, cancel frees slot, cross-user isolation).

Frontend production build (from `frontend/`):

```bat
npm run build
```

Result: **builds without errors**, and `npm audit` reports **0 vulnerabilities**.

---

## 13. Security & data-integrity notes

- Secrets live in env vars only (`.env` is git-ignored in spirit; see `.env.example`).
- Demo credentials are compared with constant-time comparison and are demo-only.
- JWT bearer auth; role enforcement server-side; no user/lawyer id is trusted from the
  client.
- Users only see their own cases/appointments; lawyers only see cases assigned to their
  `lawyer_id`.
- Classification and lawyer matching run entirely on the backend.
- `ObjectId` and `datetime` values are serialized safely; internal exceptions are not
  leaked to clients (a global handler returns a clean 503 on DB errors).
- Duplicate submissions are guarded by an optional `client_request_id` (unique index).
- Double-booking is prevented by the partial unique index on `slot_id`.
- The UI labels the classification as automated and not legal advice, and never presents
  synthetic `bar_registration`/`years_experience` values as verified credentials.

---

## 14. Known limitations / manual steps

- The two accounts are hardcoded demo identities (per spec); there is no sign-up.
- The imported datasets are synthetic demo data; names repeat across specializations, so
  the UI always pairs a lawyer's name with their specialization.
- The demo lawyer (`lawyer` login) maps to a single `lawyer_temp` record
  (`LAW-FAM01-01` by default). Change `DEMO_LAWYER_ID` to demo a different specialization.
- The seed `case_temp`/`appointment_temp` records (`DEMO-CASE-001`,
  `DEMO-APPT-001`) belong to `user_id = demo-user` and `lawyer LAW-PRO01-01`; they are
  preserved untouched and are not owned by the demo lawyer account.
