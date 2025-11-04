import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import time

cred = credentials.Certificate("/Users/yangjingcheng/Downloads/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Get a client instance for Firestore
db = firestore.client()

# --- New Workflow Function ---

def process_user_call_request(user_id):
    """
    Processes a new call request for a given user_id.
    1. Verifies user exists in 'users' collection.
    2. Prints all user data.
    3. Creates a new entry in 'PhoneCallSessions' with user_id as doc ID.
    4. Adds a new log to the 'RequestLog' subcollection of that session.
    """
    print(f"\n--- Processing request for User ID: {user_id} ---")
    
    # 1. Verify user in Firestore and 2. Read their data
    user_doc_ref = db.collection('users').document(user_id)
    
    try:
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            print(f"Error: User not found with ID: {user_id}")
            print("Request processing stopped.")
            return False
            
        # 2. Read and print all columns (fields) for the user
        print(f"Success: Found user.")
        user_data = user_doc.to_dict()
        print(f"User Data for {user_id}:")
        for key, value in user_data.items():
            print(f"  - {key}: {value}")
            
    except Exception as e:
        print(f"Error reading user document: {e}")
        return False
        
    # 3. Create an entry in 'PhoneCallSessions'
    # We will use the user_id as the document ID for the new session
    try:
        session_doc_ref = db.collection('PhoneCallSessions').document(user_id)
        
        # We set some initial data for the session document
        session_data = {
            "status": "initiated",
            "user_id_ref": user_doc_ref, # Store a reference to the user
            "session_start_time": firestore.SERVER_TIMESTAMP
        }
        session_doc_ref.set(session_data)
        print(f"\nCreated session entry: /PhoneCallSessions/{user_id}")

        # 4. Add a log under that entry's 'RequestLog' subcollection
        log_entry_data = {
            "Time": firestore.SERVER_TIMESTAMP,
            "type": "initial_request"
        }
        
        # Add a new document with an auto-generated ID to the subcollection
        log_ref = session_doc_ref.collection('RequestLog').add(log_entry_data)
        
        print(f"Added log entry to subcollection: /PhoneCallSessions/{user_id}/RequestLog/")
        print("--- Request processed successfully ---")
        return True
        
    except Exception as e:
        print(f"Error creating session or log: {e}")
        return False


# --- Example Usage ---

def check_user_and_rate_limit(user_id, limit=10):
    """
    Checks if a user exists and if they are within their call rate limit.
    1. Verifies user exists in 'users' collection.
    2. Checks the number of logs in 'PhoneCallSessions/{user_id}/RequestLog'.
    3. Returns a status indicating success or failure.
    """
    print(f"\n--- Checking auth and rate limit for User ID: {user_id} ---")

    # 1. Verify user in Firestore
    user_doc_ref = db.collection('users').document(user_id)
    try:
        user_doc = user_doc_ref.get()
        if not user_doc.exists:
            print(f"Auth Error: User not found with ID: {user_id}")
            return {"status": "error", "message": "User not found", "code": 401}
    except Exception as e:
        print(f"Error reading user document: {e}")
        return {"status": "error", "message": f"Database error: {e}", "code": 500}

    print("Success: Found user.")

    # 2. Check rate limit
    session_doc_ref = db.collection('PhoneCallSessions').document(user_id)
    session_doc = session_doc_ref.get()

    if session_doc.exists:
        try:
            logs_collection_ref = session_doc_ref.collection('RequestLog')
            logs = logs_collection_ref.limit(limit).get() # Get up to limit documents

            log_count = len(logs)
            print(f"User has {log_count} logs.")

            if log_count >= limit:
                print(f"Rate Limit Error: User has {log_count} logs, which is >= the limit of {limit}.")
                return {"status": "error", "message": "Rate limit exceeded", "code": 429}

        except Exception as e:
            # This would be an unexpected error.
            print(f"Error querying logs for user {user_id}: {e}")
            return {"status": "error", "message": f"Database error while checking logs: {e}", "code": 500}
    # If session_doc doesn't exist, log_count is 0, so we pass.

    print("--- User is authenticated and within rate limits ---")
    return {"status": "success"}


def add_successful_call_log(user_id):
    """
    Adds a log for a successful call to 'PhoneCallSessions/{user_id}/RequestLog'.
    Creates the session document if it doesn't exist.
    """
    print(f"\n--- Logging successful call for User ID: {user_id} ---")

    try:
        session_doc_ref = db.collection('PhoneCallSessions').document(user_id)
        session_doc = session_doc_ref.get()

        if not session_doc.exists:
            print(f"No session found for {user_id}, creating a new one.")
            user_doc_ref = db.collection('users').document(user_id)
            session_data = {
                "status": "initiated",
                "user_id_ref": user_doc_ref,
                "session_start_time": firestore.SERVER_TIMESTAMP
            }
            session_doc_ref.set(session_data) # use set instead of merge

        log_entry_data = {
            "Time": firestore.SERVER_TIMESTAMP,
            "type": "successful_openai_session"
        }
        session_doc_ref.collection('RequestLog').add(log_entry_data)

        print(f"Added successful call log to /PhoneCallSessions/{user_id}/RequestLog/")
        print("--- Logging complete ---")
        return True

    except Exception as e:
        print(f"Error logging successful call: {e}")
        return False

if __name__ == "__main__":
    
    # --- Setup: Let's first create a user to make sure one exists ---
    # This is just for testing, you can comment this out if you
    # already have a user "jensen_123" in your database.
    print("--- Setting up test user... ---")
    setup_user_id = "jensen_123"
    setup_user_info = {
        "name": "Jensen",
        "email": "jensen@example.com",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "premiumMember": True
    }
    try:
        db.collection('users').document(setup_user_id).set(setup_user_info)
        print(f"Test user '{setup_user_id}' created/updated.")
    except Exception as e:
        print(f"Error setting up test user: {e}")
    # --- End of setup ---
    
    
    # Give Firestore a moment to process the write
    time.sleep(1) 
    
    
    # --- Run the new workflow ---
    # This will succeed because we just created the user
    process_user_call_request(setup_user_id)
    
    # --- Run with a non-existent user ---
    # This will fail at the first step, as intended
    process_user_call_request("unknown_user_789")

