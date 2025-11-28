import argparse
import json
import os
import dspy
from agent.graph_hybrid import build_graph

def main():
    parser = argparse.ArgumentParser(description="Run the Hybrid AI Agent")
    parser.add_argument("--batch", required=True, help="Input JSONL file")
    parser.add_argument("--out", required=True, help="Output JSONL file")
    args = parser.parse_args()

    # 1. Setup LLM (Ollama)
    print("--- Initializing LLM (phi3.5:3.8b) ---")
    # Using the dspy.LM unified interface
    lm = dspy.LM(model='ollama_chat/phi3.5:3.8b', api_base='http://localhost:11434', api_key='')
    dspy.settings.configure(lm=lm)

    # 2. Setup Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "data", "northwind.sqlite")
    docs_path = os.path.join(base_dir, "docs")

    # 3. Build Graph
    print("--- Building Agent Graph ---")
    app = build_graph(db_path, docs_path)

    # 4. Process Batch
    print(f"--- Processing {args.batch} -> {args.out} ---")
    
    results = []
    
    with open(args.batch, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            if not line.strip(): continue
            
            item = json.loads(line)
            q_id = item['id']
            question = item['question']
            format_hint = item.get('format_hint', "str")
            
            print(f"\n[ID: {q_id}] Question: {question}")
            
            # Initial State
            initial_state = {
                "question": question,
                "format_hint": format_hint,
                "retry_count": 0,
                "plan": {},
                "retrieved_docs": [],
                "sql_query": "",
                "sql_result": [],
                "sql_error": "",
                "citations": []
            }
            
            # Run Graph
            # The result from app.invoke is the final state
            final_state = app.invoke(initial_state)
            
            # Construct Output
            output_item = {
                "id": q_id,
                "final_answer": final_state.get('final_answer'),
                "sql": final_state.get('sql_query', ""),
                "confidence": final_state.get('confidence', 0.0),
                "explanation": final_state.get('explanation', ""),
                "citations": final_state.get('citations', [])
            }
            
            results.append(output_item)

    # 5. Write Output
    with open(args.out, 'w', encoding='utf-8') as f_out:
        for item in results:
            f_out.write(json.dumps(item) + "\n")
            
    print(f"\n--- Done. Results saved to {args.out} ---")

if __name__ == "__main__":
    main()
