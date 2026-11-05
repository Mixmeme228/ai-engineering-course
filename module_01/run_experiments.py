"""Real GigaChat experiments; no fabricated responses or token counts."""
import json
import os
from pathlib import Path
import llm_client as m

def main():
    if not os.getenv('GIGACHAT_CREDENTIALS'):
        raise SystemExit('Сначала настройте GIGACHAT_CREDENTIALS в .env')
    strict='Ты — строгий технический специалист. Отвечай кратко и по делу. Не выдумывай измерения.'
    mentor='Ты — терпеливый наставник. Объясняй начинающему инженеру простыми словами и с примерами.'
    cases=[('temperature_0_run_1',0.0,500,strict),('temperature_0_run_2',0.0,500,strict),
           ('temperature_1_run_1',1.0,500,strict),('temperature_1_run_2',1.0,500,strict),
           ('max_tokens_50',0.0,50,strict),('role_strict',0.0,500,strict),('role_mentor',0.0,500,mentor)]
    destination=Path(__file__).resolve().parents[1]/'evidence'/'llm_parameter_experiments.json'
    results=[]
    original=(m.TEMPERATURE,m.MAX_TOKENS,m.SYSTEM_PROMPT)
    try:
        for label,temperature,max_tokens,role in cases:
            m.TEMPERATURE,m.MAX_TOKENS,m.SYSTEM_PROMPT=temperature,max_tokens,role
            response,provider,latency=m.ask_llm(m.MY_QUESTION)
            row={'experiment':label,'temperature':temperature,'max_tokens':max_tokens,
                 'system_prompt':role,'question':m.MY_QUESTION,'provider':provider,
                 'latency_seconds':round(latency,3),**response}
            results.append(row)
            destination.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(row,ensure_ascii=False),flush=True)
    finally:
        m.TEMPERATURE,m.MAX_TOKENS,m.SYSTEM_PROMPT=original

if __name__=='__main__': main()
