import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from .protocols import BaseAgent, AgentResponse, AgentResponseStatus

logger = logging.getLogger(__name__)


class TextSummarizerAgent(BaseAgent):
    """Agent that summarizes text using OpenAI models."""

    def __init__(
        self,
        client: OpenAI,
        model: str = "gpt-5-nano",
        instructions: Optional[str] = None
    ):
        super().__init__(
            name="TextSummarizerAgent",
            description="Summarizes text into well-structured articles using LLM"
        )
        self.client = client
        self.model = model
        self.instructions = instructions or self._get_default_instructions()
        self._logger = logger

    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process text to create a summary article.

        Args:
            input_data: Dict with 'text' key containing text to summarize,
                        optional 'max_length' and 'style' keys

        Returns:
            AgentResponse with article or error
        """
        # Validate input
        if not input_data or "text" not in input_data:
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error="Text is required in input data",
                error_type="validation_error"
            )

        if not isinstance(input_data["text"], str) or not input_data["text"].strip():
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error="Text must be a non-empty string",
                error_type="validation_error"
            )

        text = input_data["text"]
        max_length = input_data.get("max_length", 1000)
        style = input_data.get("style", "neutral")

        # Use configurable instructions
        instructions = self._get_default_instructions(max_length=max_length, style=style)

        # Generate article
        article = self._generate_article(text, instructions)
        if not article:
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error="Model failed to generate article",
                error_type="generation_error"
            )

        return AgentResponse(
            status=AgentResponseStatus.SUCCESS,
            data={"article": article}
        )

    def _generate_article(self, text: str, instructions: str) -> Optional[str]:
        """Generate article using the LLM."""
        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": text},
        ]

        try:
            resp = self.client.responses.create(model=self.model, input=messages)
            article_text = resp.output_text
            return article_text.strip()
        except Exception:
            self._logger.exception("Model call failed")
            return None

    @staticmethod
    def _get_default_instructions(max_length: int = 1000, style: str = "neutral") -> str:
        """Return summarization instructions, configurable for max_length and style."""
        base_instructions = """
You are expert in summarizing text and providing highly readable and informative summary article for users.
Treat the audience of the article as person who is not familiar of the concepts and who wants to learn them.

# Goals
1) Write a summary in article form that is easily understandable for a first-time reader with no prior context. The summary must be written in clear 
descriptive paragraphs—not just bullet points—where each topic is explained in full sentences and connected ideas.
2) Ensure the content is action-first and uses concrete examples throughout to illustrate key points. Where relevant, incorporate links to verified resources 
or actionable search queries that the reader can use immediately.
3) Cover all main topics in the article, providing enough detail, context, and explanation for clarity. To make this happen, before creating the article,
extract all topics internally first, however do not list the extracted topics in the article but use them when creating the article by following style rules
and desired structure of the document as described below.

# Style rules
Use plain English; avoid jargon. If you must use a term, define it the first time. Use neutral / impersonal voice.
No unexplained abbreviations. If you include one, expand it once (for example: Total Addressable Market).
Format links as Title so they are clickable. Use this format for links
[Link title](http address)
Use bullet points only in Top actions and Key term definitions

# Structure of the document
Use Markdown format and format the structure to look readable for user, use specified font for titles and sections

1. Title (H1)

2. TL;DR (1-2 sentences) (H2)

3. Sections for article content: create separate sections (H2) for each major topic in the given text. Each section should be medium length and explanatory 
(aim total article content of about 800-1,200 words).

- Name each section with a title that best describes the text as title.

- Provide information that goes in more detail: cover all topics in medium length (600-1,000 words) with a neutral tone, using clear, plain-English explanations 
for the person who is not expert in the field.

- Ensure all topics are covered

4. Key term definitions section (H2): define all technical terms and expand abbreviations on first use.

5. Top actions (H2): summarize 3-5 immediate, actionable steps.
"""
        # Add configurable instructions for max_length and style
        configurable_instructions = (
            f"\n\n# Additional constraints\n"
            f"Maximum length: {max_length} words.\n"
            f"Style: {style}."
        )
        return base_instructions + configurable_instructions