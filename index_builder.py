from whoosh.fields import Schema, ID, TEXT
from whoosh.index import create_in
from whoosh.analysis import StandardAnalyzer
from preprocessor import parse_tdt3_dataset
import os

def build_index(root_dir, index_dir):
    os.makedirs(index_dir, exist_ok=True)
    
    # 使用标准分析器，它会自动处理分词
    schema = Schema(
        docno=ID(stored=True),
        content=TEXT(stored=True)
    )
    
    ix = create_in(index_dir, schema)
    writer = ix.writer()

    docs = parse_tdt3_dataset(root_dir)
    for doc in docs:
        writer.add_document(
            docno=doc["docno"],
            content=doc["text"]
        )

    writer.commit()
    print(f"Index built successfully (Total docs: {len(docs)})")