# 信息检索系统

## 项目概述

本项目是一个基于 Python 和 Whoosh 库构建的信息检索系统。它能够对 TDT3 数据集进行索引，并支持多种查询模式，包括自由文本查询、短语查询、连字符查询以及它们的混合。系统提供了命令行界面进行索引构建和搜索，并且集成了一个基于 Flask 的简单 Web 用户界面，用于可视化搜索结果和高亮显示。此外，系统还采用了自定义的 BM25F 评分算法。

## 主要功能

-   **索引构建**：
    -   处理 TDT3 SGML 格式数据。
    -   使用 Whoosh 创建倒排索引。
    -   可通过命令行或 Web 界面触发。
-   **多样化查询**：
    -   **自由文本查询**：输入多个关键词进行搜索 (默认使用 AND 连接)。
    -   **短语查询**：使用引号 `""` 精确匹配短语，或使用下划线 `_` 连接单词作为短语。
    -   **连字符查询**：自动将查询中的连字符词（如 `closed-door`）视为一个整体或拆分为短语进行匹配。
    -   **混合查询**：支持短语、自由文本、连字符词的组合查询。
-   **结果高亮**：
    -   **命令行**：使用 ANSI 转义序列在终端对查询词进行彩色高亮。
    -   **Web 界面**：将 ANSI 高亮转换为 HTML `<span>` 标签，实现不同类型查询词的不同颜色背景高亮。
-   **自定义评分**：
    -   实现了 `CustomScorer`，继承自 Whoosh 的 `BM25F`，可进行参数调整。
-   **用户界面**：
    -   **命令行界面 (CLI)**：通过 `main.py` 执行索引和搜索操作。
    -   **Web 用户界面 (Web UI)**：通过 `app.py` 启动 Flask 应用，提供图形化搜索和索引管理入口。

## 系统架构

-   `main.py`: 命令行工具的主入口，负责解析命令、调度索引构建和执行搜索查询。包含主要的查询逻辑函数（如 `execute_query`, `free_query`, `mixed_query` 等）和结果格式化。
-   `app.py`: Flask Web 应用的入口，提供 Web 界面，处理 HTTP 请求，并调用后端搜索和索引功能。
-   `index_builder.py`: 负责索引的构建逻辑，包括读取 TDT3 数据集和使用 Whoosh API 创建索引。
-   `preprocessor.py`: 包含文本预处理函数，如 SGML 解析、文本清洗（小写化、标点移除、连字符处理）。
-   `search_engine.py`: 包含一个 `search_query` 函数，提供了另一种查询解析和执行的方式。当前系统主要依赖 `main.py` 中的查询逻辑。
-   `custom_scorer.py`: 定义了自定义的 BM25F 评分器。
-   `static/`: 存放 Web 界面的静态资源（CSS, JavaScript）。
    -   `css/style.css`: Web 界面的样式表。
    -   `js/main.js`: Web 界面的前端交互逻辑。
-   `templates/`: 存放 Flask 的 HTML 模板。
    -   `index.html`: Web 应用的主页面。
-   `indexdir/`: (默认) 存放 Whoosh 生成的索引文件。使用python main.py index命令会自动生成
-   `tdt3/`: (默认) 存放 TDT3 数据集的目录。这个需要用户自己下载

## 安装与配置

1.  **环境准备**：
    -   推荐使用 Python 3.9 或更高版本。
    -   建议使用 conda 创建并激活虚拟环境：
        ```bash
        conda create -n ir_system python=3.9
        # Windows
        conda activate ir_system
        # macOS/Linux
        conda activate ir_system
        ```
    -   或者使用 venv：
        ```bash
        python -m venv venv
        # Windows
        venv\Scripts\activate
        # macOS/Linux
        source venv/bin/activate
        ```

2.  **安装依赖**：
    -   项目根目录下应包含 `requirements.txt` 文件。
    -   运行以下命令安装所有必需的库：
        ```bash
        pip install -r requirements.txt
        ```
        主要依赖包括 `Whoosh`, `Flask`, `NLTK`, `jieba`, `scikit-learn`, `numpy`, `pandas` 等。

3.  **数据集**：
    -   将 TDT3 数据集（通常是一系列包含 `.txt` 文件的子目录）放置在项目根目录下的 `tdt3` 文件夹中，或者在构建索引时通过 Web 界面指定其他路径。

## 使用方法

### 1. 命令行界面 (CLI)

通过 `main.py` 脚本执行操作。

#### 构建索引

```bash
python main.py index
```

-   此命令会读取 `./tdt3` (默认) 目录下的数据，并在 `./indexdir` (默认) 目录中创建索引。
-   如果需要指定不同的数据目录或索引目录，请直接修改 `main.py` 中 `build_index` 函数的调用参数，或使用 Web 界面。

#### 执行搜索

```bash
python main.py search <查询字符串> [选项]
```

**查询示例**：

-   **自由文本查询** (查找同时包含 "hurricane" 和 "mitch" 的文档):
    ```bash
    python main.py search hurricane mitch
    ```

-   **短语查询** (查找精确短语 "new york city"):
    ```bash
    python main.py search "new york city"
    ```
    或者使用下划线 (在 `parse_search_args` 中处理):
    ```bash
    python main.py search new_york_city
    ```

-   **连字符查询** (查找包含 "closed-door" 的文档):
    ```bash
    python main.py search closed-door
    ```
    系统会尝试将其视为一个整体或 "closed door" 短语。

-   **混合查询** (查找包含短语 "new york city" 和关键词 "apple" 的文档):
    ```bash
    python main.py search "new york city" apple
    ```

-   **指定返回结果数量** (例如，返回前 5 个结果):
    ```bash
    python main.py search hurricane --hits=5
    ```
    或者 (如果查询字符串末尾是数字且不被解析为查询的一部分):
    ```bash
    python main.py search hurricane 5
    ```
    *(注意: `parse_search_args` 函数负责解析 `--hits` 和末尾数字。)*

**命令行高亮**：
搜索结果中的查询词会在终端中以不同颜色高亮显示（依赖终端对 ANSI 颜色的支持）。
-   红色: 短语
-   绿色: 短语中的单词
-   蓝色: 连字符词
-   黄色: 自由文本词

### 2. Web 用户界面 (Web UI)

通过 `app.py` 启动 Flask Web 服务器。

#### 启动 Web 服务

```bash
python app.py
```

-   默认情况下，服务会运行在 `http://127.0.0.1:5000/`。

#### Web 界面功能

-   **搜索**：
    -   在搜索框中输入查询内容。
    -   选择期望返回的结果数量。
    -   点击 "搜索" 按钮。
    -   结果将以卡片形式展示，查询词会以不同背景色高亮。
-   **索引管理**：
    -   可以指定 TDT3 数据集目录和索引存储目录。
    -   点击 "构建索引" 按钮来创建或更新索引。
    -   会显示索引构建的状态和结果。

**Web 界面高亮**：
-   <span style="background-color: #d4e3fc; border-radius: 3px; padding: 1px 2px;">短语高亮 (淡蓝色)</span>
-   <span style="background-color: #d8e2dc; border-radius: 3px; padding: 1px 2px;">短语中单词高亮 (莫兰迪绿)</span>
-   <span style="background-color: #cbc4d6; border-radius: 3px; padding: 1px 2px;">连字符词高亮 (莫兰迪紫)</span>
-   <span style="background-color: #f8edeb; border-radius: 3px; padding: 1px 2px;">自由词高亮 (莫兰迪粉)</span>

## 查询处理逻辑

-   `main.py` 中的 `execute_query` 函数会根据查询字符串的特征（是否包含引号、连字符）选择不同的查询策略 (`free_query`, `phrase_query`, `mixed_query`, `hyphen_query`)。
-   `mixed_query` 会先尝试使用 `AND` 连接符进行严格匹配，如果结果较少，可能会尝试使用 `OR` 连接符进行宽松匹配（具体行为取决于 `build_mixed_query_parts` 和 `execute_boolean_query` 的实现）。
-   连字符词在预处理 (`preprocessor.py`) 和查询构建时有特殊处理，通常会将其转换为短语（如 "closed-door" -> `"closed door"`）或直接作为 Term 进行索引和搜索。

## 注意事项

1.  **PowerShell 引号**：在 Windows PowerShell 中直接使用包含空格的带引号短语作为命令行参数时，引号可能被 Shell stripping。推荐使用不需要 Shell特殊处理的查询方式，例如使用下划线 `new_york_city`，或者在脚本内部有更强的引号保护逻辑。Web 界面不存在此问题。
2.  **数据集路径**：确保 TDT3 数据集按预期存放，或在构建索引时正确指定路径。
3.  **依赖版本**：`requirements.txt` 中的库版本是经过测试的，更改版本可能导致兼容性问题。
4.  **编码**：所有 Python 文件和数据文件建议使用 UTF-8 编码。

