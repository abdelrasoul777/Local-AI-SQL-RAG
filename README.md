# Local Hybrid AI Agent

A local, privacy-focused AI agent that combines **RAG (Retrieval Augmented Generation)** and **SQL** capabilities to answer questions about retail analytics. It runs entirely locally using **Ollama**, **SQLite**, and **DSPy**.

## 🚀 Features

- **Hybrid Architecture**: Intelligently routes questions to RAG (docs), SQL (database), or Hybrid (both) workflows using `LangGraph`.
- **Local LLM**: Powered by `phi3.5:3.8b` via Ollama (no API keys required).
- **Robust SQL Generation**: Generates valid SQLite queries with self-correction loops and schema awareness.
- **DSPy Optimization**: Uses `ChainOfThought` and structured signatures for reliable reasoning.
- **Zero Data Leakage**: All data and inference remain on your local machine.

## 🛠️ Prerequisites

- **Python 3.10+**
- **Ollama**: Installed and running (`ollama serve`)
- **Phi-3.5 Model**: Pull the model with `ollama pull phi3.5:3.8b`

## 📦 Installation

1. **Clone the repository** (or navigate to project folder):
   ```bash
   cd LocalAIAgent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Download the Database**:
   Ensure `data/northwind.sqlite` exists. If not:
   ```powershell
   mkdir -p data
   curl -L -o data/northwind.sqlite https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/main/dist/northwind.db
   ```

## 🏃 Usage

Run the agent with a batch of questions:

```bash
python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl
```

### Output
Results are saved to `outputs_hybrid.jsonl` with the following format:
```json
{
  "id": "question_id",
  "final_answer": "The answer...",
  "sql": "SELECT ...",
  "confidence": 1.0,
  "explanation": "Reasoning...",
  "citations": ["doc_id", "table_name"]
}
```

## 🏗️ Architecture

The agent uses a **LangGraph** workflow:

1.  **Router**: Classifies the question as `rag`, `sql`, or `hybrid`.
2.  **Retriever**: Fetches relevant chunks from `docs/` using BM25 with keyword boosting.
3.  **Planner**: Extracts constraints (e.g., date ranges, categories) from docs for Hybrid queries.
4.  **NL-to-SQL**: Generates SQL queries for `northwind.sqlite` using the `phi3.5` model.
    *   *Includes a repair loop to fix invalid SQL automatically.*
5.  **Executor**: Runs the SQL against the local database.
6.  **Synthesizer**: Combines retrieval context and SQL results to generate the final answer.

## 📂 Project Structure

```
LocalAIAgent/
├── agent/                  # Core agent logic
│   ├── rag/                # Retrieval module (BM25)
│   ├── tools/              # SQLite tools
│   ├── dspy_signatures.py  # Prompt templates
│   └── graph_hybrid.py     # LangGraph workflow
├── data/                   # SQLite database
├── docs/                   # RAG knowledge base (Markdown)
├── run_agent_hybrid.py     # Main CLI entry point
├── sample_questions_hybrid_eval.jsonl # Test questions
└── requirements.txt        # Python dependencies
```

## 📝 Notes

- **Database Range**: The Northwind database contains data from **2012-2023**.
- **Documentation**: The RAG documents (`docs/`) describe policies and campaigns for **1997**.
- **Hybrid Queries**: Questions referencing 1997 dates with the current database will correctly return 0 results due to the date mismatch, demonstrating the agent's accurate execution of logic.
