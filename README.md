# Creative Perceptions Experiment

Face judgment experiment built with FastAPI, SQLModel, and jsPsych. Participants rate a series of faces on different traits, then complete several survey measures.

## Survey Components

| File | Measure |
|------|---------|
| `creative-perceptions.html` | Societal Change Perceptions |
| `work-habits.html` | Work Characteristics |
| `kai-survey.html` | KAI Questionnaire |
| `big5-personality.html` | Big 5 Personality (TIPI) |
| `demographics.html` | Demographics & debrief questions |

## Setup

1. Clone this repo
2. Set up a Python environment: `python -m venv env`
3. Activate it: `source env/bin/activate`
4. Install Python packages: `pip install -r requirements.txt`
5. Install frontend packages: `python cli.py install_packages`
6. Initialize the local database: `python cli.py reset_db`
7. Add a blank `client.env` file in `frontend/`

## Run Locally

In two separate terminals:

```bash
# Terminal 1 — frontend
python cli.py debug

# Terminal 2 — backend
python cli.py run
```

Then visit: `http://localhost:8000/exp?workerId=XXX&assignmentId=XXX&hitId=XXX`

## Export Data

Export all participant trial and survey data (from local database):

```bash
python export_participant_data.py
```

This creates an `exported_data/` directory with per-participant CSVs and combined files for all participants.

Export from the remote (Railway) database:

```bash
railway run python cli.py export
```

## Deploy (Railway)

1. Create a Railway account: https://railway.app
2. Select your repo for deployment
3. Attach a Postgres database instance
4. Set environment variables (including `DATABASE_URL` pointing to the Postgres instance)
5. Link from terminal: `npm i -g @railway/cli && railway login && railway link`
