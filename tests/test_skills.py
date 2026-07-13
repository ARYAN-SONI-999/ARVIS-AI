import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add root folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from skills.calculator import evaluate_formula
from skills.system_info import get_system_stats
from skills.file_manager import create_file, read_file, delete_file, list_files

class TestSkills(unittest.TestCase):
    def test_calculator(self):
        # Basic calculations
        self.assertIn("Result: 4", evaluate_formula("2 + 2"))
        self.assertIn("Result: 10", evaluate_formula("sqrt(100)"))
        # Unsafe blocking
        self.assertIn("Error", evaluate_formula("import os; os.system('ls')"))
        self.assertIn("Error", evaluate_formula("__import__('os').system('ls')"))

    def test_system_info(self):
        stats = get_system_stats()
        self.assertIn("CPU Usage", stats)
        self.assertIn("RAM Usage", stats)

    def test_file_manager(self):
        test_file = "temp_test_file.txt"
        test_content = "Hello, ARVIS testing!"
        
        # Test Create
        create_res = create_file(test_file, test_content)
        self.assertIn("successfully", create_res)
        
        # Test Read
        read_res = read_file(test_file)
        self.assertIn(test_content, read_res)
        
        # Test Delete
        delete_res = delete_file(test_file)
        self.assertIn("deleted successfully", delete_res)

    @patch('requests.get')
    def test_web_reader(self, mock_get):
        from skills.web_reader import browse_url
        mock_response = MagicMock()
        mock_response.text = "<html><body><header>Nav</header><article>Article content</article></body></html>"
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        res = browse_url("https://example.com")
        self.assertIn("Article content", res)
        self.assertNotIn("Nav", res)

    @patch('pyautogui.screenshot')
    @patch('requests.post')
    def test_vision(self, mock_post, mock_screenshot):
        from skills.vision import analyze_screen
        import config
        # Create a dummy image file on disk so the file reader doesn't fail
        os.makedirs(config.TEMP_DIR, exist_ok=True)
        temp_img_path = os.path.join(config.TEMP_DIR, "vision_temp.png")
        with open(temp_img_path, "wb") as f:
            f.write(b"dummy_image_data")

        # Mock screenshot save
        mock_img = MagicMock()
        mock_screenshot.return_value = mock_img
        
        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Visual analysis output"}]
                }
            }]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Ensure we have a mock API key to bypass key check
        old_key = getattr(config, 'GEMINI_API_KEY', '')
        config.GEMINI_API_KEY = "mock_key"
        
        try:
            res = analyze_screen("What is on screen?")
            self.assertEqual(res, "Visual analysis output")
        finally:
            config.GEMINI_API_KEY = old_key

    @patch('agent.brain.ArvisBrain.execute_react_loop')
    def test_multi_agent(self, mock_loop):
        from skills.multi_agent import delegate_task
        mock_loop.return_value = [{"type": "final_answer", "content": "Sub-agent result"}]
        
        res = delegate_task("coder", "write tests")
        self.assertEqual(res, "Sub-agent result")

if __name__ == "__main__":
    unittest.main()
