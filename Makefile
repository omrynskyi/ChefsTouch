.PHONY: dev install

install:
	npm install
	pip install -r apps/api/requirements.txt

dev:
	npx concurrently \
		--names "web,api" \
		--prefix-colors "cyan,green" \
		"npm run dev --workspace=apps/web" \
		"cd apps/api && uvicorn main:app --reload --port 8000"
