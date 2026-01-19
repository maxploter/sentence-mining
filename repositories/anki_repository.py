import logging  # Import the logging module

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception

import config


class AnkiConnectError(Exception):
    """Custom exception for AnkiConnect errors."""
    pass

class AnkiRepository:
    """
    Repository for interacting with the AnkiConnect API.
    This class is a thin wrapper around the requests library.
    """

    @staticmethod
    def is_retryable(self, exception):
        """Return True if we should retry on a timeout or network error."""
        error_str = str(exception).lower()
        return "timeout" in error_str or "network error" in error_str

    @retry(
      stop=stop_after_attempt(config.ANKICONNECT_MAX_RETRIES),
      wait=wait_fixed(config.ANKICONNECT_RETRY_DELAY),
      retry=retry_if_exception(is_retryable),
      reraise=True
    )
    def request(self, action, params=None, timeout=None):
        """
        Performs a request to AnkiConnect. Returns the 'result' on success.
        Raises AnkiConnectError on failure. Retries on timeout or network errors.
        """
        if timeout is None:
            timeout = config.ANKICONNECT_TIMEOUT
        
        try:
            payload = {
                "action": action,
                "version": 6,
                "params": params or {}
            }
            resp = requests.post(config.ANKICONNECT_URL, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error") is not None:
                logging.error(f"AnkiConnect error for action '{action}': {data['error']}")
                raise AnkiConnectError(data['error'])
            return data.get("result")
        except requests.exceptions.Timeout as e:
            logging.error(f"Network timeout communicating with AnkiConnect for action '{action}': {e}")
            raise AnkiConnectError(f"Network timeout communicating with AnkiConnect: {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error communicating with AnkiConnect for action '{action}': {e}")
            raise AnkiConnectError(f"Network error communicating with AnkiConnect: {e}")
