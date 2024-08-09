# MMSQL: Advancing Multi-turn Text-to-SQL Evaluation with Comprehensive Dialogue Datasets and Large Language Models

This repository contains the scripts and code used for the experiments in the paper titled "MMSQL: Advancing Multi-turn Text-to-SQL Evaluation with Comprehensive Dialogue Datasets and Large Language Models". The repository is structured to ensure reproducibility of the experiments and includes various scripts, notebooks, and data outputs.

## Directory Structure

- `llm_generation.py`: Script responsible for generating responses using the LLM.
- `rqs_evaluation.py`: Script for evaluating responses using GPT-4o to score RQS.
- `process_outputs.ipynb`: Jupyter notebook for processing the output JSON files and generating plots.
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

Use the `llm_generation.py` script to generate responses for the dataset.

```bash
python llm_generation.py --input data/input.json --output outputs/llm_responses.json
```

### 4. Evaluate Responses with GPT-4o

Use the `rqs_evaluation.py` script to evaluate the generated responses.

```bash
python rqs_evaluation.py --input outputs/llm_responses.json --output outputs/rqs_scores.json
```

### 5. Process Outputs and Generate Plots

Open the `process_outputs.ipynb` notebook to process the output JSON files and generate the necessary plots.

```bash
jupyter notebook process_outputs.ipynb
```

### 6. Correlation Analysis

Open the `correlation_analysis.ipynb` notebook to calculate the Spearman and Pearson correlations between human ratings and GPT-4o ratings.

```bash
jupyter notebook correlation_analysis.ipynb
```

## File Descriptions

- `llm_generation.py`: Generates responses using the LLM based on the input dataset.
- `rqs_evaluation.py`: Evaluates the generated responses using GPT-4o to score RQS.
- `process_outputs.ipynb`: Processes the output JSON files and generates plots for analysis.
- `correlation_analysis.ipynb`: Calculates Spearman and Pearson correlations between human ratings and GPT-4o ratings.
- `outputs/`: Contains the JSON files generated from the experiments, including `llm_responses.json` and `rqs_scores.json`.

## Reproducibility

All scripts and notebooks are designed to ensure reproducibility of the experiments. Make sure to follow the steps in the order mentioned above to replicate the results presented in the paper.

## Contact

For any questions or issues, please contact [orlosziming@outlook.com](orlosziming@outlook.com).
