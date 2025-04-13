from openai import OpenAI
from pinecone import Pinecone
import json
from source.common import config

openai_client = OpenAI()
embedding_model = config.EMBEDDING_MODEL

pc = Pinecone(api_key=config.PINECONE_API_KEY)
pinecone_index = pc.Index(config.PINECONE_INDEX_NAME)


class VectorSearch:

    def __init__(self, user_query):
        self.user_query = user_query
        self.embedded_query = None
        self.search_result = None
        self.context_prompt = None
        self.metadata_json = None

    def embed_query(self):
        try:
            self.embedded_query = openai_client.embeddings.create(input=self.user_query, model=embedding_model).data[
                0].embedding
        except Exception as e:
            print(e)

    def vector_search(self, search_filter=None, top_k=40):
        try:
            if self.embedded_query is None:
                raise RuntimeError(
                    "Embedded query should not be None, make sure to run embed_query before vector_search")
            self.search_result = pinecone_index.query(vector=[self.embedded_query], filter=search_filter,
                                                      top_k=top_k, include_metadata=True)
        except Exception as e:
            print(e)

    def parse_content(self, chunk_size=100000):
        try:
            if len(self.search_result['matches']) == 0:
                raise RuntimeError("Insufficient data to respond to this question.")
            metadata_json = []
            context_prompt = ''
            for match in self.search_result['matches']:
                potential_prompt = context_prompt + match['metadata']['_node_content']
                if len(potential_prompt) < chunk_size:
                    metadata = {}
                    metadata = match['metadata']  # Access metadata dictionary

                    # Convert '_node_content' to JSON/object and access the nested value
                    if '_node_content' in metadata:
                        node_content = json.loads(metadata['_node_content'])
                        metadata['text'] = node_content.get('text', '')

                        # Remove the '_node_content' key
                        del metadata['_node_content']

                    # Define the keys to be removed
                    keys_to_remove = ['collection', 'orgname', '_node_type', 'doc_id', 'document_id', 'ref_doc_id',
                                      'created_date', 'published_date']

                    # Remove the specified keys from metadata
                    metadata = {key: value for key, value in metadata.items() if key not in keys_to_remove}
                    metadata_json.append(metadata)

                    context_prompt += json.dumps(metadata)
            print(context_prompt)
            self.metadata_json = metadata_json
            self.context_prompt = context_prompt
        except Exception as e:
            print(e)
            raise e

# vs = VectorSearch("give some car related accidents")
# vs.embed_query()
# vs.vector_search()
# vs.parse_content()
