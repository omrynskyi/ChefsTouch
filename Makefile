.PHONY: dev install eval-fast eval-full

install:
	npm install
	/usr/bin/python3 -m venv apps/api/.venv
	apps/api/.venv/bin/pip install -r apps/api/requirements.txt

dev:
	npx concurrently \
		--names "web,api" \
		--prefix-colors "cyan,green" \
		"npm run dev --workspace=apps/web" \
		"apps/api/.venv/bin/uvicorn apps.api.app.main:app --reload --port 8000"

eval-fast:
	python3 -m pytest -q evals/test_e001_main_assistant_eval.py evals/test_e004_render_agent_eval.py

eval-full: eval-fast
