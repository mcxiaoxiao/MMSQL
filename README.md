# MMSQL: Advancing Multi-turn Text-to-SQL Evaluation with Comprehensive Dialogue Datasets and Large Language Models

This repository contains the scripts and code used for the experiments in the "Evaluating and Enhancing Large Language Models for Complex Multi-Turn Text-to-SQL Conversations" paper. The repository is structured to ensure the reproducibility of the experiments and includes scripts, notebooks, test suit, and data outputs.

## Directory Structure
- `\datasets`: MMSQL test set `MMSQL_test.json`, MMSQL train set `MMSQL_train.json`, CoSQL dataset (Our dataset based on its databases) `cosql_dataset` You can download it [here](https://drive.google.com/uc?export=download&id=1Y3ydpFiQQ3FC0bzdfy3groV95O_f1nXF).
- `llm_generation.py`: Script responsible for generating responses using the LLM.
- `RQS_eval.py`: Script for evaluating responses using GPT-4o-mini to score RQS and label the response types.
- `ACCS_eval.py`: Script for calculating several metrics including ACCS, IACCS, EM, QM, ERROR...
- `analysis_outputs.ipynb`: Jupyter notebook processes the output JSON files and generates plots.
- `correlation_analysis.ipynb`: Jupyter notebook for calculating the Spearman and Pearson correlations between human ratings and GPT-4o ratings.
- `outputs/`: Directory containing various experimental output JSON files.

## Getting Started

To reproduce the experiments, follow the steps below:

### 1. Clone the Repository

```bash
git clone -b paper-experiments https://github.com/yourusername/mmsql-experiments.git
cd mmsql-experiments
```

### 2. Install Dependencies

Ensure you have Python 3.x and the required packages installed. You can install the necessary dependencies using:

```bash
pip install -r requirements.txt
```

### 3. Generate Responses with LLM

Use the `llm_generation.py` script to generate responses for the dataset. The generated responses are saved in the `outputs` directory.

```bash
python python llm_generation.py outputs/gemini1.5progen.json
```

### 4. Evaluate Responses with GPT-4o

Use the `rqs_evaluation.py` script to evaluate the generated responses. The RQS scores will be added directly to the output JSON file in the `outputs` directory.

```bash
python rqs_evaluation.py --input outputs/llm_responses.json --output outputs/rqs_scores.json
```

### 5. Calculate Metrics

Use the `accs_eval.py` script to calculate several metrics from the output JSON files, including ACCS, IACCS, EM, QM, and ERROR. The metrics will be added directly to the output JSON file in the `outputs` directory.

```bash
python accs_eval.py --input outputs/llm_responses.json --output outputs/metrics.json
```

### 6. Process Outputs and Generate Plots

Open the `process_outputs.ipynb` notebook to process the output JSON files and generate the necessary plots.

```bash
jupyter notebook process_outputs.ipynb
```

### 7. Correlation Analysis

Open the `correlation_analysis.ipynb` notebook to calculate the Spearman and Pearson correlations between human ratings and GPT-4o ratings.

```bash
jupyter notebook correlation_analysis.ipynb
```

## File Descriptions

- `llm_generation.py`: Generates responses using the LLM based on the input dataset and saves them in the `outputs` directory.
- `rqs_evaluation.py`: Evaluates the generated responses using GPT-4o to score RQS and adds the scores directly to the output JSON file in the `outputs` directory.
- `accs_eval.py`: Calculates several metrics from the output JSON files, including ACCS, IACCS, EM, QM, and ERROR, and adds the metrics directly to the output JSON file in the `outputs` directory.
- `process_outputs.ipynb`: Processes the output JSON files and generates plots for analysis.
- `correlation_analysis.ipynb`: Calculates Spearman and Pearson correlations between human ratings and GPT-4o ratings.
- `outputs/`: Contains the JSON files generated from the experiments, including `llm_responses.json`, `rqs_scores.json`, and `metrics.json`.

## Reproducibility

All scripts and notebooks are designed to ensure reproducibility of the experiments. Make sure to follow the steps in the order mentioned above to replicate the results presented in the paper.

```
