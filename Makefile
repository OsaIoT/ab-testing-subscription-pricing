.PHONY: test notebooks all
NB = 01_simulated_ab_analysis 02_peeking_sequential_srm_novelty 03_uplift_modelling 04_hillstrom_real_data 05_sql_experiment_analysis

test:
	python3 -m pytest -q

notebooks:
	for nb in $(NB); do jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 notebooks/$$nb.ipynb || exit 1; done

all: test notebooks
