import os
import re
from nltk.stem import PorterStemmer

def preprocess(text):
    # 基本预处理，保留文本结构
    text = text.lower()
    
    # 将连字符替换为空格，但保留其作为单词的一部分
    # 例如将 "closed-door" 变为 "closed door"
    text = re.sub(r'(\w)-(\w)', r'\1 \2', text)
    
    # 移除其他标点符号
    text = re.sub(r'[^\w\s]', '', text)
    
    return text

def parse_tdt3_sgml(content):
    docno_match = re.search(r'<DOCNO>\s*(.*?)\s*</DOCNO>', content, re.DOTALL)
    text_match = re.search(r'<TEXT>(.*?)</TEXT>', content, re.DOTALL)
    if docno_match and text_match:
        docno = docno_match.group(1).strip()
        text = text_match.group(1).strip()
        return {"docno": docno, "text": preprocess(text)}
    return None

def parse_tdt3_dataset(root_dir):
    parsed_docs = []
    for subdir in os.listdir(root_dir):
        subdir_path = os.path.join(root_dir, subdir)
        if not os.path.isdir(subdir_path):
            continue
        for file_name in os.listdir(subdir_path):
            if not file_name.endswith('.txt'):
                continue
            file_path = os.path.join(subdir_path, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                doc = parse_tdt3_sgml(content)
                if doc:
                    parsed_docs.append(doc)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
    return parsed_docs

def process_query(query_str):
    # 处理连字符和短语标记
    query_str = query_str.replace('-', '##HYPHEN##')
    
    # 提取带引号的短语（保留原始顺序）
    phrases = re.findall(r'"([^"]*)"', query_str)
    free_text = re.sub(r'"[^"]*"', '', query_str)
    
    processed_phrases = []
    for phrase in phrases:
        # 保持短语内单词顺序，仅进行必要预处理
        processed_phrase = ' '.join([
            preprocess(word).replace('##HYPHEN##', '-') 
            for word in phrase.split()
        ])
        processed_phrases.append(f'"{processed_phrase}"')
    
    # 处理自由文本部分   
    processed_free = ' '.join([
        preprocess(word).replace('##HYPHEN##', '-') 
        for word in free_text.split()
    ])
    
    # 组合处理后的查询（保留短语引号）
    final_query = ' '.join(processed_phrases + [processed_free])
    return final_query