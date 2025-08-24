import base64
import requests


def get_file_data(url: str) -> str | None:
        try:
            response = requests.get(url)
            response.raise_for_status()

            base64_content = base64.b64encode(response.content).decode('utf-8')
            return base64_content
        except requests.exceptions.RequestException as e:
            print(f"Error while downloading file: {e}") # TODO: add logger and raise custom exception
            return None