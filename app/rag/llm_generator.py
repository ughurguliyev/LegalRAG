"""LLM answer generation module"""

import re
from typing import List, Dict
import openai


class LLMGenerator:
    """Generate answers using OpenAI LLM"""

    def __init__(
        self, client: openai.OpenAI, model: str = "gpt-4", temperature: float = 0.1
    ):
        self.client = client
        self.model = model
        self.temperature = temperature

    def generate_answer(self, question: str, contexts: List[Dict]) -> str:
        """Generate answer using OpenAI LLM"""
        if not contexts:
            return "Bu sual üçün uyğun məlumat tapılmadı."

        # Sort by relevance
        contexts.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Prepare context
        context_text = ""
        for ctx in contexts[:3]:  # Top 3 most relevant
            law_name = ctx.get("law_name", "")
            article_ref = ctx.get("article_ref", "")
            content = ctx["content"].strip()

            if content:
                context_text += f"\n{law_name} - {article_ref}:\n{content}\n"

        # Create prompt
        prompt = f"""Siz Azərbaycan hüquq məsləhətçisisiniz. 
Aşağıdakı kontekst əsasında istifadəçinin sualına aydın və strukturlaşdırılmış cavab verin.
Yalnız qüvvədə olan (ləğv edilməmiş) qanunlara istinad edin.

Kontekst (Azərbaycan qanunvericiliyindən):
{context_text}

Sual: {question}

Cavab verərkən:
1. Birbaşa və aydın cavab verin
2. Müvafiq qanun və maddələrə istinad edin
3. Əsas məlumatları bullet points ilə göstərin
4. Hüquqi terminləri sadə dillə izah edin

Cavab:"""

        try:
            # Generate answer
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Siz Azərbaycan hüquq məsləhətçisisiniz.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=1000,
            )

            return response.choices[0].message.content

        except Exception:
            # Fallback to context-based answer
            return self._generate_fallback_answer(question, contexts)

    def _generate_fallback_answer(self, question: str, contexts: List[Dict]) -> str:
        """Generate answer without LLM (fallback)"""
        if not contexts:
            return "Bu sual üçün uyğun məlumat tapılmadı."

        # Sort by relevance
        contexts.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Create answer from contexts
        answer_parts = ["**Azərbaycan qanunvericiliyinə əsasən:**\n"]

        for i, ctx in enumerate(contexts[:3], 1):
            law_name = ctx.get("law_name", "")
            article_ref = ctx.get("article_ref", f"Mənbə {i}")
            content = ctx["content"].strip()

            if content:
                # Truncate long content
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

        # Try to get from metadata first
        if metadata.get("article_reference"):
            return metadata["article_reference"]

        if metadata.get("article_number"):
            return f"Maddə {metadata['article_number']}"

        # Try to extract from content
        content = doc.page_content[:200]  # First 200 chars
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
