#!/usr/bin/env python3
"""
YooCreat Backend API Testing Script - Legal Pages Only
Tests the new legal pages generation endpoint specifically
"""

import httpx
import json
import asyncio
import sys
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://smart-ebook-gen-1.preview.emergentagent.com/api"

class YooCreatLegalTester:
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
    
    async def setup_test_user_and_ebook(self):
        """Setup test user and ebook for legal pages testing"""
        self.log("Setting up test user and ebook...")
        
        # Generate unique test user
        timestamp = str(int(datetime.now().timestamp()))
        test_email = f"testuser_{timestamp}@example.com"
        test_username = f"testuser_{timestamp}"
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
                self.log(f"✅ User registration successful - User ID: {self.user_id}")
            else:
                self.log(f"❌ Registration failed: {response.status_code} - {response.text}", "ERROR")
                return False
            
            # Create ebook
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            ebook_data = {
                "author": "Marie Dubois",
                "title": "Guide Pratique de la Productivité Moderne",
                "tone": "Professionnel",
                "target_audience": ["Adultes", "Professionnels"],
                "description": "Un guide complet pour améliorer sa productivité au travail et dans la vie personnelle",
                "chapters_count": 3,
                "length": "Moyen"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/create", json=ebook_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.test_ebook_id = data.get("ebook_id")
                self.log(f"✅ Ebook created successfully - ID: {self.test_ebook_id}")
                return True
            else:
                self.log(f"❌ Ebook creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Setup error: {str(e)}", "ERROR")
            return False
    
    async def test_legal_pages_generation(self):
        """Test new legal pages generation endpoint"""
        self.log("Testing legal pages generation (NEW ENDPOINT)...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            legal_data = {
                "ebook_id": self.test_ebook_id,
                "year": 2025,
                "edition": "Première édition"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-legal-pages", json=legal_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                legal_pages = data.get("legal_pages", {})
                
                self.log("Legal pages response received. Analyzing structure...")
                
                # Check required fields
                required_fields = ["copyright_page", "legal_mentions", "title_page", "isbn", "publisher", "year", "edition"]
                missing_fields = []
                
                for field in required_fields:
                    if field not in legal_pages:
                        missing_fields.append(field)
                
                if missing_fields:
                    self.log(f"❌ Legal pages missing fields: {missing_fields}", "ERROR")
                    return False
                
                # Check content is in French
                text_fields = ["copyright_page", "legal_mentions", "title_page"]
                french_indicators = ["©", "droits", "réservés", "édition", "auteur", "mentions", "légales", "reproduction"]
                
                for field in text_fields:
                    content = legal_pages.get(field, "").lower()
                    if not any(indicator in content for indicator in french_indicators):
                        self.log(f"❌ Legal pages field '{field}' may not be in French", "ERROR")
                        self.log(f"Content: {content[:100]}...", "ERROR")
                        return False
                
                # Log sample content for verification
                self.log("Sample legal pages content:")
                self.log(f"Copyright page (first 100 chars): {legal_pages.get('copyright_page', '')[:100]}...")
                self.log(f"Year: {legal_pages.get('year')}")
                self.log(f"Edition: {legal_pages.get('edition')}")
                self.log(f"Publisher: {legal_pages.get('publisher')}")
                
                self.log("✅ Legal pages generation successful with all required fields")
                return True
                
            else:
                self.log(f"❌ Legal pages generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Legal pages generation error: {str(e)}", "ERROR")
            return False
    
    async def test_legal_pages_with_custom_params(self):
        """Test legal pages with custom parameters"""
        self.log("Testing legal pages with custom parameters...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            legal_data = {
                "ebook_id": self.test_ebook_id,
                "publisher": "Éditions Test",
                "isbn": "978-2-123456-78-9",
                "edition": "Deuxième édition",
                "year": 2024
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-legal-pages", json=legal_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                legal_pages = data.get("legal_pages", {})
                
                # Verify custom parameters are used
                if legal_pages.get("publisher") != "Éditions Test":
                    self.log(f"❌ Custom publisher not used: {legal_pages.get('publisher')}", "ERROR")
                    return False
                
                if legal_pages.get("isbn") != "978-2-123456-78-9":
                    self.log(f"❌ Custom ISBN not used: {legal_pages.get('isbn')}", "ERROR")
                    return False
                
                if legal_pages.get("year") != 2024:
                    self.log(f"❌ Custom year not used: {legal_pages.get('year')}", "ERROR")
                    return False
                
                self.log("✅ Legal pages with custom parameters successful")
                return True
                
            else:
                self.log(f"❌ Legal pages with custom params failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Legal pages custom params error: {str(e)}", "ERROR")
            return False
    
    async def run_legal_tests(self):
        """Run legal pages specific tests"""
        self.log("=== YooCreat Legal Pages Testing Started ===")
        self.log(f"Backend URL: {BACKEND_URL}")
        
        test_results = {}
        
        # Test sequence
        tests = [
            ("Setup User and Ebook", self.setup_test_user_and_ebook),
            ("Legal Pages Generation", self.test_legal_pages_generation),
            ("Legal Pages Custom Parameters", self.test_legal_pages_with_custom_params),
        ]
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running: {test_name} ---")
            try:
                result = await test_func()
                test_results[test_name] = result
                if not result:
                    self.log(f"❌ {test_name} FAILED - Stopping test sequence", "ERROR")
                    break
            except Exception as e:
                self.log(f"❌ {test_name} ERROR: {str(e)}", "ERROR")
                test_results[test_name] = False
                break
        
        # Summary
        self.log("\n=== LEGAL PAGES TEST RESULTS ===")
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status}: {test_name}")
        
        self.log(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL LEGAL PAGES TESTS PASSED!")
            return True
        else:
            self.log("⚠️  SOME LEGAL PAGES TESTS FAILED")
            return False

async def main():
    """Main test execution"""
    tester = YooCreatLegalTester()
    
    try:
        success = await tester.run_legal_tests()
        return 0 if success else 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)