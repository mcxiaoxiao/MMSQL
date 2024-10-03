 ![MMSQL](https://github.com/mcxiaoxiao/MMSQL/blob/main/mmsql.png)
# Evaluating and Enhancing Large Language Models for Complex Multi-Turn Text-to-SQL Conversations

This repository contains the scripts and code used for the experiments in the "Evaluating and Enhancing Large Language Models for Complex Multi-Turn Text-to-SQL Conversations" paper. The repository is structured to ensure the reproducibility of the experiments and includes scripts, notebooks, test suits, and data outputs. Some of the data used by the MMSQL dataset is generated by [QDA-SQL](https://github.com/mcxiaoxiao/QDA-SQL).

## Directory Structure
- `\datasets`: MMSQL test set `MMSQL_test.json`, MMSQL train set `MMSQL_train.json`, CoSQL dataset `cosql_dataset` (Our dataset based on its sqlite databases You can download it [here](https://drive.google.com/uc?export=download&id=1Y3ydpFiQQ3FC0bzdfy3groV95O_f1nXF) and unzip).
- `outputs/`: Directory containing various experimental output JSON files.
- `llm_generation.py`: The script generates responses using the LLM.
- `RQS_eval.py`: Script for evaluating responses using GPT-4o-mini to score RQS and label the response types.
- `ACCS_eval.py`: Script for calculating several metrics including ACCS, IACCS, EM, QM, ERROR...
- `correlation_analysis.ipynb`: Jupyter notebook for calculating the Spearman and Pearson correlations between human ratings and GPT-4o ratings.
- `analysis_outputs.ipynb`: Jupyter notebook for producing figures in a thesis.


## Getting Started

To reproduce the experiments or test your models, follow the steps below:

### 1. Generate Responses with LLM

Use the `llm_generation.py` script to generate responses for the MMSQL test set. You can choose between huggingface or api based LLMs.

```bash
python python llm_generation.py outputs/Llama-3-70B.json
```

### 2. Evaluate Responses with GPT-4o-mini

Use the `rqs_evaluation.py` script to evaluate the generated responses. The RQS scores will be added to the output JSON file in the `outputs` directory.

```bash
python RQS_eval.py outputs/Llama-3-70B.json outputs/gpt4_scored_Llama-3-70B.json
```

### 3. Calculate Metrics

Use the `accs_eval.py` script to calculate several metrics from the output JSON files, including base metric (e.g. ACCS, IACCS, EM, QM...) and analytical results.

```bash
python accs_eval.py outputs/gpt4_scored_Llama-3-70B.json
```
