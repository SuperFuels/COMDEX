import unittest
from unittest.mock import patch, MagicMock
from modules.aion.dream_core import DreamCore

class TestDreamCore(unittest.TestCase):
    @patch("modules.aion.dream_core.openai.ChatCompletion.create")
    @patch("modules.aion.dream_core.get_db")
    def test_generate_dream(self, mock_get_db, mock_openai):
        # Mock OpenAI response
        mock_openai.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Insightful growth and learning."))]
        )

        # Mock DB session
        mock_session = MagicMock()
        mock_get_db.return_value = iter([mock_session])

        # Instantiate DreamCore and inject fake memories
        core = DreamCore()
        core.memory.get_all = MagicMock(return_value=[
            {"label": "experience", "content": "A meaningful interaction with a human."}
        ])

        # Run generate_dream
        result = core.generate_dream()

        self.assertIsNotNone(result)
        self.assertIn("Insightful", result)
        self.assertTrue(core.is_valid_dream(result))
        print("\n✅ DreamCore test passed.")

if __name__ == '__main__':
    unittest.main()