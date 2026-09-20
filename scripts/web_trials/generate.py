"""Bounded local-model contributions for three new website trials; no JS execution."""
import argparse
import json
from pathlib import Path
import sys
from hashlib import sha256

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from app.services.local_ollama import configuration, OllamaProvider
from scripts.compare_local_models import check_idle

TASKS = {
 'stamps': '''Design a Polish stamp collector's shop, synthetic demonstration.
Return JSON {concept, categories, products, logic_js}. concept: short Polish design
direction for a premium warm ivory editorial collector shop with forest-green ink.
categories: exactly 4 short Polish thematic category names of your choice.
products: exactly 18 objects {id,title,country,category,year,price,condition}.
id unique s01 through s18. country one of Polska, Japonia, Francja, Norwegia,
Wielka Brytania, Włochy; three products per country. category from your list;
year integer 1940..2000; price integer 15..400 PLN; condition short Polish.
Fictional illustrative items; do not assert genuine rarity/certification or real stock.
logic_js: strict self-contained classic JS assigning window.TrialLogic with
filterProducts(items,{country='',category='',query='',sort='featured'}={}) and
cartTotal(items,ids). Filtering country/category exact unless empty. Query
case-insensitive substring in title or country, trimmed. Sort price-asc,
price-desc, oldest (year); featured preserves order. Do not mutate input.
cartTotal sums each unique known id once, ignores unknown ids; integer prices.
No DOM, fetch, eval, storage, random, dependencies or side effects except export.
Do not claim tests passed. All four fields required. Keep JS compact.''',
 'music': '''Design a futuristic trance artist portfolio. Return JSON with
concept, tagline, sections, logic_js. Polish concept: art direction in black,
ultraviolet, ice-white with a cinematic light portal, huge typography and restrained
chrome. tagline: short English trance mood line. sections: four Polish nav labels.
logic_js: classic JS exports window.TrialLogic={scrollTime,formatTime,filterEvents}.
scrollTime(scroll,start,end,duration): finite numbers only, invalid inputs or
duration<=0 or end<=start returns 0; otherwise clamp ratio 0..1 times duration.
formatTime(seconds): floor finite nonnegative seconds, else zero; M:SS, no hours.
filterEvents(events,city): exact city match, empty city all, no mutation.
No DOM, fetch, eval, storage, dependencies. Generated movie is controlled by
native document scroll in both directions; no wheel preventDefault or focus.
Music begins only after visitor clicks Play. Demo events must not be claimed real.
Avoid invented artist history, labels, awards or real booking links.''',
 'casino': '''Design an original premium virtual-credit arcade. Return JSON with
concept, tagline, logic_js. Polish concept: dark navy, warm gold, sophisticated
casino typography, roulette, slot machine and blackjack, no real-money services.
tagline: short Polish headline. logic_js exports window.TrialLogic with:
blackjackValue(cards): cards are ranks A,2..10,J,Q,K. Return {total,soft,bust}.
A starts11 reduced to1 until <=21 or none left. soft true iff at least one ace
still11. Invalid rank throws Error. Empty hand total0 softfalse bustfalse.
roulettePayout(bet,choice,number): bet positive integer; number integer0..36;
choice red/black/even/odd. Validate or throw Error. Zero loses all choices.
Red numbers standard European:1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36.
Returns GROSS return bet*2 for win, 0 otherwise. Never subtract stake internally.
slotPayout(bet,symbols): bet positive integer; exactly3 symbols from star,diamond,
seven,cherry. Invalid throws. Three sevens gross20*bet, any other triple10*bet,
exactly one pair gross2*bet, all different0. No mutations.
No random, DOM, fetch, eval, storage or dependencies. UI will manage a single
1000-credit wallet, explicit stake deductions, no negative balance, no concurrent
games, no purchases/deposits or cash conversion. Do not claim tests passed.'''
}

def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('site',choices=TASKS);a=p.parse_args()
    root=a.output.resolve()
    if not root.is_relative_to('/home/marcin/ai-company-workspaces') or not root.is_dir():raise ValueError('Private Linux trial directory required')
    check_idle()
    config=configuration()|{'format':'json','num_predict':3600,'num_ctx':8192,'num_thread':4,'timeout_seconds':160}
    report={'site':a.site,'prompt':TASKS[a.site],'status':'started','accepted':False,'training':False}
    path=root/'evidence'/f'{a.site}-generation.json'
    if path.exists():raise ValueError('Preserve original generation')
    path.write_text(json.dumps(report))
    try:
        result=OllamaProvider(config).complete([{'role':'system','content':'Draft a bounded website component. Return valid JSON only. Never execute code or claim tests.'}, {'role':'user','content':TASKS[a.site]}])
        report['generation']=result
        data=json.loads(result['content'])
        code=data['logic_js']
        if not isinstance(code,str) or not 20<len(code)<18000 or 'TrialLogic' not in code:raise ValueError('Invalid JS contract')
        (root/a.site/'logic.js').write_text(code)
        (root/a.site/'proposal.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
        report.update(status='drafted',logic_sha256=sha256(code.encode()).hexdigest())
    finally:path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'site':a.site,'status':report['status'],'seconds':result['elapsed_seconds'],'tokens':result['eval_count']}),flush=True)

if __name__=='__main__':main()
