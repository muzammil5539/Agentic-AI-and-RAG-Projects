"""Tests for custom tools — calculator, weather, datetime."""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pytest
from tools.calculator import calculator
from tools.datetime_tool import datetime_tool


class TestCalculator:
    def test_basic_addition(self):
        result = calculator.invoke({"expression": "2 + 3"})
        assert result == "5"

    def test_multiplication(self):
        result = calculator.invoke({"expression": "7 * 8"})
        assert result == "56"

    def test_parentheses(self):
        result = calculator.invoke({"expression": "(2 + 3) * 4"})
        assert result == "20"

    def test_division(self):
        result = calculator.invoke({"expression": "10 / 3"})
        assert "3.33" in result

    def test_power(self):
        result = calculator.invoke({"expression": "2 ** 10"})
        assert result == "1024"

    def test_sqrt(self):
        result = calculator.invoke({"expression": "sqrt(144)"})
        assert result == "12"

    def test_pi_constant(self):
        result = calculator.invoke({"expression": "pi"})
        assert "3.14" in result

    def test_divide_by_zero(self):
        result = calculator.invoke({"expression": "1 / 0"})
        assert "Error" in result

    def test_invalid_expression(self):
        result = calculator.invoke({"expression": "import os"})
        assert "Error" in result

    def test_nested_functions(self):
        result = calculator.invoke({"expression": "abs(-5)"})
        assert result == "5"


class TestDatetime:
    def test_now(self):
        result = datetime_tool.invoke({"action": "now"})
        assert "Current date/time" in result

    def test_now_with_timezone(self):
        result = datetime_tool.invoke(
            {"action": "now", "timezone_name": "America/New_York"}
        )
        assert "America/New_York" in result

    def test_add_days(self):
        result = datetime_tool.invoke(
            {"action": "add", "date_string": "2026-01-01", "days": 30}
        )
        assert "Result" in result
        assert "2026-01-31" in result

    def test_diff(self):
        result = datetime_tool.invoke(
            {
                "action": "diff",
                "date_string": "2026-01-01",
                "end_date": "2026-01-31",
            }
        )
        assert "30 days" in result

    def test_list_timezones(self):
        result = datetime_tool.invoke({"action": "list_timezones"})
        assert "America/" in result

    def test_convert(self):
        result = datetime_tool.invoke(
            {
                "action": "convert",
                "timezone_name": "UTC",
                "target_timezone": "Asia/Tokyo",
                "date_string": "2026-06-15T12:00:00",
            }
        )
        assert "Asia/Tokyo" in result

    def test_unknown_action(self):
        result = datetime_tool.invoke({"action": "foo"})
        assert "Unknown action" in result
