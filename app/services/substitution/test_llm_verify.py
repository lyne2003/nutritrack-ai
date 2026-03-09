from __future__ import annotations

from app.services.substitution.qdrant_search import search_categories
from app.services.substitution.llm_verifier import classify_and_flag_with_llm

if __name__ == "__main__":
    tests = [
        "56 g egg tagliatelle nests",
        "50 g parmesan cheese (shredded)",
        "1 cup coconut milk unsweetened",
        "1 dash salt",
        "1 cup cooked chicken breast",
    ]

    for t in tests:
        print("\n==================================================")
        print("LINE:", t)

        candidates = search_categories(t, top_k=5)
        for c in candidates:
            print(f"  cand: {c['score']:.4f} | {c['category_id']} | {c['label']}")

        decision = classify_and_flag_with_llm(t, candidates)
        print("\n✅ LLM OUTPUT:")
        print(decision)
