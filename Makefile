.PHONY: help up local down logs ingest chat eval test dev-install fmt

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	 awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up:  ## Build & start the stack (api + qdrant); open http://localhost:8000
	docker compose up --build

local:  ## Start the stack WITH a local Ollama model (no cloud API)
	docker compose --profile local up --build

down:  ## Stop and remove containers
	docker compose down

logs:  ## Tail the api logs
	docker compose logs -f api

ingest:  ## Re-build the vector index from knowledge_base/
	docker compose exec api python -m app.rag.ingest

chat:  ## Ask one question from the CLI, e.g. make chat Q="how does MCP help?"
	@curl -s -X POST localhost:8000/chat -H 'content-type: application/json' \
	  -d "{\"message\": \"$(Q)\", \"auto_approve\": true}" | python -m json.tool

eval:  ## Run the evaluation suite (trigger + trajectory + LLM-as-judge)
	docker compose exec api python -m app.eval.run_eval

test:  ## Run unit tests (no docker / no network needed)
	pip install -q -r requirements-dev.txt && python -m pytest -q

dev-install:  ## Install the full stack locally (for running outside docker)
	pip install -r requirements.txt
