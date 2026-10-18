import traceback
from pinecone.grpc import PineconeGRPC as Pinecone
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

@tool
async def search_store_policies(query: str) -> str:
    """PRIMARY KNOWLEDGE BASE. ALWAYS use this tool FIRST for any questions 
    regarding OUR company's official return policy, refund rules, cancellation 
    terms, shipping policies, or hardware warranties.
    """
    print("\n--- [TOOL: PINECONE VECTOR RAG] ---")
    print(f"-> Querying Pinecone Index for: '{query}'")
    try:
        # 1. Generate Query Embeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.OPENAI_API_KEY
        )
        query_vector = await embeddings.aembed_query(query)

        # 2. Synchronous Pinecone Call via gRPC GRPC Client
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        
        # Execute query synchronously inside thread pool to prevent async loop block
        import asyncio
        response = await asyncio.to_thread(
            index.query,
            vector=query_vector,
            top_k=5,
            include_metadata=True
        )

        matches = response.get("matches", []) if isinstance(response, dict) else getattr(response, "matches", [])
        print(f"-> Raw Matches Found: {len(matches)}")

        if not matches:
            print("-> [WARNING]: Pinecone index returned 0 matches.")
            return "NO_INTERNAL_POLICY_FOUND: No relevant internal policy document matches this query."

        # Lower threshold slightly for combined queries
        SCORE_THRESHOLD = 0.30
        valid_excerpts = []

        for m in matches:
            score = m.get("score", 0.0) if isinstance(m, dict) else getattr(m, "score", 0.0)
            metadata = m.get("metadata", {}) if isinstance(m, dict) else getattr(m, "metadata", {})
            text = metadata.get("text", "") if isinstance(metadata, dict) else ""
            doc_id = m.get("id", "N/A") if isinstance(m, dict) else getattr(m, "id", "N/A")

            print(f"   Match ID={doc_id}, Score={score:.4f}")

            if score >= SCORE_THRESHOLD and text:
                valid_excerpts.append(f"Policy Document (Relevance Score: {score:.2f}): {text}")

        if not valid_excerpts:
            print(f"-> [WARNING]: Matches found, but none passed score threshold ({SCORE_THRESHOLD}).")
            return "NO_INTERNAL_POLICY_FOUND: No internal store policies passed the relevance threshold."

        print(f"-> [SUCCESS]: Returning {len(valid_excerpts)} valid internal policy chunk(s) to Agent.")
        return "\n\n".join(valid_excerpts)

    except Exception as e:
        print(f"-> [ERROR]: Exception inside Pinecone retriever: {str(e)}")
        # Print full stack trace to your terminal to trace the exact line that failed
        traceback.print_exc()
        return f"Error searching policy index: {str(e)}"