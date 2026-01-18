import openai
import config
from tenacity import retry, wait_random_exponential, stop_after_attempt

class LLMRepository:
    """
    Repository for interacting with the Nebius AI LLM.
    This class is a thin wrapper around the openai client.
    """
    def __init__(self):
        self.client = openai.OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=config.NEBIUS_API_KEY
        )
        self.model = "openai/gpt-oss-20b"

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    def ask(self, system_prompt, user_prompt):
        """
        Sends a request to the LLM and returns the response content.
        """
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
