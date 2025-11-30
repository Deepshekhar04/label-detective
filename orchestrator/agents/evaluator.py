"""
Evaluator Agent - Automated output assessment for quality control.
"""

import os
import json
from typing import Dict, Any
from utils.logging_utils import get_logger

logger = get_logger("agents.evaluator")


class EvaluatorAgent:
    """Evaluates agent output against golden answers or rubrics."""

    def evaluate(
        self, agent_output: Dict[str, Any], expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate scan result against expected output using LLM-based judgment."""
        return self._evaluate_with_llm(agent_output, expected)

    def _evaluate_with_llm(
        self, agent_output: Dict[str, Any], expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate using GenAI LLM."""
        try:
            import google.generativeai as genai

            api_key = os.getenv("GENAI_API_KEY")
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel("gemini-pro")

            prompt = f"""You are an expert evaluator for a food label analysis system.

Agent's Output:
- Verdict: {agent_output.get('verdict', 'N/A')}
- Conflicts: {json.dumps(agent_output.get('conflicts', []), indent=2)}

Expected Output:
- Verdict: {expected.get('expected_verdict', 'N/A')}
- Expected Flags: {json.dumps(expected.get('expected_ingredient_flags', {}), indent=2)}

Evaluation Criteria:
1. Verdict Accuracy (50 points): Does the verdict match? (safe/caution/avoid)
2. Ingredient Identification (30 points): Were the correct ingredients flagged?
3. Evidence Quality (20 points): Are explanations and evidence reasonable?

Provide your evaluation as a JSON object:
{{
    "score": <0-100>,
    "feedback": "<brief explanation>",
    "discrepancies": ["<list of issues>"]
}}

Output only valid JSON, no other text.
"""

            response = model.generate_content(prompt)
            result_text = response.text.strip()

            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("`")[1].split("```")[0].strip()

            result = json.loads(result_text)

            logger.info(f"LLM evaluation score: {result.get('score', 0)}")
            return result

        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            raise
