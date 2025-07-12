"""LLM answer generation module"""

import re
from typing import List, Dict, Generator, Optional
import openai


class LLMGenerator:
    """Generate answers using OpenAI LLM"""

    def __init__(
        self, client: openai.OpenAI, model: str = "gpt-4", temperature: float = 0.1
    ):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_context_length = 2000
        self.max_content_length = 600
        self.max_tokens = 800

    def _prepare_context(self, contexts: List[Dict]) -> str:
        """Prepare context text from relevant documents"""
        if not contexts:
            return ""

        # Sort by relevance
        contexts.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        context_text = ""
        for ctx in contexts[:3]:  # Top 3 most relevant
            entry = self._format_context_entry(ctx)
            if len(context_text) + len(entry) > self.max_context_length:
                break
            context_text += entry

        return context_text

    def _format_context_entry(self, ctx: Dict) -> str:
        """Format a single context entry"""
        law_name = ctx.get("law_name", "")
        article_ref = ctx.get("article_ref", "")
        content = ctx["content"].strip()

        if not content:
            return ""

        # Truncate long content
        if len(content) > self.max_content_length:
            content = content[: self.max_content_length] + "..."

        return f"\n{law_name} - {article_ref}:\n{content}\n"

    def _create_prompt(self, question: str, context_text: str) -> str:
        """Create the prompt for the LLM"""
        return f"""Azərbaycan hüquq məsləhətçisi kimi cavab verin.

Kontekst:
{context_text}

Sual: {question}

Qısa və dəqiq cavab verin. Müvafiq maddələrə istinad edin."""

    def _get_system_message(self) -> dict:
        """Get the system message for the chat completion"""
        return {
            "role": "system",
            "content": "Azərbaycan hüquq məsləhətçisisiniz. Qısa və dəqiq cavablar verin.",
        }

    def generate_answer_stream(
        self, question: str, contexts: List[Dict]
    ) -> Generator[str, None, None]:
        """Generate answer using OpenAI LLM with streaming"""
        if not contexts:
            yield "Bu sual üçün uyğun məlumat tapılmadı."
            return

        context_text = self._prepare_context(contexts)
        prompt = self._create_prompt(question, context_text)

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    self._get_system_message(),
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception:
            yield self._generate_fallback_answer(question, contexts)

    def generate_answer(self, question: str, contexts: List[Dict]) -> str:
        """Generate answer using OpenAI LLM"""
        if not contexts:
            return "Bu sual üçün uyğun məlumat tapılmadı."

        context_text = self._prepare_context(contexts)
        prompt = self._create_prompt(question, context_text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    self._get_system_message(),
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False,
            )
            return response.choices[0].message.content

        except Exception:
            return self._generate_fallback_answer(question, contexts)

    def _generate_fallback_answer(self, question: str, contexts: List[Dict]) -> str:
        """Generate answer without LLM (fallback)"""
        if not contexts:
            return "Bu sual üçün uyğun məlumat tapılmadı."

        contexts.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        answer_parts = ["**Azərbaycan qanunvericiliyinə əsasən:**\n"]

        for i, ctx in enumerate(contexts[:3], 1):
            law_name = ctx.get("law_name", "")
            article_ref = ctx.get("article_ref", f"Mənbə {i}")
            content = ctx["content"].strip()

            if content:
                if len(content) > 500:
                    content = content[:500] + "..."
                answer_parts.append(f"\n📋 **{law_name} - {article_ref}:**")
                answer_parts.append(f"{content}")

        answer_parts.append(
            "\n\n⚖️ **Hüquqi əsas:** Yuxarıda göstərilən qanun maddələri"
        )
        return "\n".join(answer_parts)

    @staticmethod
    def extract_article_reference(doc) -> str:
        """Extract article reference from document"""
        metadata = doc.metadata

        # Check metadata first
        if metadata.get("article_reference"):
            return metadata["article_reference"]
        if metadata.get("article_number"):
            return f"Maddə {metadata['article_number']}"

        # Extract from content
        content = doc.page_content[:200]
        patterns = [
            r"Maddə\s+(\d+(?:\.\d+)*)",
            r"(\d+(?:\.\d+)*)\s*[-–—]\s*c[iıü]\s+maddə",
            r"(\d+(?:\.\d+)*)\.\s+[A-ZƏÖÜÇĞIŞI]",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return f"Maddə {match.group(1)}"

        return None
