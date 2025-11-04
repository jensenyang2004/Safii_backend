import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# This allows importing from the 'backend' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.firebase import check_user_and_rate_limit, add_successful_call_log

class TestFirebaseUtils(unittest.TestCase):

    @patch('src.firebase.db')
    def test_check_user_and_rate_limit_user_not_found(self, mock_db):
        """Test case for a user that does not exist."""
        user_id = "unknown_user"
        
        mock_user_doc = MagicMock()
        mock_user_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        result = check_user_and_rate_limit(user_id)
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'User not found')
        self.assertEqual(result['code'], 401)
        mock_db.collection.assert_called_with('users')
        mock_db.collection.return_value.document.assert_called_with(user_id)

    @patch('src.firebase.db')
    def test_check_user_and_rate_limit_under_limit(self, mock_db):
        """Test case for a user that is under the rate limit."""
        user_id = "jensen_123"
        
        mock_user_doc = MagicMock()
        mock_user_doc.exists = True
        
        mock_session_doc = MagicMock()
        mock_session_doc.exists = True
        
        mock_logs = [MagicMock()] * 5 # 5 logs
        mock_db.collection.return_value.document.return_value.get.side_effect = [mock_user_doc, mock_session_doc]
        mock_db.collection.return_value.document.return_value.collection.return_value.limit.return_value.get.return_value = mock_logs
        
        result = check_user_and_rate_limit(user_id, limit=10)
        
        self.assertEqual(result['status'], 'success')
        
    @patch('src.firebase.db')
    def test_check_user_and_rate_limit_at_limit(self, mock_db):
        """Test case for a user that is at the rate limit."""
        user_id = "jensen_123"
        
        mock_user_doc = MagicMock()
        mock_user_doc.exists = True
        
        mock_session_doc = MagicMock()
        mock_session_doc.exists = True
        
        mock_logs = [MagicMock()] * 10 # 10 logs
        mock_db.collection.return_value.document.return_value.get.side_effect = [mock_user_doc, mock_session_doc]
        mock_db.collection.return_value.document.return_value.collection.return_value.limit.return_value.get.return_value = mock_logs
        
        result = check_user_and_rate_limit(user_id, limit=10)
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Rate limit exceeded')
        self.assertEqual(result['code'], 429)

    @patch('src.firebase.db')
    def test_check_user_and_rate_limit_no_session(self, mock_db):
        """Test case for a user with no session document (0 logs)."""
        user_id = "jensen_123"
        
        mock_user_doc = MagicMock()
        mock_user_doc.exists = True
        
        mock_session_doc = MagicMock()
        mock_session_doc.exists = False # No session
        
        mock_db.collection.return_value.document.return_value.get.side_effect = [mock_user_doc, mock_session_doc]
        
        result = check_user_and_rate_limit(user_id, limit=10)
        
        self.assertEqual(result['status'], 'success')

    @patch('src.firebase.db')
    @patch('src.firebase.firestore.SERVER_TIMESTAMP')
    def test_add_successful_call_log_new_session(self, mock_timestamp, mock_db):
        """Test adding a log when no session exists."""
        user_id = "jensen_123"
        
        mock_session_doc = MagicMock()
        mock_session_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_session_doc
        
        result = add_successful_call_log(user_id)
        
        self.assertTrue(result)
        
        mock_db.collection.assert_any_call('PhoneCallSessions')
        session_doc_ref = mock_db.collection.return_value.document.return_value
        session_doc_ref.set.assert_called_once()
        
        log_collection_ref = session_doc_ref.collection.return_value
        log_collection_ref.add.assert_called_once()
        
    @patch('src.firebase.db')
    @patch('src.firebase.firestore.SERVER_TIMESTAMP')
    def test_add_successful_call_log_existing_session(self, mock_timestamp, mock_db):
        """Test adding a log when a session already exists."""
        user_id = "jensen_123"
        
        mock_session_doc = MagicMock()
        mock_session_doc.exists = True
        mock_db.collection.return_value.document.return_value.get.return_value = mock_session_doc
        
        result = add_successful_call_log(user_id)
        
        self.assertTrue(result)
        
        session_doc_ref = mock_db.collection.return_value.document.return_value
        session_doc_ref.set.assert_not_called()
        
        log_collection_ref = session_doc_ref.collection.return_value
        log_collection_ref.add.assert_called_once()

if __name__ == '__main__':
    unittest.main()