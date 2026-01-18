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

def strip_markdown_formatting(text):
    """
    Removes common markdown formatting (bold, italics) from a string.
    """
    if not isinstance(text, str):
        return text
    # Remove bold (**text**) and italics (*text* or _text_)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    return text

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

def generate_sentence(word, definition, context):
    """
    Generates one example sentence for a word.
    """
    system_prompt = "You are a helpful assistant that generates an example sentence."
    user_prompt = f"""
    The word is "{word}".
    Its definition is: "{definition}".
    It appeared in the original context: "{context}".

    Please generate one new, distinct sentence using the word "{word}".
    The sentence should be easy to understand and clearly demonstrate the meaning of the word.
    Return only the sentence.
    """
    return llm_client.ask(system_prompt, user_prompt)

def create_cloze_with_llm(word, sentence):
    """
    Uses the LLM to intelligently create a cloze deletion for a word in a sentence,
    handling different word forms.
    """
    system_prompt = """You are an Anki expert. Your task is to create a cloze deletion for a given sentence.
Find the word provided by the user, or its inflected form (e.g., plural, past tense), in the sentence.
Wrap ONLY that word or phrase with Anki's cloze syntax, like this: '{{c1::word}}'.
Return only the modified sentence. Do not add any explanation."""
    user_prompt = f"""The word to be clozed is '{word}'.
The sentence is:
---
{sentence}
---
For example, if the word is 'run' and the sentence is 'He ran a marathon.', the output should be 'He {{c1::ran}} a marathon.'.
If the word is 'walk' and the sentence is 'He was walking home.', the output should be 'He was {{c1::walking}} home.'.
If the word is 'big data' and the sentence is 'The field of big data is growing.', the output should be 'The field of {{c1::big data}} is growing.'."""
    
    return llm_client.ask(system_prompt, user_prompt)