import os


PROMPTS_DIR = os.path.dirname(__file__)


def load_prompt(prompt_name: str, variables: dict) -> str:
    """
    Returns the prompt content with variables filled in.

    Example of use:
        load_prompt('recall', {'name': 'Maria', 'date': '10/01/2026'})
    """
    filename = f"{prompt_name}.md"
    filepath = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(filepath):
        raise ValueError(f"Prompt '{prompt_name}' not found.")
    with open(filepath, "r", encoding="utf-8") as f:
        prompt = f.read()
    return prompt.format(**variables)
