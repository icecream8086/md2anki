# md2anki — 完整使用文档

## 概述

md2anki 读取 `src/` 目录下的 Markdown 文件，按标题拆分成小节，对每节调用
Claude AI 生成结构化卡片数据，最后打包成 `.apkg` 文件导入 Anki。

```
src/*.md  ──→  解析器  ──→  章节  ──→  AI (Claude)  ──→  卡片  ──→  .apkg
                            │                          │
                            └── 渲染图表 ───────────────┘
                              (Mermaid / PlantUML → SVG)
```

---

## 安装

### 1. Python 环境

```bash
conda activate thesis_env
# 或
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 依赖说明

| 包 | 必需？ | 用途 |
|---|---|---|
| `markdown-it-py` | 是 | Markdown 解析 |
| `genanki` | 是 | Anki 打包 |
| `anthropic` | 否* | AI 生成卡片 |
| `plantuml` | 否 | PlantUML 渲染 |
| `mmdc` (npm) | 否 | Mermaid 渲染 |

\* 没有 `anthropic` SDK 或未设置 `ANTHROPIC_API_KEY` 时，会生成占位卡片。

### 3. API Key（可选）

```bash
export MD2ANKI_ANTHROPIC_API_KEY=sk-ant-...
```

或在项目根目录创建 `.env` 文件：

```
MD2ANKI_ANTHROPIC_API_KEY=sk-ant-...
MD2ANKI_ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

---

## 使用方法

### 基本流程

```bash
# 把 .md 文件放入 src/
python md2anki.py process

# 使用自定义牌组名
python md2anki.py process --deck "我的牌组"

# 每节生成更多卡片
python md2anki.py process --cards 5
```

### 离线模式（跳过 AI）

```bash
python md2anki.py process --no-ai
```

每节生成一张占位卡片，内容为该节原文前 300 字。适合测试流程或没有 API Key 时使用。

### 查看解析结果

```bash
python md2anki.py list-sections
```

以表格形式显示所有章节：文件名、行号、标题级别、文字长度、图片数、图表数。

### 查看配置

```bash
python md2anki.py config
```

---

## 输入格式

### 文件位置

`src/` 目录下所有 `.md` 文件都会被处理。**不会**递归扫描子目录。
文件按字母序排序后依次处理。

### 标题层级

标题是主要的结构划分机制：

- **H1**（`#`）→ 科目/模块标题
- **H2**（`##`）→ 章节边界（每个 H2 独立调用 AI）
- **H3**（`###`）→ 子章节（仍属于父 H2）

每个 H2 区间会独立发给 AI，因此请保持每节聚焦一个主题。

### 图表

**Mermaid**（需要安装 `mmdc`）：

    ```mermaid
    graph TD
        A-->B
    ```

**PlantUML**（需要 `plantuml` Python 包）：

    ```plantuml
    @startuml
    A -> B: message
    @enduml
    ```

渲染后的 SVG 会自动嵌入生成的卡片中。

### LaTeX 公式

行间公式：`$$ E = mc^2 $$`

行内公式：`$ax^2 + bx + c = 0$`

公式原文会保留在章节内容中，一并发送给 AI。

### 内联 HTML

原始 HTML（包括 `<svg>…</svg>`）会被保留在章节内容中。

### 图片

```markdown
![描述](image.png)
```

图片路径优先相对于 `src/` 解析，其次相对于项目根目录。
匹配到的图片会自动复制到 `out/media/` 并打包进 `.apkg`。

### 填空标记 (Cloze)

想生成语法填空卡片，在笔记中使用 Anki 填空格式：

```
The {{c1::quick}} brown {{c2::fox}} jumps over the lazy dog.
```

AI 遇到含有 `{{c1::...}}` 的章节时，会生成 **cloze** 类型卡片。

---

## 卡片类型详解

### 1. 概念卡片（`type: concept`）

| 字段 | 显示效果 |
|---|---|
| 正面 | 概念名（居中加粗） |
| 定义 | 鼠尾草绿底色块 |
| 比喻 | 淡紫灰底色块 |
| 例子 | 玫瑰粉底色块 |
| 笔记 | 浅草绿底色块 |

每个区块仅在字段非空时显示。

### 2. 拼写卡片（`type: word`）

**正面**：单词按 2–3 个字母分组，每 400ms 淡入一组。点击正面可一键全部显示。

**背面**：完整单词（大号）、音标、释义、例句。

### 3. 推导链卡片（`type: math`）

一条笔记生成 **4 张卡片**：

1. Step 1 → Step 2
2. Step 2 → Step 3
3. Step 3 → Step 4
4. Step 4 → Step 5

每张卡片正面显示当前步骤，背面显示下一步骤 + 向下箭头过渡。

### 4. 填空卡片（`type: cloze`）

标准 Anki 填空格式。`{{c1::...}}` 标记以蓝色高亮显示。
额外字段可包含语法笔记。

### 5. 代码输出卡片（`type: code`）

**正面**：深色终端风格代码块（`#1a1a2e` 背景）。

**背面**：代码块 + 输出（绿色边框）+ 文字解释。

适合预测代码输出、解释算法伪代码等场景。

### 6. 图示卡片（`type: diagram`）

内联嵌入 SVG 内容（韦恩图、流程图、动画数学步骤等）。
`svg_content` 字段接受原始 SVG 标记或 `svg_utils` 的输出。

---

## 如何写好源笔记

### 推荐写法

```
## 主题

概念简要说明。

关键细节：
- 要点 1
- 要点 2

### 子主题

更具体的内容。
```

### 避免

- 一个标题下塞多个无关主题
- 依赖 H4+ 标题（只有 H1–H3 用于分节）
- 复杂的原始 HTML 表格（虽然会保留，但 AI 可能解析不好）

### 参考模板

`template/` 目录下提供了可直接使用的模板：

- `template-basic.md` — 通用模板
- `template-computer.md` — 代码/算法/复杂度
- `template-math.md` — 公式/推导/集合论
- `template-english.md` — 词汇/语法/填空
- `template-science.md` — 定义/过程/图示

复制一份到 `src/` 后按需修改即可。

---

## 输出说明

```
out/
├── Markdown_Notes.apkg   # 导入 Anki
└── media/                # SVG 和图片（自动收集）
```

### 媒体文件大小

如果 `media/` 目录超过 100 MB，会打印警告。Anki 对过大的媒体目录
处理较慢——建议减少图片大小后再放入笔记。

---

## 配置参考

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `MD2ANKI_ANTHROPIC_API_KEY` | `""` | Anthropic API Key |
| `MD2ANKI_ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | 模型名称 |
| `MD2ANKI_SRC_DIR` | `src` | 输入目录 |
| `MD2ANKI_OUT_DIR` | `out` | 输出目录 |
| `MD2ANKI_CARDS_PER_SECTION` | `3` | 每节卡片数 |
| `MD2ANKI_MAX_SECTION_CHARS` | `4000` | 截断长章节 |
| `MD2ANKI_DECK_NAME` | `Markdown Notes` | Anki 牌组名 |
| `MD2ANKI_MERMAID_BIN` | `mmdc` | Mermaid CLI 路径 |
| `MD2ANKI_PLANTUML_RENDERING` | `python` | `python` 或 `jar` |

以上变量可从项目根目录的 `.env` 文件加载。

---

## 图表工具安装

### Mermaid

```bash
npm install -g @mermaid-js/mermaid-cli
# 验证
mmdc --version
```

### PlantUML（Python 模式）

```bash
pip install plantuml
```

### PlantUML（JAR 模式）

下载 `plantuml.jar`，然后设置：

```
MD2ANKI_PLANTUML_JAR=/path/to/plantuml.jar
MD2ANKI_PLANTUML_RENDERING=jar
```

---

## SVG 工具（`svg_utils`）

Python 函数，用于程序化生成 SVG 内容，填入图示卡片的 `svg_content` 字段。

```python
from md2anki.svg_utils import venn, animated_steps, flow_chart

# 两集合韦恩图
svg = venn([
    {"label": "A", "fill": "#2D7DD2"},
    {"label": "B", "fill": "#2A9D8F"},
])

# 动画数学步骤（逐行淡入）
svg = animated_steps([
    "y = x²",
    "dy/dx = 2x",
])

# 流程图
svg = flow_chart(
    nodes=[{"label": "开始", "x": 150, "y": 20},
           {"label": "处理", "x": 150, "y": 80}],
    edges=[(0, 1)],
)
```

输出为 SVG 标记字符串，可直接填入 `svg_content` 字段。
