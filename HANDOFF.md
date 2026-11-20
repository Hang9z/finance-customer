# 金融智能客服 × 金融智脑 RAG 联调与交接文档（HANDOFF）

> 更新时间：2026-11-20  
> 适用范围：[`d:\code\finance-customer`](file:///d:/code/finance-customer)、[`D:\code\finance_brain`](file:///D:/code/finance_brain)、[`D:\code\finance-data`](file:///D:/code/finance-data)

---

## 一、三项目拓扑与启动命令

| 服务角色 | 本地路径 | 端口 | 健康检查 / 页面入口 | 启动命令 |
|---|---|---|---|---|
| 金融业务中台 (`finance-data`) | `D:\code\finance-data` | `8000` | `http://127.0.0.1:8000/health` | `Push-Location D:\code\finance-data; .\.venv\Scripts\python -m app.main` |
| 金融智脑查询服务 (`finance_brain`) | `D:\code\finance_brain` | `8001` | `http://127.0.0.1:8001/health`<br>`POST /api/v1/retrieve` | `Push-Location D:\code\finance_brain; .\.venv\Scripts\python api/query_service.py` |
| 金融智脑文档导入服务 (`finance_brain`) | `D:\code\finance_brain` | `8002` | `http://127.0.0.1:8002/health`<br>`http://127.0.0.1:8002/import.html` | `Push-Location D:\code\finance_brain; .\.venv\Scripts\python api/file_import_service.py` |
| 金融客服后端 (`finance-customer`) | `d:\code\finance-customer` | `18082` | `http://127.0.0.1:18082/docs`<br>`GET /api/rag/status` | `Push-Location d:\code\finance-customer; .\.venv\Scripts\python main.py` |
| 金融客服前端 (`Vite + React`) | `d:\code\finance-customer\frontend` | `5173` | `http://127.0.0.1:5173/` | `Push-Location d:\code\finance-customer\frontend; npm run dev` |

- **外部基础设施（虚拟机 `192.168.100.133`）**：
  - Milvus：`http://192.168.100.133:19530`（切片集合 `finance_chunks`，主体集合 `finance_item_names`）
  - MongoDB：`mongodb://192.168.100.133:27017`（数据库 `finance_kb`）
  - MinIO：`192.168.100.133:9000`（桶 `knowledge-base-files`）

---

## 二、已完成的功能演进

### 1. 金融客服主干能力（`d:\code\finance-customer`）
1. **账号与卡号互通 + 查询闭环**：支持 `6222...` 银行卡号、`ACC...` 账户号及 4 位尾号自动解析，补齐账户余额、交易流水、贷款审批进度（`loan_progress_query`）、投诉工单进度（`ticket_progress_query`）闭环。
2. **信贷全链路闭环**：支持授信额度查询（`credit_limit_query`）、贷款申请（`loan_application`）、还款计划与逾期账单查询（`repayment_plan_query`）、贷款还款（`loan_repayment`），以及高危步骤确定性二次确认门禁（`_CONFIRM_TOKENS` / `_CANCEL_TOKENS`）与任务暂停/恢复切换。
3. **安全护栏、脱敏与可观测性**：
   - `customer/security/auth.py`（HS256 会话凭证）、`guardrails.py`（防 Prompt 注入与跨客户越权）、`masking.py`（敏感卡号/账户号/身份证号脱敏）。
   - `customer/utils/observability.py`：接入 Langfuse 全链路 Trace（`https://jp.cloud.langfuse.com`）。
   - `POST /api/chat/stream`：SSE 流式分阶段状态（`stage`、`delta`、`done`）与结构化回执凭证（`receipt`）。

### 2. 金融智脑 RAG 融合（`D:\code\finance_brain` × `d:\code\finance-customer`）
1. **`finance_brain` 接口扩展与备份保护**：
   - 已基于融合前原始提交 `1497286` 创建并推送永久备份分支 **`backup/original`**（`origin/backup/original`），核心目录 `processor/`、`utils/`、`common/` 保持原版未改动。
   - [`api/query_service.py`](file:///D:/code/finance_brain/api/query_service.py)：新增 `POST /api/v1/retrieve`，完整对齐 [`main_graph.py`](file:///D:/code/finance_brain/processor/query_processor/main_graph.py) 检索拓扑：`node_item_name_confirm` → 三路并发召回（`node_search_embedding` + `node_search_embedding_hyde` + `node_web_search_mcp`）→ `node_rrf` → `node_rerank`（`top_k=10`）。
   - [`api/file_import_service.py`](file:///D:/code/finance_brain/api/file_import_service.py) & [`page/import.html`](file:///D:/code/finance_brain/page/import.html)：默认端口迁至 `8002`（避免与 `finance-data` `8000` 冲突），新增 `GET /health` 与 `Cache-Control: no-store`，并将 `import.html` 视觉风格统一为金融客服的账本纸张风格（`#F6F4EF` / `#3F6F68` / `Noto Serif SC`），移除了多余内部顶栏。
2. **`finance-customer` 知识检索与溯源闭环**：
   - [`customer/clients/rag_client.py`](file:///d:/code/finance-customer/customer/clients/rag_client.py)：异步调用 `finance_brain` `/api/v1/retrieve` 并提供 `/api/rag/status` 双端口（`8001` / `8002`）健康探测；已去掉 15s 读取超时限制（`rag_timeout_seconds=0.0`，`httpx.Timeout(None, connect=3.0)`），仅在 RAG 服务未连接、接口报错或未召回切片时回退本地知识库兜底。
   - [`customer/handlers/knowledge/intents.py`](file:///d:/code/finance-customer/customer/handlers/knowledge/intents.py)：全部 7 类知识意图均已绑定 `"rag.default"`。
   - [`customer/handlers/knowledge/provider.py`](file:///d:/code/finance-customer/customer/handlers/knowledge/provider.py)：修复了 `focused_object`（如 `account`“活期储蓄账户”）被误传为 Milvus `item_names` 过滤条件的问题（现仅在 `focused.type in {"finance_product", "knowledge_doc", "product"}` 时传 `item_names`）。
   - [`customer/engine/dialogue_engine.py`](file:///d:/code/finance-customer/customer/engine/dialogue_engine.py)：在 `chitchat` 分支前增加非寒暄文本的远程 RAG 探测（`score >= 0.35` 自动转为知识回答并复用 `prefetched_chunks`），防止财报/研报/基金文档被误判为闲聊。
   - 前端 [`Conversation.tsx`](file:///d:/code/finance-customer/frontend/src/components/Conversation/Conversation.tsx)（气泡下方可折叠「参考溯源 · N 条知识切片」）、[`KnowledgeAdminModal.tsx`](file:///d:/code/finance-customer/frontend/src/components/KnowledgeAdminModal.tsx)（顶栏「知识库 · 文档导入入库」弹窗嵌入 `:8002/import.html`，已移除「智脑检索调试」Tab）。

---

## 三、已解决的核心瓶颈（2026-11-20 更新）

### 1. 已解决：单文档多章节召回被 `limit=5` 与 `top_k=6` 截断的问题
- **现象**：以 Milvus 中《易方达智造优势混合型证券投资基金（易方达智造优势混合C）基金产品资料概要更新》为例，该文档在 `finance_chunks` 集合中共切分为 **13 条切片**（包含产品概况×2、投资目标与策略×3、资产配置图表×1、销售费用×1、运作扣除费用×1、**（三）基金运作综合费用测算 1.81%×1**、风险揭示×1、重要提示×1、其他查询方式×1）。
- **落地改动**：
  - 将 [`node_search_embedding.py`](file:///D:/code/finance_brain/processor/query_processor/nodes/node_search_embedding.py) 与 [`node_search_embedding_hyde.py`](file:///D:/code/finance_brain/processor/query_processor/nodes/node_search_embedding_hyde.py) 的 `create_hybrid_search_requests` 及 `hybrid_search` 的 `limit` 均调至 **`15`**；
  - 将 [`node_rrf.py`](file:///D:/code/finance_brain/processor/query_processor/nodes/node_rrf.py) 的 `top_k` 从 `6` 上调至 **`15`**，确保单篇文档的全量章节切片都能进入 Rerank 精排。

### 2. 已解决：Rerank 阶段超长切片分块 Max-Pooling 无损提速（方案 C）
- **原瓶颈**：[`node_rerank.py`](file:///D:/code/finance_brain/processor/query_processor/nodes/node_rerank.py) 原逻辑对超过 512 tokens 的切片在 `for` 循环中串行调用大模型（`rerank_text_refine`）压缩摘要，全流程检索耗时 `40s ~ 116s`。
- **落地改动**：
  - 在 [`node_rerank.py`](file:///D:/code/finance_brain/processor/query_processor/nodes/node_rerank.py) 中实现 `_split_text_for_rerank`（保留首行/表头上下文的重叠滑动窗口分块）与 `step_4_list_score_and_rank` 的单切片多子窗口 **Max-Pooling** 聚合打分；
  - 无需调用 LLM 摘要且 **0 信息丢失**（全文每一段均参与 Reranker 批量打分，原始 `text` 完整保留），3400+ 字长切片的 Rerank 节点总耗时从 `40s+` 降至 **`~2.5s - 3.0s`**。
