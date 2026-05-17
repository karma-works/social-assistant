def extract_text(content: object) -> str:
    """Extract plain text from a ChatVertexAI response (handles Gemini thinking blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")
    return str(content)
