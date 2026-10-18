import time
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

POLICY_DOCUMENTS = [
    {
        "id": "doc1",
        "text": "Return Policy: Customers can request a full refund or return within 30 days of purchase for unused items in original packaging. Refunds are processed back to the original payment method within 3-5 business days.",
        "category": "refund",
        "source": "store_policy"
    },
    {
        "id": "doc2",
        "text": "Cancellation Policy: Orders can be cancelled for a full refund at any time before the status changes to SHIPPED or DELIVERED. If an order is already DELIVERED, it must be handled under the standard 30-day Return Policy.",
        "category": "cancellation",
        "source": "store_policy"
    },
    {
        "id": "doc3",
        "text": "Shipping Policy: Standard shipping takes 3 to 5 business days. Express shipping takes 1 to 2 business days. Free shipping applies to orders over $100.",
        "category": "shipping",
        "source": "store_policy"
    },
    {
        "id": "doc4",
        "text": "Warranty Policy: All electronic hardware products include a 1-year limited warranty covering manufacturing defects. It does not cover accidental damage or water exposure.",
        "category": "warranty",
        "source": "store_policy"
    }
]


def initialize_and_seed_pinecone():
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index_name = settings.PINECONE_INDEX_NAME

    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Creating Pinecone index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        time.sleep(5)

    index = pc.Index(index_name)
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.OPENAI_API_KEY
    )

    print("Embedding and uploading policy documents to Pinecone...")
    vectors_to_upsert = []
    for doc in POLICY_DOCUMENTS:
        vector_values = embeddings.embed_query(doc["text"])
        vectors_to_upsert.append({
            "id": doc["id"],
            "values": vector_values,
            "metadata": {"text": doc["text"], "category": doc["category"], "source": doc["source"]}
        })

    index.upsert(vectors=vectors_to_upsert)
    print("Pinecone ingestion complete!")


if __name__ == "__main__":
    initialize_and_seed_pinecone()