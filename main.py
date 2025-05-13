import sys
import re
from search_engine import search_query
from index_builder import build_index
from whoosh.index import open_dir
from whoosh.qparser import QueryParser, PhrasePlugin
from whoosh.highlight import HtmlFormatter, ContextFragmenter, Highlighter
from custom_scorer import CustomScorer
from typing import Tuple, List, Dict
from tqdm import tqdm  # 需要安装 tqdm
from preprocessor import parse_tdt3_dataset
import traceback


class Config:
    DEFAULT_HITS = 10
    MAX_HITS = 100
    COLOR = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'phrase': '\033[91m',    # 红色
        'hyphen': '\033[94m',    # 蓝色
        'term': '\033[92m',      # 绿色
        'warning': '\033[93m'    # 黄色
    }

def main():
    """
    程序主入口点，处理命令行参数并调度索引构建或搜索功能。
    """
    if len(sys.argv) < 2:
        print("用法示例: python main.py [index|search] ...")
        return

    command = sys.argv[1]
    if command == "index":
        # 构建索引，指定 TDT3 数据集根目录和索引存储目录
        # 这里的路径是相对路径，确保 TDT3 数据集位于程序同级目录下的 tdt3 文件夹
        print("开始构建索引...")
        build_index("./tdt3", "indexdir")
        print("索引构建完成。") # 添加完成提示
    elif command == "search":
        # 执行搜索命令
        try:
            # 解析查询字符串和结果数量参数
            query_str, top_n = parse_search_args(sys.argv[2:])

            if not query_str:
                # 如果解析后查询字符串为空，打印使用方法并返回
                print("用法示例: python main.py search <查询字符串> [--hits=N]")
                return # 确保无查询字符串时程序退出

            # 执行实际搜索，调用 search_engine 模块的功能
            # execute_query 函数内部已包含了查询模式选择和 Whoosh 交互
            print(f"\n正在搜索: '{query_str}' (期望结果数: {top_n})") # 提示用户正在搜索
            results = execute_query(query_str, top_n)

            # 输出搜索结果
            print(f"\n查询: '{query_str}' (共找到 {len(results)} 个结果, 展示前 {top_n} 个)") # 修正提示信息
            if not results: # 添加判断，如果 results 为空则提示
                print("未找到匹配的文档。")
            else:
                # 循环遍历并打印每个搜索结果的详细信息
                for res in results:
                    # 使用中文标签提高可读性
                    print(f"序号: {res['rank']:02d} | 相似度得分: {res['score']:.4f} | 文档编号: {res['docno']}")
                    print(f"摘要: {res['snippet']}\n---") # 每条结果之间用 --- 分隔，更清晰
        except FileNotFoundError as e:
            print(f"错误: 索引目录不存在 → {str(e)}")
        except PermissionError as e:
            print(f"错误: 文件访问权限不足 → {str(e)}")
        except KeyboardInterrupt:
            print("\n操作已取消")
        except Exception as e:
            print(f"未预期的错误: {type(e).__name__} → {str(e)}")
            traceback.print_exc()

def parse_search_args(args: List[str]) -> Tuple[str, int]:
    """
    解析搜索参数并标准化查询格式
    
    参数:
        args (list): 命令行参数列表
        
    返回:
        tuple: (处理后的查询字符串, 结果数量)
        
    支持语法:
        - 下划线短语: new_york_city → "new york city"
        - 显式短语参数: --phrase=3 前三个词作为短语
        - 结果数指定: --hits=5 或末尾数字
    """
    # 处理普通查询
    raw_query = ' '.join(args)
    processed_query = raw_query  # 默认不变
    
    # 处理 --hits 参数
    top_n = 10
    if "--hits=" in raw_query:
        hits_match = re.search(r'--hits=(\d+)', raw_query)
        if hits_match:
            top_n = int(hits_match.group(1))
            raw_query = raw_query.replace(f"--hits={top_n}", "").strip()
            processed_query = raw_query  # 更新处理后的查询
    
    # 处理短语标记参数
    if "--phrase=" in raw_query:
        phrase_count_match = re.search(r'--phrase=(\d+)', raw_query)
        if phrase_count_match:
            count = int(phrase_count_match.group(1))
            # 移除参数本身
            raw_query = raw_query.replace(f"--phrase={count}", "").strip()
            parts = raw_query.split()
            if len(parts) >= count:
                # 将前count个词作为短语
                phrase = ' '.join(parts[:count])
                rest = ' '.join(parts[count:])
                processed_query = f'"{phrase}" {rest}'
            else:
                processed_query = raw_query
    # 处理下划线表示短语
    else:
        # 检查并识别用下划线连接的词组
        parts = []
        for term in raw_query.split():
            if '_' in term and not term.startswith('--'):  # 避免匹配选项
                phrase = term.replace('_', ' ')
                parts.append(f'"{phrase}"')
            else:
                parts.append(term)
        processed_query = ' '.join(parts)
    
    # 检查末尾数字是否是 hits 参数
    parts = processed_query.split()
    if parts and parts[-1].isdigit():
        top_n = int(parts[-1])
        processed_query = ' '.join(parts[:-1])
    
    return processed_query.strip(), top_n

def execute_query(query_str: str, top_n: int = 10) -> list:
    """
    根据查询字符串特点选择合适的查询策略
    
    Args:
        query_str: 用户输入的查询字符串
        top_n: 需要返回的结果数量
        
    Returns:
        list: 格式化后的搜索结果列表
    """
    if not query_str or not query_str.strip():
        print("[错误] 查询字符串不能为空")
        return []
    
    try:
        # 检测查询类型特征
        has_phrase = '"' in query_str
        words = query_str.replace('"', ' ').split()
        hyphen_words = [w for w in words if '-' in w]
        normal_words = [w for w in words if '-' not in w]
        
        # 根据特征选择查询策略
        if has_phrase:
            # 如果有短语，一律视为混合查询
            return mixed_query(query_str, top_n)
        elif hyphen_words:
            # 仅当只有一个连字符词且没有其他词时才使用连字符查询
            if len(hyphen_words) == 1 and len(normal_words) == 0:
                return hyphen_query(query_str, top_n, use_or=False)
            else:
                # 有连字符词但还有其他词，视为混合查询
                return mixed_query(query_str, top_n)
        else:
            # 纯自由文本查询
            return free_query(query_str, top_n)
    except Exception as e:
        print(f"[错误] 执行查询失败: {type(e).__name__} - {str(e)}")
        return []

def free_query(query_str: str, top_n: int = 10) -> list:
    """
    执行自由文本查询
    
    Args:
        query_str: 查询字符串
        top_n: 返回结果数量
        
    Returns:
        list: 格式化后的搜索结果列表
    """
    try:
        ix = open_dir("indexdir")
        with ix.searcher(weighting=CustomScorer()) as searcher:
            parser = QueryParser("content", schema=ix.schema)
            query = parser.parse(query_str)
            
            print(f"[查询模式] 自由查询: {query}")
            
            results = searcher.search(query, limit=top_n)
            print(f"[结果数量] 找到 {len(results)} 个结果")
            
            return format_results(results, query_str, query_type="free")
    except FileNotFoundError:
        print("[错误] 索引目录不存在，请先构建索引")
        return []
    except Exception as e:
        print(f"[错误] 自由查询失败: {type(e).__name__} - {str(e)}")
        return []

def phrase_query(query_str: str, top_n: int = 10) -> list:
    """
    执行短语查询
    
    Args:
        query_str: 查询字符串
        top_n: 返回结果数量
        
    Returns:
        list: 格式化后的搜索结果列表
    """
    try:
        ix = open_dir("indexdir")
        with ix.searcher(weighting=CustomScorer()) as searcher:
            parser = QueryParser("content", schema=ix.schema)
            parser.add_plugin(PhrasePlugin())
            query = parser.parse(query_str)
            
            print(f"[查询模式] 短语查询: {query}")
            
            results = searcher.search(query, limit=top_n)
            print(f"[结果数量] 找到 {len(results)} 个结果")
            
            return format_results(results, query_str, query_type="phrase")
    except FileNotFoundError:
        print("[错误] 索引目录不存在，请先构建索引")
        return []
    except Exception as e:
        print(f"[错误] 短语查询失败: {type(e).__name__} - {str(e)}")
        return []

def mixed_query(query_str: str, top_n: int = 10) -> list:
    """
    执行混合查询（短语+自由文本+连字符），同时使用AND和OR策略
    
    Args:
        query_str: 查询字符串
        top_n: 返回结果数量
        
    Returns:
        list: 格式化后的搜索结果列表
    """
    try:
        ix = open_dir("indexdir")
        with ix.searcher(weighting=CustomScorer()) as searcher:
            # 解析查询组件
            query_parts = build_mixed_query_parts(query_str)
            if not query_parts:
                print("[提示] 提取的查询组件为空，无法执行查询")
                return []
                
            # 执行AND查询（严格匹配）
            and_results = execute_boolean_query(
                searcher, query_parts, "AND", top_n, 
                "[查询模式] 混合查询(AND)", "[结果数量] 严格匹配找到"
            )
            
            # 执行OR查询（宽松匹配）
            or_results = execute_boolean_query(
                searcher, query_parts, "OR", top_n,
                "[查询模式] 混合查询(OR)", "[结果数量] 宽松匹配找到"
            )
            
            # 合并结果，优先使用AND结果
            final_results = merge_search_results(and_results, or_results, top_n)
            
            # 返回格式化后的结果
            return format_results(final_results, query_str, query_type="mixed")
    except FileNotFoundError:
        print("[错误] 索引目录不存在，请先构建索引")
        return []
    except Exception as e:
        print(f"[错误] 混合查询失败: {type(e).__name__} - {str(e)}")
        traceback.print_exc()  # 对于复杂的混合查询，打印详细错误信息
        return []

def build_mixed_query_parts(query_str: str) -> list:
    """
    从查询字符串中提取查询组件
    
    Args:
        query_str: 用户输入的查询字符串
        
    Returns:
        list: 查询组件列表
    """
    query_parts = []
    
    # 提取短语
    phrases = re.findall(r'"([^"]*)"', query_str)
    for phrase in phrases:
        if phrase.strip():
            query_parts.append(f'content:"{phrase.strip()}"')
    
    # 提取自由文本
    free_text = re.sub(r'"[^"]*"', '', query_str).strip()
    
    # 处理连字符词和自由文本词
    for word in free_text.split():
        if not word:
            continue
            
        if '-' in word:
            # 连字符词作为短语
            hyphen_word = word.replace('-', ' ').strip()
            if hyphen_word:
                query_parts.append(f'content:"{hyphen_word}"')
        elif len(word) > 2:  # 忽略太短的词
            query_parts.append(f'content:{word}')
    
    return query_parts

def execute_boolean_query(searcher, query_parts, connector, limit, mode_msg, result_msg):
    """
    使用布尔连接符执行查询
    
    Args:
        searcher: Whoosh搜索器对象
        query_parts: 查询组件列表
        connector: 连接符（AND或OR）
        limit: 结果数限制
        mode_msg: 查询模式提示
        result_msg: 结果数提示
        
    Returns:
        搜索结果
    """
    parser = QueryParser("content", schema=searcher.ixreader.schema)
    parser.add_plugin(PhrasePlugin())
    
    query_str = f" {connector} ".join(query_parts)
    query = parser.parse(query_str)
    
    print(f"{mode_msg}: {query}")
    
    results = searcher.search(query, limit=limit)
    print(f"{result_msg} {len(results)} 个结果")
    
    return results

def merge_search_results(and_results, or_results, top_n):
    """
    合并两种搜索结果，去除重复
    
    Args:
        and_results: 严格匹配结果
        or_results: 宽松匹配结果
        top_n: 需要返回的结果数量
        
    Returns:
        list: 合并后的结果列表
    """
    final_results = []
    seen_docnos = set()
    
    # 先添加严格匹配结果
    for hit in and_results:
        final_results.append(hit)
        seen_docnos.add(hit["docno"])
    
    # 补充宽松匹配结果（去重）
    remaining_slots = top_n - len(final_results)
    if remaining_slots > 0:
        for hit in or_results:
            if hit["docno"] not in seen_docnos and len(final_results) < top_n:
                final_results.append(hit)
                seen_docnos.add(hit["docno"])
    
    return final_results

def hyphen_query(query_str: str, top_n: int = 10, use_or: bool = False) -> list:
    """
    执行连字符查询
    
    Args:
        query_str: 查询字符串
        top_n: 返回结果数量
        use_or: 是否使用OR连接符（默认False，使用AND）
        
    Returns:
        list: 格式化后的搜索结果列表
    """
    try:
        ix = open_dir("indexdir")
        with ix.searcher(weighting=CustomScorer()) as searcher:
            # 分解查询
            words = query_str.split()
            query_parts = []
            
            # 记录连字符词和普通词
            hyphen_terms = []
            
            for word in words:
                if '-' in word:
                    # 连字符词作为整体短语
                    hyphen_word = word.replace('-', ' ')
                    query_parts.append(f'content:"{hyphen_word}"')
                    hyphen_terms.append(hyphen_word)
                else:
                    query_parts.append(f'content:{word}')
            
            # 使用 AND 或 OR 连接
            connector = " OR " if use_or else " AND "
            final_query_str = connector.join(query_parts)
            
            parser = QueryParser("content", schema=ix.schema)
            parser.add_plugin(PhrasePlugin())
            query = parser.parse(final_query_str)
            
            print(f"[查询模式] 连字符查询 ({connector.strip()}): {query}")
            
            results = searcher.search(query, limit=top_n)
            print(f"[结果数量] 找到 {len(results)} 个结果")
            
            # 将连字符词传递给format_results，确保高亮
            return format_results(results, query_str, query_type="hyphen", 
                                hyphen_terms=hyphen_terms)
    except FileNotFoundError:
        print("[错误] 索引目录不存在，请先构建索引")
        return []
    except Exception as e:
        print(f"[错误] 连字符查询失败: {type(e).__name__} - {str(e)}")
        return []

def format_results(results, query_str=None, query_type="free", **kwargs):
    """
    使用ANSI颜色代码高亮关键词，优先级：短语 > 连字符词 > 短语中单词 > 自由词
    
    Args:
        results: Whoosh搜索结果
        query_str: 原始查询字符串
        query_type: 查询类型（free, phrase, mixed, hyphen）
        **kwargs: 额外参数
        
    Returns:
        list: 格式化后的搜索结果列表
    """
    if not results:
        return []
        
    search_results = []
    
    # 定义ANSI颜色代码
    colors = {
        'red': '\033[31m',      # 短语用红色
        'green': '\033[32m',    # 短语中的单词用绿色
        'blue': '\033[34m',     # 连字符词用蓝色
        'yellow': '\033[33m',   # 自由词用黄色
        'bold': '\033[1m',      # 加粗
        'reset': '\033[0m'      # 重置所有样式
    }
    
    for i, hit in enumerate(results):
        try:
            # 获取文本及摘要
            content = hit.get("content", "")
            if not content:
                content = ""
                
            # 提取摘要相关信息
            snippet_data = extract_snippet(content, query_str)
            snippet = snippet_data["snippet"]
            
            # 按优先级应用高亮
            colored_snippet = apply_highlighting(snippet, query_str, query_type, colors)
            
            # 添加到结果
            search_results.append({
                "rank": i + 1,
                "score": round(hit.score, 4),
                "docno": hit["docno"],
                "snippet": colored_snippet
            })
        except Exception as e:
            print(f"[警告] 结果格式化错误: {str(e)}")
            search_results.append({
                "rank": i + 1,
                "score": round(hit.score, 4) if hasattr(hit, 'score') else 0.0,
                "docno": hit.get("docno", "unknown"),
                "snippet": content[:300] + "..." if content else "无法获取摘要"
            })
    
    return search_results

def extract_snippet(content, query_str, length=700):
    """
    从文档内容中提取包含查询词的摘要
    
    Args:
        content: 文档内容
        query_str: 查询字符串
        length: 摘要长度
        
    Returns:
        dict: 包含摘要和其他信息的字典
    """
    # 提取查询组件
    phrases = re.findall(r'"([^"]*)"', query_str)
    free_text = re.sub(r'"[^"]*"', '', query_str).strip()
    
    # 所有位置列表
    positions = []
    
    # 查找短语位置
    for phrase in phrases:
        pos = content.lower().find(phrase.lower())
        if pos != -1:
            positions.append(pos)
    
    # 查找连字符词和普通词位置
    for word in free_text.split():
        if '-' in word:
            hyphen_word = word.replace('-', ' ')
            pos = content.lower().find(hyphen_word.lower())
            if pos != -1:
                positions.append(pos)
        elif len(word) > 2:
            pos = content.lower().find(word.lower())
            if pos != -1:
                positions.append(pos)
    
    # 选择摘要位置
    if positions:
        center = sum(positions) // max(len(positions), 1)  # 避免除零错误
        start = max(0, center - length // 2)
        end = min(len(content), start + length)
        snippet = content[start:end]
    else:
        snippet = content[:length]
    
    return {
        "snippet": snippet,
        "positions": positions
    }

def apply_highlighting(snippet, query_str, query_type, colors):
    """
    按优先级应用高亮
    
    Args:
        snippet: 文本摘要
        query_str: 查询字符串
        query_type: 查询类型
        colors: 颜色代码字典
        
    Returns:
        str: 应用高亮后的摘要
    """
    # 使用标记跟踪已高亮的位置
    marked_positions = []
    snippet_processed = snippet
    
    try:
        # 1. 首先高亮完整短语 (红色，最高优先级)
        phrases = re.findall(r'"([^"]*)"', query_str)
        for phrase in phrases:
            snippet_processed = highlight_terms(
                snippet_processed, [phrase], colors['red'], colors['bold'], 
                colors['reset'], marked_positions
            )
        
        # 2. 高亮连字符词 (蓝色)
        free_text = re.sub(r'"[^"]*"', '', query_str).strip()
        hyphen_words = []
        for word in free_text.split():
            if '-' in word and len(word) > 2:
                hyphen_words.append(word.replace('-', ' '))
        
        if hyphen_words:
            snippet_processed = highlight_terms(
                snippet_processed, hyphen_words, colors['blue'], colors['bold'], 
                colors['reset'], marked_positions
            )
        
        # 3. 高亮短语中的单词(绿色)，只有在混合查询或短语查询时
        if query_type in ["mixed", "phrase"]:
            phrase_words = []
            for phrase in phrases:
                phrase_words.extend([w for w in phrase.split() if len(w) > 2])
            
            if phrase_words:
                snippet_processed = highlight_terms(
                    snippet_processed, phrase_words, colors['green'], colors['bold'], 
                    colors['reset'], marked_positions
                )
        
        # 4. 最后高亮自由文本词 (黄色)
        free_words = [w for w in free_text.split() if '-' not in w and len(w) > 2]
        if free_words:
            snippet_processed = highlight_terms(
                snippet_processed, free_words, colors['yellow'], colors['bold'], 
                colors['reset'], marked_positions
            )
        
        return snippet_processed
    except Exception as e:
        print(f"[警告] 高亮处理错误: {str(e)}")
        return snippet  # 出错时返回原始摘要

def highlight_terms(text, terms, color, bold, reset, marked_positions):
    """
    在文本中高亮指定词语
    
    Args:
        text: 要处理的文本
        terms: 要高亮的词语列表
        color: 颜色代码
        bold: 加粗代码
        reset: 重置代码
        marked_positions: 已标记位置列表
        
    Returns:
        str: 高亮后的文本
    """
    result = text
    
    for term in terms:
        if not term or len(term) <= 2:
            continue
            
        term_lower = term.lower()
        result_lower = result.lower()
        
        start_pos = 0
        while True:
            pos = result_lower.find(term_lower, start_pos)
            if pos == -1:
                break
            
            # 检查是否是单词边界且未被高亮
            if is_valid_highlight_position(result_lower, pos, len(term_lower), marked_positions):
                # 标记这个位置
                new_pos_end = pos + len(term_lower)
                marked_positions.append((pos, new_pos_end))
                
                # 提取原始大小写的文本
                original = result[pos:new_pos_end]
                # 添加颜色高亮
                colored = f"{bold}{color}{original}{reset}"
                
                # 更新文本
                result = result[:pos] + colored + result[new_pos_end:]
                
                # 更新所有标记位置（考虑添加的颜色代码长度）
                offset = len(colored) - len(original)
                marked_positions = [
                    (s + offset if s > pos else s, e + offset if e > pos else e) 
                    for s, e in marked_positions
                ]
                
                # 更新搜索起点和结果小写版本
                result_lower = result.lower()
                start_pos = pos + len(colored)
            else:
                start_pos = pos + 1
    
    return result

def is_valid_highlight_position(text, pos, length, marked_positions):
    """
    检查给定位置是否适合高亮（是单词边界且未被高亮）
    
    Args:
        text: 文本
        pos: 开始位置
        length: 词语长度
        marked_positions: 已标记位置列表
        
    Returns:
        bool: 是否适合高亮
    """
    # 检查单词边界
    is_boundary = (
        (pos == 0 or not text[pos-1].isalnum()) and
        (pos + length >= len(text) or not text[pos + length].isalnum())
    )
    
    # 检查是否与已高亮区域重叠
    not_overlapping = not any(s <= pos < e for s, e in marked_positions)
    
    return is_boundary and not_overlapping

def display_search_results(results, top_n):
    """
    格式化输出搜索结果
    
    Args:
        results: 搜索结果列表
        top_n: 显示结果数量
    """
    if not results:
        print("\n 未找到匹配文档")
        return
    
    actual_count = len(results)
    display_count = min(actual_count, top_n)
    
    print(f"\n 共找到 {actual_count} 条结果 (展示前 {display_count} 条):")
    
    for idx, res in enumerate(results, 1):
        if idx > top_n:
            break
            
        print(f"""
        [{idx:02d}] 文档编号: {res['docno']}
        相关度得分: {res['score']:.4f}
        摘要预览: {res['snippet']}
        {'━'*50}""")

def parse_arguments():
    """使用 argparse 重构命令行参数解析"""
    import argparse
    parser = argparse.ArgumentParser(description='信息检索系统')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # 索引构建子命令
    index_parser = subparsers.add_parser('index', help='构建索引')
    index_parser.add_argument('--data-dir', default='./tdt3', 
                            help='数据集路径 (默认: ./tdt3)')
    index_parser.add_argument('--index-dir', default='indexdir',
                            help='索引存储路径 (默认: indexdir)')

    # 搜索子命令
    search_parser = subparsers.add_parser('search', help='执行搜索')
    search_parser.add_argument('query', nargs='+', help='查询语句')
    search_parser.add_argument('--hits', type=int, default=Config.DEFAULT_HITS,
                             help=f'返回结果数量 (默认: {Config.DEFAULT_HITS}, 最大: {Config.MAX_HITS})',
                             choices=range(1, Config.MAX_HITS+1))  # 限制结果数范围
    search_parser.add_argument('--phrase', type=int, metavar='N',
                             help='前N个词作为短语查询')
    return parser.parse_args()

def handle_index_command(args):
    """处理索引构建命令"""
    print(f"正在从 {args.data_dir} 构建索引...")
    try:
        build_index(args.data_dir, args.index_dir)
        print(f"索引构建完成，存储于 {args.index_dir}")
    except Exception as e:
        print(f"索引构建失败: {str(e)}")
        sys.exit(1)

def handle_search_command(args):
    """处理搜索命令"""
    processed_query = process_query_args(' '.join(args.query), args.phrase)
    print(f"\n正在搜索: {processed_query} (期望结果数: {args.hits})")
    
    try:
        results = execute_query(processed_query, args.hits)
        display_search_results(results, args.hits)
    except Exception as e:
        print(f"搜索执行错误: {str(e)}")
        sys.exit(1)

def process_query_args(raw_query, phrase_length=None):
    """带校验的查询参数处理"""
    if not raw_query.strip():
        raise ValueError("查询内容不能为空")
        
    if phrase_length and phrase_length < 1:
        raise ValueError("短语长度必须为正整数")
        
    # ... 原有处理逻辑 ...
    return processed_query

def build_index(data_dir, index_dir):
    docs = parse_tdt3_dataset(data_dir)
    with tqdm(total=len(docs), desc="索引构建进度") as pbar:
        for doc in docs:
            # 处理文档...
            pbar.update(1)

if __name__ == "__main__":
    main()