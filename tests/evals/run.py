"""Deterministic toy retrieval eval. Never presents these samples as a statistical claim."""
import json
import os
from pathlib import Path
os.environ["EMBEDDING_API_KEY"] = ""
os.environ["EMBEDDING_BASE_URL"] = ""
from services.api.db import Base, make_database
from packages.rag.knowledge import ingest, search

QUERIES = {
    "gtm-foundations": ["GTM解决什么问题", "Go-to-Market价值", "STP市场细分", "ICP理想客户", "B2B决策者", "目标客户购买假设", "产品价值主张", "市场进入验证顺序", "触达转化路径", "客户成功与GTM"],
    "channel-and-kol": ["海外渠道销售与KOL营销的区别", "sell-in和sell-out", "经销商库存", "KOL创作者筛选", "粉丝量真实互动", "渠道回款风险", "返利设计", "本地创作者与零售", "终端动销", "内容合作受众影响"],
    "gtm-metrics": ["ROI口径", "ROI与ROAS区别", "CAC分子分母", "LTV留存假设", "回收周期现金流", "归因窗口局限", "自然销量增量贡献", "护栏指标", "统计显著性样本", "增长实验决策规则"],
}


def run():
    engine, factory = make_database("sqlite://")
    Base.metadata.create_all(engine)
    results = []
    with factory() as db:
        ingest(db, Path(__file__).resolve().parents[1] / "fixtures/knowledge")
        for expected, queries in QUERIES.items():
            for q in queries:
                matches = search(db, q, "learning", top_k=5)
                ranks = [i + 1 for i, item in enumerate(matches) if item["doc_id"] == expected]
                results.append({"query": q, "expected_doc": expected, "rank": min(ranks) if ranks else None, "permissions_valid": all(item["permission"] == "public_display" for item in matches)})
    report = {"dataset": "30 authored toy queries / 3 original learning documents", "mode": "lexical-development", "recall_at_5": sum(r["rank"] is not None for r in results) / len(results), "mrr_at_5": sum(1 / r["rank"] if r["rank"] else 0 for r in results) / len(results), "permission_leaks": sum(not r["permissions_valid"] for r in results), "results": results, "limitations": "小型自写样本，仅做功能回归；未评估真实语义模型、人工citation support或统计显著性。"}
    output = Path('.data/eval-report.json'); output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='results'}, ensure_ascii=False))


if __name__ == '__main__':
    run()
