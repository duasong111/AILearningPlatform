# dify_workflow

项目里所有调 Dify Workflow API 的客户端。

## 文件清单

| 文件 | 作用 | 工作流用途 | 输入 | 输出 |
|---|---|---|---|---|
| [bili_push.py](bili_push.py) | 哔哩哔哩视频推送 | 知识点 → 推荐 B 站教学视频 | `knowledgePoints` (逗号串) | `outputs.text`: `list[dict]`,每个元素是 {index, title, duration, description, pic, bvid} |
| [kb_search.py](kb_search.py) | 知识库 top 3 检索 | 用户问题 → 知识库候选片段 | `query` (可改名) | `outputs.result`: `list[dict]`,每条 = {metadata, title, content, files, summary} |
| [quiz_generator.py](quiz_generator.py) | 题库生成 | 关键词 → 选择题 + 问答题 | `mcq_count`(int), `qa_count`(int), `search_query`(str) | 待补充（运行后记录实际结构） |


## 知识库 top 3 — 响应结构

`kb_search.py` 返回的 `outputs.result` 是一条 `list[dict]`,**长度固定 3**(工作流里设的 top_k),按 `metadata.score` 从高到低排序。每条结构:

```json
{
  "metadata": {
    "document_name": "计算机操作系统.md",        // 来自哪个 md
    "dataset_name":  "计算机网络.md...",         // 知识库名
    "score":         0.6534552466084592,         // 相似度,越大越相关
    "segment_id":    "19d9e475-...",             // 片段 ID
    "segment_position": 6,                       // 文档内片段序号
    "segment_word_count": 584,                   // 片段字数
    "retriever_from": "workflow",                // 来自工作流检索
    "doc_metadata": {
      "uploader": "2024710745@yangtzeu.edu.cn",
      "upload_date": 1781019407.0,
      "last_update_date": 1781019423.917888
    }
  },
  "title":   "计算机操作系统.md",                 // 同 metadata.document_name
  "content": "进程与线程 1. 进程 ...",            // ← 知识块正文(真正用到的字段)
  "files":   null,
  "summary": null
}
```

## 哔哩哔哩视频推送 — 响应结构

`bili_push.py` 返回的 `outputs.text` 是一条 `list[dict]`,**长度不固定** (工作流按知识点匹配出来几个就返回几个,常见 5~10 条)。`index` 字段是工作流给的排序号,不连续(可能跳号,如 [1,2,4,5,6,7,8,10])。每条结构:

```json
{
  "index":       1,                                  // 排序号,可能跳号
  "title":       "黑马Java网络编程教程, ...",         // 视频标题
  "duration":    "189:45",                            // 时长,"mm:ss" 或 "hh:mm:ss"
  "description": "黑马23年最新Java基础全套教程: ...\r\n...",  // 简介,含 \r\n
  "pic":         "//i0.hdslb.com/bfs/archive/...png", // 封面图(协议省略,前端用要补 https://)
  "bvid":        "BV1Bp4y1E7sh"                       // 视频 ID,拼 url 用 https://www.bilibili.com/video/{bvid}/
}
```

## 环境要求

```bash
pip install requests
```

## 配置 API Key

API Key 放在 `dify_workflow/.env` 里(已 `.gitignore` 忽略,不会进 git):

```ini
BILI_PUSH_API_KEY=app-xxx
KB_SEARCH_API_KEY=app-xxx
QUIZ_GENERATOR_API_KEY=app-xxx
```

两个脚本启动时会**自动**读取同目录下的 `.env`,所以直接 `python bili_push.py` 即可,无需手动 `export`。

也可以在系统环境变量里设同名变量,优先级高于 `.env`。

