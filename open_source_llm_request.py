from transformers import AutoTokenizer, AutoConfig, AddedToken
import torch
from loguru import logger
import copy


def build_prompt_chatglm3(tokenizer, query, history, system=None):
    history.append({"role": 'user', 'message': query})
    # system
    input_ids = tokenizer.get_prefix_tokens() + \
                [tokenizer.get_command(f"<|system|>")] + \
                tokenizer.encode(system, add_special_tokens=False)
    # convs
    for item in history:
        role, message = item['role'], item['message']
        if role == 'user':
            tokens = [tokenizer.get_command(f"<|user|>")] + \
                     tokenizer.encode(message, add_special_tokens=False) + \
                     [tokenizer.get_command(f"<|assistant|>")]
        else:
            tokens = tokenizer.encode(message, add_special_tokens=False) + [tokenizer.eos_token_id]
        input_ids += tokens

    return input_ids


def build_prompt(tokenizer, template,  history, system=None):
    template_name = template.template_name
    system_format = template.system_format
    user_format = template.user_format
    assistant_format = template.assistant_format
    system = system if system is not None else template.system

    if template_name == 'chatglm2':
        prompt = tokenizer.build_prompt(query, history)
        input_ids = tokenizer.encode(prompt)
    elif template_name == 'chatglm3':
        input_ids = build_prompt_chatglm3(tokenizer, query, history, system)
    else:
        input_ids = []

        # setting system information
        if system_format is not None:
            # system信息不为空
            if system is not None:
                system_text = system_format.format(content=system)
                input_ids = tokenizer.encode(system_text, add_special_tokens=False)
        # concat conversation
        for item in history:
            role, message = item['role'], item['message']
            if role == 'user':
                message = user_format.format(content=message, stop_token=tokenizer.eos_token)
            else:
                message = assistant_format.format(content=message, stop_token=tokenizer.eos_token)
            tokens = tokenizer.encode(message, add_special_tokens=False)
            input_ids += tokens
    input_ids = torch.tensor([input_ids], dtype=torch.long)

    return input_ids


def load_tokenizer(model_name_or_path):
    # config = AutoConfig.from_pretrained(model_name_or_path, trust_remote_code=True)
    # 加载tokenzier
    tokenizer = AutoTokenizer.from_pretrained(
        model_name_or_path,
        trust_remote_code=True,
        use_fast=False
        # llama不支持fast
        # use_fast=False if config.model_type == 'llama' else True
    )

    if tokenizer.__class__.__name__ == 'QWenTokenizer':
        tokenizer.pad_token_id = tokenizer.eod_id
        tokenizer.bos_token_id = tokenizer.eod_id
        tokenizer.eos_token_id = tokenizer.eod_id
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    # assert tokenizer.pad_token_id is not None, "pad_token_id should not be None"
    return tokenizer


import sys
sys.path.append("../../../")
from component.utils import ModelUtils
from component.template import template_dict
# 使用合并后的模型进行推理
# model_name_or_path = 'Qwen/Qwen-7B-Chat'
# template_name = 'qwen'
#  adapter_name_or_path = None

model_name_or_path = '/mnt/nvme1n1p2/share/hf-models/Meta-Llama-3-8B-Instruct'
template_name = 'llama3'
adapter_name_or_path = None

template = template_dict[template_name]
# 是否使用4bit进行推理，能够节省很多显存，但效果可能会有一定的下降
load_in_4bit = True
# 生成超参配置
max_new_tokens = 2048
top_p = 0.9
temperature = 0.0
repetition_penalty = 1.0

# 加载模型
logger.info(f'Loading model from: {model_name_or_path}')
logger.info(f'adapter_name_or_path: {adapter_name_or_path}')
model = ModelUtils.load_model(
    model_name_or_path,
    load_in_4bit=load_in_4bit,
    adapter_name_or_path=adapter_name_or_path
).eval()
tokenizer = load_tokenizer(model_name_or_path if adapter_name_or_path is None else adapter_name_or_path)
if template_name == 'chatglm2':
    stop_token_id = tokenizer.eos_token_id
elif template_name == 'chatglm3':
    stop_token_id = [tokenizer.eos_token_id, tokenizer.get_command("<|user|>"), tokenizer.get_command("<|observation|>")]
else:
    if template.stop_word is None:
        template.stop_word = tokenizer.eos_token
    stop_token_id = tokenizer.convert_tokens_to_ids(template.stop_word)


def process_messages(messages):
    system_message = messages[0]['content']
    filtered_messages = messages[1:]
    
    for message in filtered_messages:
        print(message)
        if 'content' in message:
            message['message'] = message.pop('content')
        
    return system_message, filtered_messages

def request_llm(message):


    system_message, history = process_messages(message)

    input_ids = build_prompt(tokenizer, template, copy.deepcopy(history), system=system_message).to(model.device)
    # outputs = model.generate(
    #     input_ids=input_ids, max_new_tokens=max_new_tokens, do_sample=False,
    #     top_p=top_p, temperature=temperature, repetition_penalty=repetition_penalty,
    #     eos_token_id=stop_token_id
    # )
    outputs = model.generate(
        input_ids=input_ids, max_new_tokens=max_new_tokens, do_sample=False, repetition_penalty=repetition_penalty,
        eos_token_id=stop_token_id
    )
    outputs = outputs.tolist()[0][len(input_ids[0]):]
    response = tokenizer.decode(outputs)
    response = response.strip().replace(template.stop_word, "").strip()
    

    # print("Output：{}".format(response))

    return "666"
