import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add root folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.brain import ArvisBrain
from agent.task_router import TaskRouter

class TestBrain(unittest.TestCase):
    def test_json_parsing_fallback(self):
        brain = ArvisBrain(session_id="test")
        
        # Test clean JSON parsing
        json_str = '{"thought": "test", "final_answer": "done"}'
        res = brain.parse_json_fallback(json_str)
        self.assertEqual(res["final_answer"], "done")
        
        # Test markdown codeblocks wrapper JSON parsing fallback
        markdown_str = '```json\n{"thought": "test", "final_answer": "done"}\n```'
        res = brain.parse_json_fallback(markdown_str)
        self.assertEqual(res["final_answer"], "done")
        
        # Test raw text wrapping JSON
        wrapped_str = 'Here is the JSON: {"thought": "test", "final_answer": "done"} hope this helps!'
        res = brain.parse_json_fallback(wrapped_str)
        self.assertEqual(res["final_answer"], "done")

    @patch('agent.brain.ArvisBrain.check_local_task')
    @patch('agent.brain.ArvisBrain.has_any_valid_key')
    @patch('agent.brain.ArvisBrain.get_cached_response')
    @patch('agent.brain.ArvisBrain.call_ai_smart')
    def test_react_loop_single_tool_execution(self, mock_ai_call, mock_cache, mock_valid_key, mock_local_task):
        mock_cache.return_value = None
        mock_valid_key.return_value = True
        mock_local_task.return_value = None
        # Setup mock behavior:
        # Step 1: AI decides to run evaluate_formula
        # Step 2: AI returns final answer based on tool output
        mock_ai_call.side_effect = [
            '{"thought": "I need to compute 10+20", "tool": "evaluate_formula", "args": {"formula": "10 + 20"}}',
            '{"thought": "Result is computed", "final_answer": "The sum is 30"}'
        ]
        
        router = TaskRouter()
        brain = ArvisBrain(session_id="test_run", task_router=router)
        
        events = list(brain.execute_react_loop("Calculate 10 + 20"))
        
        # Verify event stream
        event_types = [e["type"] for e in events]
        self.assertIn("thought_start", event_types)
        self.assertIn("thought", event_types)
        self.assertIn("tool_call", event_types)
        self.assertIn("tool_result", event_types)
        self.assertIn("final_answer", event_types)
        
        # Verify result content
        final_answ_event = [e for e in events if e["type"] == "final_answer"][0]
        self.assertEqual(final_answ_event["content"], "The sum is 30")

if __name__ == "__main__":
    # Ensure database doesn't lock for testing
    unittest.main()
