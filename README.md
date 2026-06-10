# Fitness Workout Tracker

FastAPI backend for a fitness/workout tracking app.

- Project: https://roadmap.sh/projects/fitness-workout-tracker
- Repo: https://github.com/trippusultan/fitness-workout-tracker

## Run

```bash
python -m venv fitness-venv
fitness-venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test

```bash
pytest -v
```

## API Docs

- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
