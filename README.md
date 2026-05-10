# md2anki

将 Markdown 笔记转换为 Anki 闪卡 (`.apkg`)，支持 AI 自动生成卡片。

## 快速开始

```bash
# 1. 把 .md 文件放进 src/
cp ~/notes/*.md src/

# 2. 运行（无 API Key 时会生成占位卡片）
python md2anki.py process --no-ai

# 3. 使用 AI 生成（只需设置一次 Key）
export MD2ANKI_ANTHROPIC_API_KEY=sk-...
python md2anki.py process

# 输出：out/Markdown_Notes.apkg
```

## 命令

| 命令 | 说明 |
|---|---|
| `process` | 完整流程：解析 → 渲染 → AI 生成 → 打包 |
| `list-sections` | 查看解析出的章节列表 |
| `config` | 查看当前配置 |

### process 选项

```
--deck "我的牌组"    # 自定义牌组名
--cards 5            # 每节生成几张卡片 (默认 3)
--src my_notes/      # 输入目录 (默认 src/)
--no-ai              # 跳过 AI，使用占位卡片
--model claude-sonnet-4-20250514
```

## 笔记模板

`template/` 目录下有各学科模板：

| 模板 | 适用 |
|---|---|
| `template-basic.md` | 通用笔记 |
| `template-computer.md` | 计算机 / 编程 / 算法 |
| `template-math.md` | 数学公式 / 推导 / 集合论 |
| `template-english.md` | 英语语法 / 词汇 / 句式 |
| `template-science.md` | 科学 / 生物 / 化学 |

## 卡片类型

| 类型 | 模型 | AI 何时选用 |
|---|---|---|
| concept | 概念卡片 | 纯文字解释、定义 |
| word | 拼写卡片 | 词汇、术语 |
| math | 推导链 | 公式 + 推导步骤 |
| cloze | 填空 | 句子含 `{{c1::空缺}}` |
| code | 代码输出 | 代码片段 |
| diagram | SVG 图示 | Mermaid / PlantUML / SVG |

## 依赖

- Python 3.10+
- `conda activate thesis_env`（或 `pip install -r requirements.txt`）
- Anthropic API Key（可选，用于 AI 生成）
- `mmdc` CLI（可选，用于渲染 Mermaid 图表）
