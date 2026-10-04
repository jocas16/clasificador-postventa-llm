.PHONY: install data run test dashboard clean
install:
	pip install -r requirements.txt
data:
	python scripts/generar_dummy.py --n 1000
run:
	python scripts/run_pipeline.py --datos data/raw/casos_postventa.csv --provider $(or $(PROVIDER),mock)
test:
	pytest tests -q
dashboard:
	streamlit run app_dashboard.py
clean:
	rm -rf outputs/* data/processed/* __pycache__ .pytest_cache
