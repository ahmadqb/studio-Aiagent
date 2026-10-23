

# Studio Inquiry Assistant (fictional test data)

An AI agent that reads a customer inquiry, looks up service information through tools,
and drafts a friendly reply. It only drafts: it never sends messages or makes bookings.

## Architecture
- SQLite table with fictional services, prices, durations, and studio info
- FastAPI endpoints: `/api/services`, `/api/service?name=...`, `/api/studio_info`
- LangGraph agent with 3 read-only tools, running on Ollama (`llama3.2`)
- Safety check: medical questions and complaints are referred to the studio team
  before the model is called

## Prerequisites
`ollama pull llama3.2`. On Linux, Ollama must be reachable from containers
(`OLLAMA_HOST=0.0.0.0`) for Docker mode.

## Run with Docker
```bash
docker compose up --build
```
Runs the four test inquiries. Another inquiry:
`docker compose run --rm agent python agent.py "Do you have lash lifting?"`

## Run locally
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python setup_db.py
uvicorn app:app --reload                                  # terminal 1
API_URL=http://localhost:8000 python agent.py --test      # terminal 2 (the 4 tests)
API_URL=http://localhost:8000 python agent.py             # interactive mode
```

## Limitations
Small local model; the keyword-based safety check is simple and may miss unusual
wording; fictional data only; drafts must be reviewed by a human.
