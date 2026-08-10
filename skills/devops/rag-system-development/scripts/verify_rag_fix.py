#!/usr/bin/env python3
"""
Verification script for the sync_hybrid_search_with_citations fix.
Run this after applying the fix to verify the RAG pipeline works.
"""
import sys
sys.path.insert(0, "/c/Users/valte/project_rag")

from server import sync_hybrid_search_with_citations

def test_rag_retrieval():
    """Test that retrieval returns context and sources for known queries."""
    test_queries = [
        "What is RAG?",
        "How does hybrid retrieval work?",
        "What is vectorless RAG?",
        "Explain agentic RAG",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        context, sources, had_context = sync_hybrid_search_with_citations(query)
        
        print(f"had_context: {had_context}")
        print(f"context length: {len(context)} chars")
        print(f"sources count: {len(sources)}")
        
        if sources:
            print("\nTop sources:")
            for i, s in enumerate(sources[:3]):
                print(f"  {i+1}. {s['source_file']} (p.{s['page']}) - relevance: {s['relevance_score']}")
                if s['headings']:
                    print(f"     Headings: {s['headings'][:80]}")
        else:
            print("  NO SOURCES RETURNED - BUG STILL EXISTS!")
        
        if not had_context:
            print("❌ FAIL: No context retrieved for known query")
            return False
    
    print("\n✅ ALL TESTS PASSED - Fix verified!")
    return True

if __name__ == "__main__":
    test_rag_retrieval()