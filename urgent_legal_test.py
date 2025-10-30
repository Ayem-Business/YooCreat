#!/usr/bin/env python3
"""
URGENT TEST: Legal Mentions Save Button Fix
Tests the specific fix for [object Object] error when saving legal mentions
"""

import httpx
import json
import asyncio
import sys
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://smartwriter-2.preview.emergentagent.com/api"

class UrgentLegalTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.auth_token = None
        self.user_id = None
        self.test_ebook_id = None
        
    async def cleanup(self):
        await self.client.aclose()
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def setup_test_environment(self):
        """Quick setup: register user and create ebook"""
        self.log("Setting up test environment...")
        
        # Generate unique test user
        timestamp = str(int(datetime.now().timestamp()))
        test_email = f"urgenttest_{timestamp}@example.com"
        test_username = f"urgenttest_{timestamp}"
        test_password = "TestPassword123!"
        
        try:
            # Register user
            register_data = {
                "username": test_username,
                "email": test_email,
                "password": test_password
            }
            
            response = await self.client.post(f"{BACKEND_URL}/auth/register", json=register_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("token")
                self.user_id = data.get("user", {}).get("id")
                self.log(f"✅ User registered - ID: {self.user_id}")
            else:
                self.log(f"❌ Registration failed: {response.status_code} - {response.text}", "ERROR")
                return False
            
            # Create ebook
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            ebook_data = {
                "author": "Test Author",
                "title": "Legal Test Book",
                "tone": "Professional",
                "target_audience": ["Adults"],
                "description": "Test book for legal mentions fix",
                "chapters_count": 2,
                "length": "Short"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/create", json=ebook_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.test_ebook_id = data.get("ebook_id")
                self.log(f"✅ Ebook created - ID: {self.test_ebook_id}")
                return True
            else:
                self.log(f"❌ Ebook creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Setup error: {str(e)}", "ERROR")
            return False
    
    async def test_legal_mentions_fix(self):
        """Test the URGENT fix for legal mentions save button"""
        self.log("=== TESTING URGENT LEGAL MENTIONS FIX ===")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Step 1: Generate initial legal pages
            self.log("Step 1: Generating initial legal pages...")
            legal_gen_data = {
                "ebook_id": self.test_ebook_id,
                "year": 2025,
                "edition": "Première édition"
            }
            
            gen_response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-legal-pages", json=legal_gen_data, headers=headers)
            
            if gen_response.status_code != 200:
                self.log(f"❌ Failed to generate legal pages: {gen_response.status_code} - {gen_response.text}", "ERROR")
                return False
            
            self.log("✅ Initial legal pages generated successfully")
            
            # Step 2: Test the update with JSON body (the fix)
            self.log("Step 2: Testing legal pages update with JSON body...")
            
            update_data = {
                "ebook_id": self.test_ebook_id,
                "copyright_page": "© 2025 Test Author\nDroits réservés.",
                "legal_mentions": "Protection de la propriété intellectuelle : Ce livre est protégé."
            }
            
            self.log(f"Sending POST to /api/ebooks/update-legal-pages")
            self.log(f"Request body: {json.dumps(update_data, indent=2)}")
            
            update_response = await self.client.post(f"{BACKEND_URL}/ebooks/update-legal-pages", json=update_data, headers=headers)
            
            self.log(f"Response status: {update_response.status_code}")
            self.log(f"Response body: {update_response.text}")
            
            # Step 3: Verify the response
            if update_response.status_code == 200:
                try:
                    response_data = update_response.json()
                    
                    # Check for expected response format
                    if response_data.get("success") == True:
                        self.log("✅ Response contains success: true")
                    else:
                        self.log(f"❌ Response missing success=true: {response_data}", "ERROR")
                        return False
                    
                    expected_message = "Legal pages updated successfully"
                    actual_message = response_data.get("message", "")
                    if expected_message in actual_message:
                        self.log(f"✅ Response contains expected message: '{actual_message}'")
                    else:
                        self.log(f"❌ Unexpected message: '{actual_message}'", "ERROR")
                        return False
                    
                    # Check for [object Object] error
                    response_text = update_response.text
                    if "[object Object]" in response_text:
                        self.log("❌ CRITICAL: [object Object] error still present in response!", "ERROR")
                        return False
                    else:
                        self.log("✅ No [object Object] errors found in response")
                    
                except json.JSONDecodeError:
                    self.log(f"❌ Response is not valid JSON: {update_response.text}", "ERROR")
                    return False
                
            else:
                self.log(f"❌ Update request failed with status {update_response.status_code}", "ERROR")
                
                # Check if this is the old [object Object] error
                response_text = update_response.text
                if "[object Object]" in response_text:
                    self.log("❌ CRITICAL: [object Object] error detected - fix not working!", "ERROR")
                else:
                    self.log(f"❌ Different error: {response_text}", "ERROR")
                
                return False
            
            # Step 4: Verify data persistence
            self.log("Step 3: Verifying data persistence...")
            
            get_response = await self.client.get(f"{BACKEND_URL}/ebooks/{self.test_ebook_id}", headers=headers)
            
            if get_response.status_code == 200:
                ebook_data = get_response.json()
                legal_pages = ebook_data.get("legal_pages", {})
                
                # Check if our updates were saved
                saved_copyright = legal_pages.get("copyright_page", "")
                saved_legal_mentions = legal_pages.get("legal_mentions", "")
                
                if update_data["copyright_page"] in saved_copyright:
                    self.log("✅ Copyright page properly saved in MongoDB")
                else:
                    self.log(f"❌ Copyright page not saved. Expected: '{update_data['copyright_page']}', Got: '{saved_copyright}'", "ERROR")
                    return False
                
                if update_data["legal_mentions"] in saved_legal_mentions:
                    self.log("✅ Legal mentions properly saved in MongoDB")
                else:
                    self.log(f"❌ Legal mentions not saved. Expected: '{update_data['legal_mentions']}', Got: '{saved_legal_mentions}'", "ERROR")
                    return False
                
                self.log("✅ All data properly persisted in database")
                return True
            else:
                self.log(f"❌ Failed to retrieve ebook for verification: {get_response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Test error: {str(e)}", "ERROR")
            import traceback
            self.log(f"Full traceback: {traceback.format_exc()}", "ERROR")
            return False
    
    async def run_urgent_test(self):
        """Run the urgent legal mentions fix test"""
        self.log("=== URGENT LEGAL MENTIONS SAVE BUTTON FIX TEST ===")
        self.log(f"Backend URL: {BACKEND_URL}")
        
        # Setup
        if not await self.setup_test_environment():
            self.log("❌ Test environment setup failed", "ERROR")
            return False
        
        # Run the fix test
        success = await self.test_legal_mentions_fix()
        
        # Results
        self.log("\n=== TEST RESULTS ===")
        if success:
            self.log("🎉 URGENT FIX VERIFIED: Legal mentions save button working correctly!")
            self.log("✅ No [object Object] errors")
            self.log("✅ JSON body properly parsed by backend")
            self.log("✅ Data properly saved to MongoDB")
            self.log("✅ Expected response format returned")
            return True
        else:
            self.log("❌ URGENT FIX FAILED: Legal mentions save button still has issues")
            return False

async def main():
    """Main test execution"""
    tester = UrgentLegalTester()
    
    try:
        success = await tester.run_urgent_test()
        return 0 if success else 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)