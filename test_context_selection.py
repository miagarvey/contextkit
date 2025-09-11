#!/usr/bin/env python3
"""Test script for the multi-stage LLM context selection system."""

import os
import sys
from pathlib import Path

# Add the contextkit package to the path
sys.path.insert(0, str(Path(__file__).parent))

from contextkit.core.auto import auto_compose_context

def test_context_selection():
    """Test the multi-stage LLM context selection with various scenarios."""
    
    print("🧪 Testing Multi-Stage LLM Context Selection System")
    print("=" * 60)
    
    # Test scenarios with different types of queries
    test_cases = [
        {
            "name": "Customer LTV Analysis Query",
            "prompt": "What's the average customer lifetime value by acquisition channel?",
            "project": "analytics",
            "expected_relevance": "High - should find LTV-related ContextPacks"
        },
        {
            "name": "Returns Analysis Query", 
            "prompt": "How do product returns affect customer lifetime value?",
            "project": "analytics",
            "expected_relevance": "High - should find returns and LTV ContextPacks"
        },
        {
            "name": "Unrelated Query",
            "prompt": "What's the weather like today?",
            "project": "analytics", 
            "expected_relevance": "Low - should return minimal or no context"
        },
        {
            "name": "Project Isolation Test",
            "prompt": "What's the average customer lifetime value?",
            "project": "different-project",
            "expected_relevance": "Low - should not find analytics ContextPacks"
        },
        {
            "name": "General Business Query",
            "prompt": "Show me a dashboard analysis of our key metrics",
            "project": "analytics",
            "expected_relevance": "Medium - should find dashboard-related content"
        },
        {
            "name": "No Project Filter Test",
            "prompt": "What's the customer lifetime value analysis?",
            "project": None,
            "expected_relevance": "High - should find all relevant ContextPacks"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"Prompt: {test_case['prompt']}")
        print(f"Project: {test_case['project']}")
        print(f"Expected: {test_case['expected_relevance']}")
        print("-" * 40)
        
        try:
            # Test the context composition
            result = auto_compose_context(
                prompt=test_case['prompt'],
                max_tokens=4000,
                current_schema=None,
                project=test_case['project']
            )
            
            # Analyze the result
            if "[CONTEXTKIT]" in result:
                context_part = result.split("[CONTEXTKIT]", 1)[1]
                
                # Extract metadata
                lines = context_part.split('\n')
                packs_used = []
                token_count = 0
                
                for line in lines:
                    if "ContextPack(s):" in line:
                        packs_part = line.split("ContextPack(s):")[1].strip()
                        packs_used = [p.strip() for p in packs_part.split(",") if p.strip()]
                    elif "Estimated tokens:" in line:
                        try:
                            token_part = line.split("Estimated tokens:")[1].split("/")[0].strip()
                            token_count = int(token_part)
                        except (IndexError, ValueError):
                            pass
                
                print(f"✅ Context Found:")
                print(f"   - ContextPacks Used: {len(packs_used)}")
                print(f"   - Pack Names: {packs_used}")
                print(f"   - Token Count: {token_count}")
                
                # Show first few lines of context
                context_lines = context_part.split('\n')[:10]
                print(f"   - Preview: {' '.join(context_lines)[:200]}...")
                
            else:
                print("❌ No context selected (LLM determined no relevant context)")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 60}")
    print("🎯 Test Summary:")
    print("- Multi-stage LLM selection should be conservative")
    print("- Project isolation should prevent cross-project context")
    print("- Irrelevant queries should get minimal/no context")
    print("- Relevant queries should get targeted, useful context")

if __name__ == "__main__":
    test_context_selection()
