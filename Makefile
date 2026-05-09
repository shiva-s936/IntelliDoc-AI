.PHONY: install run-api run-ui test lint format help

install:
	pip install -r requirements.txt

run-api:
	uvicorn api:app --host 0.0.0.0 --port 8000 --reload

run-ui:
	cd frontend && npm run dev

test:
	python -m pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .

help:
	@echo "Available targets:"
	@echo "  install   - Install Python dependencies"
	@echo "  run-api   - Start FastAPI server on port 8000"
	@echo "  run-ui    - Start React dev server on port 5173"
	@echo "  test      - Run pytest test suite"
	@echo "  lint      - Run ruff linter"
	@echo "  format    - Run ruff formatter"
