from whoosh.index import open_dir
from whoosh.qparser import QueryParser, PhrasePlugin
from whoosh.highlight import HtmlFormatter, ContextFragmenter, Highlighter
from custom_scorer import CustomScorer
import re

def search_query(query_str, top_n=10):
    try:
        ix = open_dir("indexdir")
        with ix.searcher(weighting=CustomScorer()) as searcher:
            # 使用完全自定义的查询构建方式
            query_builder = []
            
            # 提取短语查询
            if '"' in query_str:
                phrases = []
                # 提取所有引号内的内容
                phrase_matches = re.findall(r'"([^"]*)"', query_str)
                for phrase in phrase_matches:
                    phrases.append(phrase)
                    
                # 移除短语部分，得到自由文本
                free_text = re.sub(r'"[^"]*"', '', query_str).strip()
                
                # 先添加短语部分
                for phrase in phrases:
                    query_builder.append(f'content:"{phrase}"')
                
                # 再添加自由文本部分
                if free_text:
                    for word in free_text.split():
                        # 处理连字符词
                        if '-' in word:
                            # 整体作为一个词
                            hyphen_word = word.replace('-', ' ')
                            query_builder.append(f'content:"{hyphen_word}"')
                        else:
                            query_builder.append(f'content:{word}')
            else:
                # 只有自由文本
                for word in query_str.split():
                    # 处理连字符词
                    if '-' in word:
                        # 整体作为一个词
                        hyphen_word = word.replace('-', ' ')
                        query_builder.append(f'content:"{hyphen_word}"')
                    else:
                        query_builder.append(f'content:{word}')
            
            # 构建最终查询
            final_query = " AND ".join(query_builder)
            
            print(f"[DEBUG] Final Query: {final_query}")
            
            # 解析查询
            parser = QueryParser("content", schema=ix.schema)
            parser.add_plugin(PhrasePlugin())
            query = parser.parse(final_query)
            
            print(f"[DEBUG] Parsed Query: {query}")
            
            results = searcher.search(query, limit=top_n)
            print(f"[DEBUG] Found {len(results)} results")
            
            formatter = HtmlFormatter(tagname='b', classname='match', between='...')
            fragmenter = ContextFragmenter(surround=50)
            highlighter = Highlighter(formatter=formatter, fragmenter=fragmenter)
            
            search_results = []
            for i, hit in enumerate(results):
                try:
                    # 尝试高亮匹配的内容
                    highlighted = highlighter.highlight_hit(hit, 'content')
                    # 如果没有高亮，使用原始内容的一部分
                    if not highlighted:
                        highlighted = hit["content"][:150] + "..."
                except Exception as e:
                    print(f"Highlighting error: {e}")
                    highlighted = hit["content"][:150] + "..."
                
                search_results.append({
                    "rank": i + 1,
                    "score": round(hit.score, 4),
                    "docno": hit["docno"],
                    "snippet": highlighted
                })
            return search_results
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []