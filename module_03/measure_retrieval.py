"""Reproduce the three chunking measurements without paid API calls."""
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import ingestion
import vector_store
from qdrant_connect import make_client

def main():
    model=SentenceTransformer(ingestion.MODEL_NAME)
    client=make_client(True, ingestion.DB_PATH)
    rows=[]
    try:
        baseline=vector_store.baseline_whole_documents(model)
        for size,overlap in ((1000,200),(400,100),(600,150)):
            ingestion.CHUNK_SIZE,ingestion.OVERLAP=size,overlap
            manifest,_=ingestion.build_index(client,model)
            docs,facts,total=vector_store.check_questions(client,model,ingestion.ALIAS)
            rows.append({'chunk_size':size,'overlap':overlap,'chunks':manifest['chunks'],
                         'document_hits':docs,'fact_hits':facts,'total':total})
        vector_store.threshold_report(client,model,ingestion.ALIAS)
        report={'baseline_document_hits':baseline[0],'baseline_total':baseline[1],
                'corpus':'provided reference corpus; external PDFs reparsed locally',
                'measurements':rows}
        destination=Path(__file__).resolve().parents[1]/'evidence'/'retrieval_measurements.json'
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:
        ingestion.CHUNK_SIZE,ingestion.OVERLAP=600,150
        client.close()

if __name__=='__main__': main()
