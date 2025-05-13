// 等待页面加载完成
$(document).ready(function() {
    // 绑定搜索按钮点击事件
    $('#search-button').click(function() {
        performSearch();
    });
    
    // 绑定回车键触发搜索
    $('#search-input').keypress(function(event) {
        if (event.which === 13) { // 回车键的键码
            performSearch();
        }
    });
    
    // 绑定构建索引按钮点击事件
    $('#build-index-button').click(function() {
        buildIndex();
    });
    
    // 显示初始状态
    $('#search-status').html('<p class="text-muted">请输入查询内容</p>');
});

/**
 * 执行搜索并显示结果
 */
function performSearch() {
    const query = $('#search-input').val().trim();
    const topN = $('#results-count').val();
    
    // 验证查询不为空
    if (!query) {
        $('#search-status').html('<p class="text-danger">请输入查询内容</p>');
        return;
    }
    
    // 显示加载状态
    $('#search-status').html('<div class="loader"></div><p>正在搜索...</p>');
    $('#search-results').empty();
    
    // 发送搜索请求
    $.ajax({
        url: '/search',
        type: 'POST',
        data: {
            query: query,
            top_n: topN
        },
        success: function(response) {
            // 清空状态
            $('#search-status').empty();
            
            // 显示搜索统计信息
            const resultCount = response.total;
            $('#search-status').html(
                `<p class="mb-3">查询: <strong>${query}</strong> | 共找到 <strong>${resultCount}</strong> 条结果</p>`
            );
            
            // 如果没有结果
            if (resultCount === 0) {
                $('#search-results').html('<div class="alert alert-info">未找到匹配的文档</div>');
                return;
            }
            
            // 显示搜索结果
            displayResults(response.results);
        },
        error: function(xhr) {
            const errorMessage = xhr.responseJSON?.error || '搜索请求失败';
            $('#search-status').html(`<p class="text-danger">${errorMessage}</p>`);
        }
    });
}

/**
 * 显示搜索结果
 * @param {Array} results 搜索结果数组
 */
function displayResults(results) {
    const $resultsContainer = $('#search-results');
    $resultsContainer.empty();
    
    results.forEach(result => {
        // 创建结果卡片
        const $resultCard = $('<div class="result-card"></div>');
        
        // 创建结果头部
        const $header = $('<div class="result-header"></div>');
        $header.append(`<h5>【${result.rank}】 ${result.docno}</h5>`);
        $header.append(`<span class="badge bg-secondary">相关度: ${result.score}</span>`);
        $resultCard.append($header);
        
        // 创建摘要部分
        const $snippet = $('<div class="result-snippet"></div>');
        $snippet.html(result.snippet); // 直接插入包含高亮标记的HTML
        $resultCard.append($snippet);
        
        $resultsContainer.append($resultCard);
    });
}

/**
 * 构建索引
 */
function buildIndex() {
    const dataDir = $('#data-dir').val().trim();
    const indexDir = $('#index-dir').val().trim();
    
    // 验证目录不为空
    if (!dataDir || !indexDir) {
        $('#index-status').html('<p class="text-danger">数据目录和索引目录不能为空</p>');
        return;
    }
    
    // 显示加载状态
    $('#index-status').html('<div class="loader"></div><p>正在构建索引，这可能需要几分钟时间...</p>');
    $('#build-index-button').prop('disabled', true);
    
    // 发送构建索引请求
    $.ajax({
        url: '/build_index',
        type: 'POST',
        data: {
            data_dir: dataDir,
            index_dir: indexDir
        },
        success: function(response) {
            $('#index-status').html(`<p class="text-success">${response.message}</p>`);
        },
        error: function(xhr) {
            const errorMessage = xhr.responseJSON?.error || '索引构建失败';
            $('#index-status').html(`<p class="text-danger">${errorMessage}</p>`);
        },
        complete: function() {
            $('#build-index-button').prop('disabled', false);
        }
    });
} 