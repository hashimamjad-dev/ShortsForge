import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import json, time, requests, os
from pathlib import Path
from shorts_generator.stages.highlights.editorial import select_clips
texts = [
'Let us discuss how to make a reliable backup of your photographs.',
'The first step is to keep three copies: your working copy and two backups.',
'Put one backup on an external drive and another in a different location.',
'That way a broken computer or a house fire cannot destroy every copy.',
'Once a month, restore a few pictures to check that the backups really work.',
'A backup you have never tested is only a hope, so make restoration part of the routine.',
'Now a quick message from our sponsor. Buy our special storage plan today.',
'Welcome back. The next topic is why plants need light.',
'Plants use light energy to turn water and carbon dioxide into sugars.',
'Those sugars supply the energy and materials a plant needs to grow.',
'If a houseplant leans toward a window, it is growing toward the light source.',
'Rotate the pot regularly and choose a location with suitable light for that species.',
'This balances its growth without exposing shade-loving leaves to harsh direct sun.'
]
t={'duration':130,'segments':[{'start':i*10.,'end':(i+1)*10.,'text':s} for i,s in enumerate(texts)]}
metrics=[]
def llm(prompt):
 r=requests.post('http://localhost:11434/api/generate',json={'model':os.getenv('BENCHMARK_MODEL','qwen3:4b-instruct'),'prompt':prompt,'think':False,'stream':False,'format':'json','options':{'num_ctx':8192,'temperature':0.1,'num_predict':2048}},timeout=600)
 r.raise_for_status(); d=r.json(); metrics.append({k:d.get(k) for k in ['total_duration','load_duration','eval_count','eval_duration','prompt_eval_count']}); return d['response']
start=time.monotonic(); clips=select_clips(t,2,llm)
result={'model':os.getenv('BENCHMARK_MODEL','qwen3:4b-instruct'),'elapsed_seconds':time.monotonic()-start,'clips':clips,'metrics':metrics}
Path(os.getenv('BENCHMARK_OUTPUT','output/model-selection.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
