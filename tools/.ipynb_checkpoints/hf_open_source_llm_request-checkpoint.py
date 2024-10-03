import transformers
import torch

model_id = "/mnt/nvme1n1p2/share/hf-models/Meta-Llama-3-70B-Instruct"

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
)

terminators = [
    pipeline.tokenizer.eos_token_id,
    pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>")
]

def request_llm(messages):

    outputs = pipeline(
        messages,
        max_new_tokens=256,
        eos_token_id=terminators,
        do_sample=False,
    )

    return outputs[0]["generated_text"][-1]['content']