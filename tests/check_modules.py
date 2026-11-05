"""Offline contract checks. No real provider calls or fabricated experiment results."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) == 1:
    for module in ('module_01', 'module_02', 'module_03', 'module_04', 'module_05'):
        subprocess.run([sys.executable, __file__, module], check=True)
    print('All offline contract checks passed.')
    raise SystemExit()

module = sys.argv.pop()
sys.path.insert(0, str(ROOT / module))

if module == 'module_01':
    import llm_client as m
    class Checks(unittest.TestCase):
        def test_primary_does_not_use_reserve(self):
            with patch.object(m,'call_gigachat',return_value={'answer':'primary'}), patch.object(m,'call_huggingface') as backup:
                result,provider,latency=m.ask_llm('question')
                self.assertEqual((result['answer'],provider),('primary','GigaChat'))
                self.assertGreaterEqual(latency,0)
                backup.assert_not_called()
        def test_fallback_and_double_failure(self):
            with patch.object(m,'call_gigachat',side_effect=ValueError('401')), patch.object(m,'call_huggingface',return_value={'answer':'reserve'}) as backup:
                result,provider,_=m.ask_llm('same question')
                self.assertEqual((result['answer'],provider),('reserve','HuggingFace'))
                backup.assert_called_once_with('same question')
            with patch.object(m,'call_gigachat',side_effect=ValueError('401')), patch.object(m,'call_huggingface',side_effect=RuntimeError('503')):
                with self.assertRaises(RuntimeError): m.ask_llm('q')

elif module == 'module_02':
    import structured_output as m
    class Checks(unittest.TestCase):
        def test_canonical_ids(self):
            for code in ('км 101','KM-101','КМ-101'):
                raw=json.dumps({'category':'инцидент','equipment_id':code,'priority':'высокий','summary':'Остановка'},ensure_ascii=False)
                self.assertEqual(m.parse_ticket('```json\n'+raw+'\n```').equipment_id,'КМ-101')
        def test_manual_review(self):
            for raw in ('нет данных','{bad}',json.dumps({'category':'ошибка','summary':'x'}),json.dumps({'category':'инцидент','equipment_id':'ГМ-9','priority':'высокий','summary':'x'}),json.dumps({'category':'инцидент','priority':'критический','summary':'x'})):
                self.assertIsNone(m.parse_ticket(raw))
        def test_equipment_optional(self):
            ticket=m.parse_ticket(json.dumps({'category':'доступ','priority':'низкий','summary':'Права входа'}))
            self.assertIsNone(ticket.equipment_id)

elif module == 'module_03':
    import ingestion as i
    import parse_documents as p
    import generate_corpus as g
    import vector_store as v
    class Checks(unittest.TestCase):
        def test_chunk_boundaries(self):
            self.assertEqual([len(c) for c in i.chunk_text('абвгд'*100,200,50)],[200,200,200,50])
            self.assertEqual(i.chunk_text('',200,50),[])
            self.assertEqual(i.chunk_text('  \n\t',20,2),[])
            for size,overlap in ((0,0),(10,10),(10,11),(10,-1)):
                with self.assertRaises(ValueError): i.chunk_text('x',size,overlap)
        def test_pdf_cleanup_and_scan(self):
            self.assertEqual(p.clean_text('  первая\t строка  \n\n\n\n вторая  '),'первая строка\n\nвторая')
            self.assertFalse(p.has_text_layer('',0))
            self.assertFalse(p.has_text_layer('1'*399,2))
            self.assertTrue(p.has_text_layer('1'*400,2))
            self.assertEqual(p.unfilled_sources(),[])
        def test_untrusted_generation(self):
            self.assertEqual(g.validate_equipment_id('KM-101'),'КМ-101')
            self.assertIsNone(g.validate_equipment_id('ГМ-9'))
            self.assertEqual(g.extract_json_array('Ответ:\n```json\n[{"x":1}]\n```'),[{'x':1}])
            for raw in ('none','[broken]','{"x":1}'):
                self.assertIsNone(g.extract_json_array(raw))
        def test_filter(self):
            from unittest.mock import Mock
            model=Mock(); model.encode.return_value.tolist.return_value=[0.1]*384
            client=Mock(); client.query_points.return_value.points=[]
            v.search(client,model,'q','promtech',doc_type='регламент')
            condition=client.query_points.call_args.kwargs['query_filter'].must[0]
            self.assertEqual((condition.key,condition.match.value),('type','регламент'))
            v.search(client,model,'q','promtech')
            self.assertIsNone(client.query_points.call_args.kwargs['query_filter'])

elif module == 'module_04':
    import rag_assistant as r
    import evaluate_rag as e
    def hit(doc,date='',page=None,section='5.1',text='Факт',score=.8):
        return NS(score=score,payload={'doc_id':doc,'date':date,'page':page,'section':section,'text':text})
    class Checks(unittest.TestCase):
        def test_sources_and_gate(self):
            hits=[hit('REGL-GEN-01'),hit('EXT-1',page=12)]
            context=r.format_context(hits)
            self.assertIn('REGL-GEN-01, раздел 5.1',context)
            self.assertIn('EXT-1, стр. 12',context)
            self.assertIn('Факт',context)
            self.assertFalse(r.confidence_gate([]))
            self.assertFalse(r.confidence_gate([hit('x',score=.499)]))
            self.assertTrue(r.confidence_gate([hit('x',score=.5)]))
            messages=r.build_prompt('question',context)
            self.assertEqual([m['role'] for m in messages],['system','user'])
            self.assertIn(r.REFUSAL_TEXT,messages[0]['content'])
            self.assertIn(context,messages[1]['content'])
        def test_classification(self):
            q={'in_corpus':True,'expected':['DOC'],'must_contain':'1 рабочий день'}
            for answer,sources,label in ((r.REFUSAL_TEXT,[],'over_refusal'),('1 рабочий день',[],'retrieval_error'),('3 дня',['DOC'],'generation_error'),('1 РАБОЧИЙ ДЕНЬ',['DOC'],'ok')):
                self.assertEqual(e.classify(q,[],{'answer':answer,'sources':sources}),label)
            q['in_corpus']=False
            self.assertEqual(e.classify(q,[],{'answer':r.REFUSAL_TEXT,'sources':[]}), 'ok')
            self.assertEqual(e.classify(q,[],{'answer':'выдумка','sources':[]}), 'hallucination')
        def test_versions_preserve_chunks_and_unrelated_docs(self):
            hits=[hit('REGL-GEN-01-OLD','2022-01-01'),hit('CARD-X','2020'),hit('REGL-GEN-01','2024-01-10'),hit('REGL-GEN-01','2024-01-10',section='5.2')]
            self.assertEqual(e.resolve_conflicts(hits),hits[1:])
        def test_judge_failure_is_not_ok(self):
            with patch.dict('os.environ',{'GIGACHAT_CREDENTIALS':''}):
                self.assertEqual(e.llm_judge('q','c','a')['overall_verdict'],'error')
        def test_sweep_restores_baseline_on_failure(self):
            with patch.object(e,'CHUNK_COMBOS',[(1000,200)]), patch.object(e.ingestion,'build_index',return_value=({'chunks':563},[])) as build, patch.object(e,'run_eval',side_effect=RuntimeError('provider unavailable')):
                with self.assertRaises(RuntimeError): e.sweep_chunking(object(),object(),'promtech')
                self.assertEqual((e.ingestion.CHUNK_SIZE,e.ingestion.OVERLAP),(600,150))
                self.assertEqual(build.call_count,2)
        def test_judge_repairs_invalid_schema_once(self):
            valid={'answer_relevance':'high','context_relevance':'low','answer_faithfulness':'high',
                   'overall_verdict':'refusal_ok','reason':'Контекст не содержит ответа.'}
            invalid={**valid,'answer_faithfulness':'not_applicable'}
            response=lambda data:NS(choices=[NS(message=NS(content=json.dumps(data)))])
            with patch.dict('os.environ',{'GIGACHAT_CREDENTIALS':'test'}), patch.object(e,'GigaChat') as factory:
                chat=factory.return_value.__enter__.return_value.chat
                chat.side_effect=[response(invalid),response(valid)]
                self.assertEqual(e.llm_judge('q','c',r.REFUSAL_TEXT),valid)
                self.assertEqual(chat.call_count,2)

elif module == 'module_05':
    from langchain_core.messages import AIMessage,HumanMessage
    from langchain_core.runnables import RunnableLambda
    import simple_chain as s
    import rag_lcel as r
    import multi_chain as m
    class Checks(unittest.TestCase):
        def test_parser_uses_position(self):
            self.assertEqual(s.pick_category('документация, затем регламент'),'документация')
            self.assertEqual(s.pick_category('об инциденте; Категория: РЕГЛАМЕНТ.'),'регламент')
            self.assertEqual(s.pick_category('неизвестно'),'не определено')
        def test_history_does_not_mutate(self):
            history=[HumanMessage(content='1'),AIMessage(content='2'),HumanMessage(content='3'),AIMessage(content='4')]
            self.assertEqual(r.trim_history(history,3),history[2:])
            self.assertEqual(len(history),4)
            self.assertIsNot(r.trim_history(history,10),history)
            self.assertEqual(r.trim_history(history,0),[])
        def test_routes_do_not_call_model_when_unnecessary(self):
            def forbidden(x): raise AssertionError('Model must not be called')
            model=RunnableLambda(forbidden)
            chain=m.build_router_chain(model)
            self.assertEqual(chain.invoke({'question':'?'})['route'],'уточнить')
            self.assertEqual(chain.invoke({'question':'Искрит датчик насоса!'})['route'],'safety -> человеку')
            self.assertEqual(s.route_answer({'category':'не определено','question':'отпуск'},model)['action'],'специалисту')
            self.assertEqual(r.dialog_step('Что случилось с насосом НМ-205?',[],model)['standalone'],'Что случилось с насосом НМ-205?')
        def test_rule_regression(self):
            wrong=[c for c in m.CASES if ('уточнить' if len(c['question'].strip())<m.MIN_QUESTION_LEN else m.classify(c['question']))!=c['route']]
            self.assertEqual(len(wrong),1)
            self.assertIn('газету',wrong[0]['question'])
            self.assertTrue(m.mentions_equipment('KM-101 странно шумит.'))
            self.assertEqual(m.classify('переустановка приложения'),'general')
        def test_lcel_contract(self):
            model=RunnableLambda(lambda prompt: AIMessage(content='Категория: документация'))
            self.assertEqual(s.build_classify_chain(model).invoke({'question':'Паспорт насоса'}),'документация')
            condense=RunnableLambda(lambda prompt:AIMessage(content='Какая производительность насоса НМ-205?'))
            result=r.dialog_step('А у него?', [HumanMessage(content='НМ-205')],condense)
            self.assertEqual(result['standalone'],'Какая производительность насоса НМ-205?')

unittest.main(verbosity=2)
