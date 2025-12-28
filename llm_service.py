import openai
import config
import re
from tenacity import retry, wait_random_exponential, stop_after_attempt

class LLM:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=config.NEBIUS_API_KEY
        )
        self.model = "openai/gpt-oss-20b"

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    def ask(self, system_prompt, user_prompt):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error communicating with Nebius: {e}")
            raise

llm_client = LLM()

def get_definition(word, context):
    """
    Gets the definition of a word using an LLM, based on the context.
    """
    system_prompt = "You are a helpful assistant that provides concise definitions."
    user_prompt = f"""
    Please provide a concise definition for the word or phrase "{word}".
    The word appeared in the following context:
    ---
    {context}
    ---
    Based on this context, what is the most likely meaning of "{word}"?
    Provide only the definition, without any extra text or explanations.
    """
    return llm_client.ask(system_prompt, user_prompt)

def generate_sentences(word, definition, context):
    """
    Generates three example sentences for a word.
    """
    system_prompt = "You are a helpful assistant that generates example sentences."
    user_prompt = f"""
    The word is "{word}".
    Its definition is: "{definition}".
    It appeared in the original context: "{context}".

    Please generate three new, distinct sentences using the word "{word}".
    The sentences should be easy to understand and clearly demonstrate the meaning of the word.
    Return the sentences as a numbered list.
    """
    response_text = llm_client.ask(system_prompt, user_prompt)
    if response_text:
        sentences = [s.strip() for s in response_text.split('\n') if s.strip()]
        sentences = [re.sub(r'^\d+\.\s*', '', s) for s in sentences]
        return sentences
    return []