"""
Calculator plugin for VoicePilot-CLI.

Provides mathematical calculation capabilities including
basic arithmetic, common functions, and expression evaluation.
"""

import math
import re
from typing import Any, Dict, List

from voicepilot_cli.plugins.base import PluginBase


class CalculatorPlugin(PluginBase):
    """Calculator plugin for mathematical expressions.

    Supports basic arithmetic (+, -, *, /, ^, %), parentheses,
    common math functions (sqrt, sin, cos, tan, log, etc.),
    and constants (pi, e).
    """

    # Safe math functions available for evaluation
    SAFE_FUNCTIONS = {
        "sqrt": math.sqrt,
        "abs": abs,
        "round": round,
        "pow": pow,
        "min": min,
        "max": max,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "ceil": math.ceil,
        "floor": math.floor,
        "factorial": math.factorial,
        "degrees": math.degrees,
        "radians": math.radians,
    }

    SAFE_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "inf": math.inf,
    }

    @property
    def name(self) -> str:
        """Get plugin name.

        Returns:
            'calculator'
        """
        return "calculator"

    @property
    def description(self) -> str:
        """Get plugin description.

        Returns:
            Description string.
        """
        return "Mathematical expression calculator. Supports arithmetic, functions, and constants."

    @property
    def trigger_keywords(self) -> List[str]:
        """Get trigger keywords.

        Returns:
            List of keywords that trigger this plugin.
        """
        return [
            "计算", "算", "等于多少", "多少",
            "calculate", "compute", "math",
            "加", "减", "乘", "除",
            "平方", "开方", "平方根",
            "sin", "cos", "tan", "log",
        ]

    @property
    def commands(self) -> List[str]:
        """Get supported commands.

        Returns:
            List of command strings.
        """
        return ["calc", "calculate", "math"]

    def execute(self, command: str, **kwargs: Any) -> str:
        """Execute a calculation.

        Args:
            command: Mathematical expression or natural language calculation request.
            **kwargs: Additional parameters (may include 'expression').

        Returns:
            Calculation result as a formatted string.
        """
        # If called with explicit expression parameter
        expression = kwargs.get("expression", "")
        if expression:
            return self._evaluate_and_format(expression)

        # Try to extract expression from natural language
        expression = self._extract_expression(command)
        if expression:
            return self._evaluate_and_format(expression)

        return ""

    def _extract_expression(self, text: str) -> str:
        """Extract a mathematical expression from natural language text.

        Handles both direct expressions and Chinese number descriptions.

        Args:
            text: Input text containing a math expression.

        Returns:
            Extracted expression string or empty string.
        """
        # Remove common prefixes/suffixes
        text = re.sub(r"^(计算|算|calculate|compute|请|帮我)\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*(等于多少|是多少|=\?)\s*$", "", text)

        # Replace Chinese operators
        text = text.replace("加", "+").replace("减", "-")
        text = text.replace("乘以", "*").replace("乘", "*")
        text = text.replace("除以", "/").replace("除", "/")
        text = text.replace("的平方", "**2").replace("的立方", "**3")
        text = text.replace("平方根", "sqrt").replace("开方", "sqrt")
        text = text.replace("×", "*").replace("÷", "/")

        # Replace Chinese number words
        text = self._replace_chinese_numbers(text)

        # Try to find a mathematical expression
        # Match patterns like: 2+3, (1+2)*3, sqrt(16), etc.
        patterns = [
            r"[\d\.\,]+[\s]*[\+\-\*\/\%\^][\s]*[\d\.\,]+(?:[\s]*[\+\-\*\/\%\^][\s]*[\d\.\,]+)*",
            r"sqrt\s*\([^)]+\)",
            r"(?:sin|cos|tan|log|log10|log2|exp)\s*\([^)]+\)",
            r"pi|e\b",
            r"\d+\s*\*\*\s*\d+",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                expr = match.group().strip()
                # Validate that it looks like a math expression
                if re.search(r"[\d\+\-\*\/\(\)\^]", expr):
                    return expr

        return ""

    def _replace_chinese_numbers(self, text: str) -> str:
        """Replace Chinese number words with digits.

        Args:
            text: Text with Chinese numbers.

        Returns:
            Text with Chinese numbers replaced.
        """
        # Simple digit replacements
        replacements = {
            "零": "0", "一": "1", "二": "2", "三": "3", "四": "4",
            "五": "5", "六": "6", "七": "7", "八": "8", "九": "9",
            "十": "10", "百": "00", "千": "000",
        }
        for cn, digit in replacements.items():
            text = text.replace(cn, digit)
        return text

    def _evaluate_and_format(self, expression: str) -> str:
        """Evaluate a mathematical expression and format the result.

        Args:
            expression: Mathematical expression string.

        Returns:
            Formatted result string.
        """
        try:
            result = self._safe_eval(expression)
            if result is None:
                return f"无法计算: {expression}"

            # Format the result
            if isinstance(result, float):
                # Check if result is close to an integer
                if result == int(result) and abs(result) < 1e15:
                    return f"{expression} = {int(result)}"
                else:
                    return f"{expression} = {result:.6g}"
            else:
                return f"{expression} = {result}"

        except ZeroDivisionError:
            return f"错误: 除以零 ({expression})"
        except (ValueError, SyntaxError) as e:
            return f"无法计算 '{expression}': {e}"
        except Exception as e:
            return f"计算错误: {e}"

    def _safe_eval(self, expression: str) -> Any:
        """Safely evaluate a mathematical expression.

        Uses only whitelisted functions and constants to prevent
        code injection.

        Args:
            expression: Mathematical expression to evaluate.

        Returns:
            Evaluation result.

        Raises:
            ValueError: If expression contains unsafe content.
        """
        # Pre-process expression
        expr = expression.strip()
        expr = expr.replace("^", "**")

        # Validate expression - only allow safe characters
        allowed_chars = set("0123456789+-*/.()%() ,abcdefghijklmnopqrstuvwxyz")
        if not all(c in allowed_chars for c in expr.lower()):
            raise ValueError("Expression contains disallowed characters")

        # Check for dangerous patterns
        dangerous = ["import", "exec", "eval", "open", "__", "class", "def"]
        for d in dangerous:
            if d in expr.lower():
                raise ValueError(f"Expression contains disallowed pattern: {d}")

        # Create safe namespace
        safe_globals: Dict[str, Any] = {"__builtins__": {}}
        safe_globals.update(self.SAFE_CONSTANTS)
        safe_globals.update(self.SAFE_FUNCTIONS)

        # Evaluate
        try:
            return eval(expr, safe_globals, {})  # noqa: S307
        except Exception as e:
            raise ValueError(f"Cannot evaluate: {e}")

    def can_handle(self, input_text: str) -> bool:
        """Check if this plugin can handle the input.

        Args:
            input_text: User input text.

        Returns:
            True if the input looks like a calculation request.
        """
        # Check trigger keywords
        if super().can_handle(input_text):
            return True

        # Check for mathematical expression patterns
        math_patterns = [
            r"\d+\s*[\+\-\*\/\^]\s*\d+",
            r"sqrt\s*\(",
            r"(?:sin|cos|tan|log)\s*\(",
        ]
        for pattern in math_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                return True

        return False
