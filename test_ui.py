"""Exercise actual Streamlit workflows with its supported test harness."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class WorkbenchUI(unittest.TestCase):
    def test_demo_workflows(self):
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run(timeout=30)
        self.assertFalse(app.exception)
        for label in ['Run audio comparison', 'Train MPG model']:
            next(b for b in app.button if b.label == label).click().run(timeout=60)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
        for text in ['ADD-DRIVER kamal (0,0) BIKE','CREATE-ORDER BIKE (1,1) (4,5)','RECEIVE-ORDER (1,1) (4,5) kamal']:
            next(t for t in app.text_input if t.label == 'Command').set_value(text)
            next(b for b in app.button if b.label == 'Execute command').click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
        self.assertEqual(len(app.session_state['transport'].completed), 1)

if __name__ == '__main__':
    unittest.main()
