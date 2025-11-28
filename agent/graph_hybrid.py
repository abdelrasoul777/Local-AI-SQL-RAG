from typing import TypedDict, Annotated, List, Dict, Any, Union
import operator
import dspy
import sqlite3
from langgraph.graph import StateGraph, END

from agent.dspy_signatures import Router, GenerateSQL, SynthesizeAnswer, ExtractConstraints
from agent.rag.retrieval import Retriever
from agent.tools.sqlite_tool import SQLiteTool

# --- State Definition ---
class AgentState(TypedDict):
    question: str
    format_hint: str
    
    # Intermediate states
    plan: Dict[str, Any]
    retrieved_docs: List[Dict[str, Any]]
    sql_query: str
    sql_result: List[Any]
    sql_error: str
    
    # Output
    final_answer: Any
    explanation: str
    confidence: float
    citations: List[str]
    
    # Control flow
    route: str
    retry_count: int

# --- Nodes ---

class AgentNodes:
    def __init__(self, db_path, docs_path):
        self.sqlite_tool = SQLiteTool(db_path)
        self.retriever = Retriever(docs_path)
        
        # Initialize DSPy modules with temperature control
        self.router = dspy.Predict(Router)
        self.sql_generator = dspy.Predict(GenerateSQL)  # Revert to Predict for stability
        self.synthesizer = dspy.ChainOfThought(SynthesizeAnswer)
        self.constraint_extractor = dspy.ChainOfThought(ExtractConstraints)

    def node_router(self, state: AgentState):
        print(f"--- Router: Analyzing '{state['question']}' ---")
        prediction = self.router(question=state['question'])
        decision = prediction.decision.lower().strip()
        
        # Normalize decision
        if 'sql' in decision: decision = 'sql'
        elif 'rag' in decision: decision = 'rag'
        else: decision = 'hybrid'
            
        return {"route": decision}

    def node_retriever(self, state: AgentState):
        print("--- Retriever: Fetching docs ---")
        results = self.retriever.retrieve(state['question'], k=3)
        return {"retrieved_docs": results}

    def node_planner(self, state: AgentState):
        print("--- Planner: Extracting constraints ---")
        
        # Extract constraints from retrieved documents if available
        if state.get('retrieved_docs'):
            docs_text = "\n".join([doc['content'] for doc in state['retrieved_docs']])
            prediction = self.constraint_extractor(
                question=state['question'],
                documents=docs_text
            )
            constraints = prediction.constraints
            print(f"Extracted Constraints: {constraints}")
            return {"plan": {"constraints": constraints}}
        
        return {"plan": {"constraints": "No specific constraints"}}

    def node_nl_sql(self, state: AgentState):
        print("--- NL SQL: Generating Query ---")
        schema_str = self.sqlite_tool.get_schema_detailed()
        
        # Get constraints from planner
        constraints = state.get('plan', {}).get('constraints', 'None')
        
        # Add retry context if previous error exists
        q = state['question']
        if state.get('sql_error'):
            q += f" (Previous SQL had error: {state['sql_error']}. Fix it!)"
        
        try:
            prediction = self.sql_generator(
                question=q,
                schema_info=schema_str,
                constraints=str(constraints)
            )
            
            # Extract SQL from LLM response - handle multiple formats
            raw_response = str(prediction.sql_query).strip()
            
            # Remove completion markers
            raw_response = raw_response.split('[[')[0].split('##')[0].strip()
            
            # Extract from markdown blocks
            if '```sql' in raw_response:
                sql = raw_response.split('```sql')[1].split('```')[0].strip()
            elif '```' in raw_response:
                sql = raw_response.split('```')[1].split('```')[0].strip()
            else:
                sql = raw_response
            
            # Remove semicolons, comments, and newlines
            sql = sql.split(';')[0].strip()
            sql = ' '.join(sql.split())  # Normalize whitespace
            
            # Basic validation
            if not sql.upper().startswith('SELECT'):
                raise ValueError("Query must start with SELECT")
                
            return {"sql_query": sql}
            
        except Exception as e:
            print(f"SQL Generation Error: {e}")
            # Fallback: generate a simple safe query
            fallback_sql = "SELECT 1 as result"
            return {"sql_query": fallback_sql, "sql_error": f"Generation failed: {str(e)}"}

    def node_executor(self, state: AgentState):
        print(f"--- Executor: Running SQL ---")
        print(f"Query: {state['sql_query']}")
        
        result = self.sqlite_tool.execute(state['sql_query'])
        
        if isinstance(result, str) and result.startswith("Error"):
            print(f"   >> SQL Execution Failed: {result}")
            # Increment retry count on error
            current_retries = state.get('retry_count', 0)
            return {"sql_error": result, "sql_result": [], "retry_count": current_retries + 1}
        
        return {"sql_result": result, "sql_error": "", "retry_count": 0}

    def node_synthesizer(self, state: AgentState):
        print("--- Synthesizer: Formatting Answer ---")
        
        # Compile context
        context_parts = []
        citations = []
        
        if state.get('retrieved_docs'):
            context_parts.append("Documentation:")
            for doc in state['retrieved_docs']:
                context_parts.append(f"- {doc['content']}")
                citations.append(doc['id'])
                
        if state.get('sql_result'):
            context_parts.append(f"SQL Result: {state['sql_result']}")
            citations.append("Orders") # Generic DB citation as per reqs, or derive from query
            
        context_str = "\n".join(context_parts)
        
        try:
            prediction = self.synthesizer(
                question=state['question'],
                context=context_str,
                format_hint=state['format_hint']
            )
            
            # Parse and validate the answer
            final_ans = prediction.final_answer
            
            # Try to convert based on format hint
            if state['format_hint'] == 'int':
                try:
                    # Extract first number if it's embedded in text
                    import re
                    numbers = re.findall(r'\d+', str(final_ans))
                    final_ans = int(numbers[0]) if numbers else int(final_ans)
                except:
                    final_ans = 0
            elif state['format_hint'] == 'float':
                try:
                    import re
                    numbers = re.findall(r'\d+\.?\d*', str(final_ans))
                    final_ans = float(numbers[0]) if numbers else float(final_ans)
                except:
                    final_ans = 0.0
            
            # Parse confidence
            try:
                conf = float(prediction.confidence)
                if conf > 1.0: conf = 1.0
                if conf < 0.0: conf = 0.0
            except:
                conf = 0.7
            
            expl = str(prediction.explanation)[:200]  # Truncate to avoid issues
            
            return {
                "final_answer": final_ans,
                "explanation": expl,
                "confidence": conf,
                "citations": citations
            }
        except Exception as e:
            print(f"Synthesizer error: {e}")
            # Fallback: try to parse answer from context or error message
            import re
            import json
            
            # Try to extract from error message if it contains partial JSON
            error_str = str(e)
            final_ans = "N/A"
            expl = "Could not synthesize answer due to parsing error"
            conf = 0.0
            
            # Attempt to extract fields from partial response
            if "final_answer" in error_str:
                try:
                    match = re.search(r'"final_answer"\s*:\s*"?([^",}]+)"?', error_str)
                    if match:
                        final_ans = match.group(1)
                except:
                    pass
            
            return {
                "final_answer": final_ans,
                "explanation": expl,
                "confidence": conf,
                "citations": citations
            }

    def check_retry(self, state: AgentState):
        """Conditional edge for repair loop"""
        if state.get('sql_error'):
            current_retries = state.get('retry_count', 0)
            if current_retries < 2:
                print(f"!!! Error detected. Retrying ({current_retries + 1}/2) !!!")
                return "retry"
            else:
                print("!!! Max retries reached. Proceeding with error !!!")
                return "continue"
        return "continue"

# --- Graph Construction ---

def build_graph(db_path, docs_path):
    nodes = AgentNodes(db_path, docs_path)
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("router", nodes.node_router)
    workflow.add_node("retriever", nodes.node_retriever)
    workflow.add_node("planner", nodes.node_planner)
    workflow.add_node("nl_sql", nodes.node_nl_sql)
    workflow.add_node("executor", nodes.node_executor)
    workflow.add_node("synthesizer", nodes.node_synthesizer)
    
    # Entry point
    workflow.set_entry_point("router")
    
    # Conditional Edges from Router
    workflow.add_conditional_edges(
        "router",
        lambda x: x['route'],
        {
            "rag": "retriever",
            "sql": "nl_sql",
            "hybrid": "retriever" # Start with retriever for hybrid
        }
    )
    
    # Hybrid flow: Retriever -> Planner -> NL SQL
    workflow.add_edge("retriever", "planner")
    
    # Planner logic
    def planner_router(state):
        if state['route'] == 'hybrid':
            return "nl_sql"
        return "synthesizer" # If just RAG
        
    workflow.add_conditional_edges(
        "planner",
        planner_router,
        {
            "nl_sql": "nl_sql",
            "synthesizer": "synthesizer"
        }
    )
    
    # SQL Flow & Repair Loop
    workflow.add_edge("nl_sql", "executor")
    
    workflow.add_conditional_edges(
        "executor",
        nodes.check_retry,
        {
            "retry": "nl_sql",
            "continue": "synthesizer"
        }
    )
    
    # Exit
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()

