"""Generate text-only brand holdout responses with a saved QLoRA adapter."""
import argparse
import json
from contextlib import nullcontext
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.check_sft_tokenization import SNAPSHOT
from scripts.qwen_qlora_smoke import configure


def run(adapter, exam, output):
    configure()
    import torch
    from peft import PeftModel
    from unsloth import FastModel
    base, tokenizer = FastModel.from_pretrained(model_name=str(SNAPSHOT), max_seq_length=4096,
        load_in_4bit=True, full_finetuning=False, trust_remote_code=False, local_files_only=True,
        text_only=True, offload_embedding=False, dtype=torch.bfloat16)
    if base.config.architectures is None:
        base.config.architectures=[type(base).__name__]
    model=PeftModel.from_pretrained(base,str(adapter),is_trainable=False); FastModel.for_inference(model)
    data=json.loads(Path(exam).read_text()); results=[]
    for phase, disable in (('base',True),('adapter',False)):
        for case in data['cases']:
            req=case['request']; prompt=tokenizer.apply_chat_template([
                {'role':'system','content':req['system']},{'role':'user','content':req['user']}],
                tokenize=False,add_generation_prompt=True,enable_thinking=False)
            enc=tokenizer(prompt,add_special_tokens=False,return_tensors='pt')
            with (model.disable_adapter() if disable else nullcontext()),torch.inference_mode():
                out=model.generate(**{k:v.to('cuda') for k,v in enc.items()},max_new_tokens=900,do_sample=False,
                    use_cache=True,pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
            results.append({'phase':phase,'id':case['id'],'kind':case['kind'],
                            'content':tokenizer.decode(out[0,enc['input_ids'].shape[1]:].tolist(),skip_special_tokens=True)})
    Path(output).write_text(json.dumps({'schema':'brand-text-holdout-responses.v1','exam':str(exam),'results':results},ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('adapter',type=Path);parser.add_argument('exam',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.adapter,args.exam,args.output)
