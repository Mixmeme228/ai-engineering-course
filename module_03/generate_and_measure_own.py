"""Generate a separate personal corpus and measure it without overwriting reference data."""
import json
import shutil
from pathlib import Path
import generate_corpus as g
import corpus_loader as loader
import ingestion
import vector_store
from sentence_transformers import SentenceTransformer
from qdrant_connect import make_client

def main():
    g.GENERATED_DIR=g.DATA_DIR/'generated_own'
    g.CORPUS_DIR=g.DATA_DIR/'corpus_own'
    g.GENERATED_DIR.mkdir(exist_ok=True)
    g.CORPUS_DIR.mkdir(exist_ok=True)
    for source in (g.DATA_DIR/'corpus').glob('EXT-*.json'):
        shutil.copy2(source,g.CORPUS_DIR/source.name)
    cards=g.generate_cards()
    g.generate_incidents()
    g.generate_reglaments()
    incidents=json.loads((g.GENERATED_DIR/'incidents.json').read_text(encoding='utf-8'))['incidents']
    if len(cards)!=9 or len(incidents)!=12:
        raise RuntimeError(f'Неполный корпус: {len(cards)} карточек, {len(incidents)} инцидентов')
    loader.CORPUS_DIR=g.CORPUS_DIR
    documents=loader.load_documents()
    records=loader.load_records()
    ingestion.MANIFEST_PATH=g.DATA_DIR/'index_manifest_own.json'
    ingestion.CHUNK_SIZE,ingestion.OVERLAP=600,150
    model=SentenceTransformer(ingestion.MODEL_NAME)
    client=make_client(True,g.BASE_DIR/'qdrant_own')
    try:
        manifest,_=ingestion.build_index(client,model)
        doc_hits,fact_hits,total=vector_store.check_questions(client,model,ingestion.ALIAS)
        missing=[]
        for q in vector_store.QUESTIONS:
            if q['in_corpus'] and not any(q['must_contain'].casefold() in r['text'].casefold() for r in records):
                missing.append({'id':q['id'],'question':q['question'],'missing_fact':q['must_contain']})
        report={'source':'own real GigaChat generation','cards':len(cards),'incidents':len(incidents),
                'reglaments':len(list(g.GENERATED_DIR.glob('reglament_*.md'))),
                'documents':len(documents),'records':len(records),'chunks':manifest['chunks'],
                'document_hits':doc_hits,'fact_hits':fact_hits,'total':total,
                'evaluation_note':'Provided course gold set; missing facts demonstrate changed corpus coverage, not necessarily retrieval errors.',
                'questions_without_reference_fact':missing,'generation_usage':g._usage}
        out=g.BASE_DIR.parent/'evidence'/'own_corpus_measurements.json'
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:
        client.close()

if __name__=='__main__': main()
