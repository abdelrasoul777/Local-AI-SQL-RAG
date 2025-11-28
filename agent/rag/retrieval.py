import os
import re
from rank_bm25 import BM25Okapi

class Retriever:
    def __init__(self, docs_dir):
        self.docs_dir = docs_dir
        self.documents = []
        self.doc_ids = []
        self.bm25 = None
        self._load_documents()
        
    def _load_documents(self):
        """Load and chunk markdown files from the docs directory."""
        if not os.path.exists(self.docs_dir):
            print(f"Warning: Docs directory {self.docs_dir} not found.")
            return

        for filename in os.listdir(self.docs_dir):
            if filename.endswith(".md"):
                file_path = os.path.join(self.docs_dir, filename)
                base_name = os.path.splitext(filename)[0]
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Simple chunking by headers (##) or just paragraphs if needed
                # For this requirement, we'll chunk by sections or paragraphs
                chunks = self._chunk_markdown(content)
                
                for i, chunk in enumerate(chunks):
                    if chunk.strip():
                        self.documents.append(chunk)
                        self.doc_ids.append(f"{base_name}::chunk{i}")

        # Initialize BM25
        tokenized_corpus = [doc.lower().split() for doc in self.documents]
        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)

    def _chunk_markdown(self, content):
        """
        Splits markdown content into semantic chunks.
        Strategy: Split by headers (## or #) and keep content with its header.
        """
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        
        for line in lines:
            # Detect header lines
            if line.startswith('##') or (line.startswith('#') and not line.startswith('##')):
                # Save previous chunk if exists
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(chunk_text)
                # Start new chunk with header
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)
        
        return chunks

    def retrieve(self, query, k=3):
        """
        Retrieve top-k chunks for a given query.
        Uses hybrid scoring: BM25 + exact keyword matching boost.
        Returns: List of dicts with 'content' and 'id'.
        """
        if not self.bm25:
            return []
            
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # Extract important keywords (capitalized words, quoted terms, numbers)
        import re
        keywords = []
        # Find capitalized words (likely important terms like "Beverages", "AOV")
        keywords.extend(re.findall(r'\b[A-Z][a-zA-Z]+\b', query))
        # Find quoted terms
        keywords.extend(re.findall(r'"([^"]+)"', query))
        # Find important question terms
        important_terms = ['unopened', 'opened', 'perishable', 'non-perishable', 
                          'summer', 'winter', 'aov', 'revenue', 'margin']
        keywords.extend([w for w in query.lower().split() if w in important_terms])
        
        # Combine BM25 with keyword boost
        hybrid_scores = []
        for i, bm25_score in enumerate(bm25_scores):
            doc_lower = self.documents[i].lower()
            
            # Boost score if important keywords appear
            keyword_boost = 0.0
            for keyword in keywords:
                if keyword.lower() in doc_lower:
                    # Higher boost for exact matches in headers (lines starting with ##)
                    if f"## {keyword.lower()}" in doc_lower or f"# {keyword.lower()}" in doc_lower:
                        keyword_boost += 3.0
                    else:
                        keyword_boost += 1.0
            
            hybrid_scores.append(bm25_score + keyword_boost)
        
        # Get top k indices
        top_n = sorted(range(len(hybrid_scores)), key=lambda i: hybrid_scores[i], reverse=True)[:k]
        
        results = []
        for i in top_n:
            # Filter out zero scores to avoid irrelevant noise
            if hybrid_scores[i] > 0:
                results.append({
                    "content": self.documents[i],
                    "id": self.doc_ids[i],
                    "score": hybrid_scores[i]
                })
                
        return results

if __name__ == "__main__":
    # Test Retriever
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    docs_path = os.path.join(base_dir, "docs")
    
    retriever = Retriever(docs_path)
    print(f"Loaded {len(retriever.documents)} chunks.")
    
    query = "When is the Summer Beverages event?"
    results = retriever.retrieve(query)
    print(f"\nQuery: {query}")
    for r in results:
        print(f"- [{r['id']}] {r['content'][:50]}...")
