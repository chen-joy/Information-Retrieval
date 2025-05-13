# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
import sys
import os
import re
from search_engine import search_query
from index_builder import build_index
import traceback

# 初始化Flask应用
app = Flask(__name__)

# 导入现有功能模块
from main import execute_query, format_results, parse_search_args

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """处理搜索请求"""
    try:
        # 获取查询参数
        query_str = request.form.get('query', '')
        top_n = int(request.form.get('top_n', 10))
        
        if not query_str:
            return jsonify({'error': '查询不能为空'}), 400
            
        # 执行查询
        results = execute_query(query_str, top_n)
        
        # 格式化结果为JSON友好格式
        formatted_results = []
        for res in results:
            # 将ANSI颜色代码转换为HTML标签
            snippet_html = highlight_result_filter(res['snippet'])
            
            formatted_results.append({
                'rank': res['rank'],
                'score': res['score'],
                'docno': res['docno'],
                'snippet': snippet_html  # 使用转换后的HTML
            })
            
        return jsonify({
            'query': query_str,
            'total': len(results),
            'results': formatted_results
        })
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'搜索出错: {str(e)}'}), 500

@app.route('/build_index', methods=['POST'])
def build_index_route():
    """处理索引构建请求"""
    try:
        data_dir = request.form.get('data_dir', './tdt3')
        index_dir = request.form.get('index_dir', 'indexdir')
        
        if not os.path.exists(data_dir):
            return jsonify({'error': f'数据目录不存在: {data_dir}'}), 400
            
        # 异步构建索引会更好，但这里简化处理
        build_index(data_dir, index_dir)
        
        return jsonify({'success': True, 'message': f'索引构建完成，共索引了{count_docs(index_dir)}个文档'})
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'索引构建失败: {str(e)}'}), 500

def count_docs(index_dir):
    """计算索引中的文档数量"""
    try:
        from whoosh.index import open_dir
        ix = open_dir(index_dir)
        return ix.doc_count()
    except:
        return "未知"

@app.template_filter('highlight_result')
def highlight_result_filter(text):
    """处理高亮结果，确保颜色代码在HTML中正确显示"""
    if not isinstance(text, str):
        return text
        
    # 转换ANSI颜色代码为HTML格式
    color_map = {
        '\033[31m': '<span class="highlight-phrase">',  # 红色 - 短语
        '\033[32m': '<span class="highlight-term">',    # 绿色 - 词语
        '\033[34m': '<span class="highlight-hyphen">',  # 蓝色 - 连字符
        '\033[33m': '<span class="highlight-free">',    # 黄色 - 自由词
        '\033[1m': '',                                 # 加粗忽略
        '\033[0m': '</span>'                           # 重置
    }
    
    # 处理所有颜色代码
    for ansi, html in color_map.items():
        text = text.replace(ansi, html)
    
    return text

if __name__ == '__main__':
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用静态文件缓存
    app.run(debug=True, port=5000)
