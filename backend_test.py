#!/usr/bin/env python3
"""
YooCreat Backend API Testing Script
Tests the improved AI-generated ebook content formatting
"""

import httpx
import json
import asyncio
import sys
from datetime import datetime
import re

# Backend URL from frontend/.env
BACKEND_URL = "https://smart-ebook-gen-1.preview.emergentagent.com/api"

class YooCreatAPITester:
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
    
    async def test_user_registration_login(self):
        """Test user registration and login"""
        self.log("Testing user registration and login...")
        
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
                return True
            else:
                self.log(f"❌ Registration failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Registration error: {str(e)}", "ERROR")
            return False
    
    async def test_create_ebook(self):
        """Create a test ebook"""
        self.log("Creating test ebook...")
        
        try:
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
            self.log(f"❌ Ebook creation error: {str(e)}", "ERROR")
            return False
    
    async def test_enhanced_toc_generation(self):
        """Test enhanced TOC generation with subtitles"""
        self.log("Testing enhanced TOC generation...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            toc_data = {
                "author": "Marie Dubois",
                "title": "Guide Pratique de la Productivité Moderne",
                "tone": "Professionnel",
                "target_audience": ["Adultes", "Professionnels"],
                "description": "Un guide complet pour améliorer sa productivité au travail et dans la vie personnelle",
                "chapters_count": 3,
                "length": "Moyen"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-toc", json=toc_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                toc = data.get("toc", [])
                
                # Verify TOC structure
                issues = []
                
                for chapter in toc:
                    # Check for subtitles field
                    if "subtitles" not in chapter:
                        issues.append(f"Chapter {chapter.get('number', '?')} missing 'subtitles' field")
                    elif not isinstance(chapter["subtitles"], list):
                        issues.append(f"Chapter {chapter.get('number', '?')} 'subtitles' is not a list")
                    elif len(chapter["subtitles"]) < 2 or len(chapter["subtitles"]) > 4:
                        issues.append(f"Chapter {chapter.get('number', '?')} has {len(chapter['subtitles'])} subtitles (expected 2-4)")
                    
                    # Check for markdown symbols in titles/descriptions
                    title = chapter.get("title", "")
                    description = chapter.get("description", "")
                    
                    if re.search(r'[#]{1,6}\s', title + " " + description):
                        issues.append(f"Chapter {chapter.get('number', '?')} contains markdown symbols in title/description")
                
                if issues:
                    self.log("❌ TOC generation issues found:", "ERROR")
                    for issue in issues:
                        self.log(f"  - {issue}", "ERROR")
                    return False
                else:
                    self.log(f"✅ TOC generation successful - {len(toc)} chapters with proper subtitles")
                    # Store TOC for content generation
                    self.test_toc = toc
                    return True
                    
            else:
                self.log(f"❌ TOC generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ TOC generation error: {str(e)}", "ERROR")
            return False
    
    async def test_content_generation_format(self):
        """Test content generation with new format requirements"""
        self.log("Testing content generation with new format...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            content_data = {
                "ebook_id": self.test_ebook_id,
                "toc": self.test_toc
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-content", json=content_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                chapters = data.get("chapters", [])
                
                issues = []
                
                for chapter in chapters:
                    content = chapter.get("content", "")
                    chapter_num = chapter.get("number", "?")
                    chapter_type = chapter.get("type", "chapter")
                    
                    # Check for markdown symbols in content
                    if re.search(r'[#]{1,6}\s', content):
                        issues.append(f"Chapter {chapter_num} contains markdown symbols (# ## ###) in content")
                    
                    # Check for 🔹 markers (should be present)
                    if "🔹" not in content and chapter_type == "chapter":
                        issues.append(f"Chapter {chapter_num} missing 🔹 section markers")
                    
                    # Check for mandatory sections in regular chapters
                    if chapter_type == "chapter":
                        if "🔹 En synthèse" not in content and "En synthèse" not in content:
                            issues.append(f"Chapter {chapter_num} missing mandatory 'En synthèse' section")
                        
                        if "🔹 Question de réflexion" not in content and "Réflexion personnelle" not in content:
                            issues.append(f"Chapter {chapter_num} missing mandatory 'Question de réflexion' section")
                
                if issues:
                    self.log("❌ Content generation format issues found:", "ERROR")
                    for issue in issues:
                        self.log(f"  - {issue}", "ERROR")
                    return False
                else:
                    self.log(f"✅ Content generation successful - {len(chapters)} chapters with proper format")
                    return True
                    
            else:
                self.log(f"❌ Content generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Content generation error: {str(e)}", "ERROR")
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
                french_indicators = ["©", "droits", "réservés", "édition", "auteur", "mentions", "légales"]
                
                for field in text_fields:
                    content = legal_pages.get(field, "").lower()
                    if not any(indicator in content for indicator in french_indicators):
                        self.log(f"❌ Legal pages field '{field}' may not be in French", "ERROR")
                        return False
                
                self.log("✅ Legal pages generation successful with all required fields")
                return True
                
            else:
                self.log(f"❌ Legal pages generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Legal pages generation error: {str(e)}", "ERROR")
            return False
    
    async def test_health_check(self):
        """Test API health check"""
        self.log("Testing API health check...")
        
        try:
            response = await self.client.get(f"{BACKEND_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.log("✅ API health check passed")
                    return True
                else:
                    self.log(f"❌ API health check failed: {data}", "ERROR")
                    return False
            else:
                self.log(f"❌ API health check failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ API health check error: {str(e)}", "ERROR")
            return False
    
    async def run_all_tests(self):
        """Run all backend tests"""
        self.log("=== YooCreat Backend API Testing Started ===")
        self.log(f"Backend URL: {BACKEND_URL}")
        
        test_results = {}
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("User Registration/Login", self.test_user_registration_login),
            ("Create Test Ebook", self.test_create_ebook),
            ("Enhanced TOC Generation", self.test_enhanced_toc_generation),
            ("Content Generation Format", self.test_content_generation_format),
            ("Legal Pages Generation", self.test_legal_pages_generation),
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
        self.log("\n=== TEST RESULTS SUMMARY ===")
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status}: {test_name}")
        
        self.log(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL TESTS PASSED - YooCreat API improvements working correctly!")
            return True
        else:
            self.log("⚠️  SOME TESTS FAILED - Issues need to be addressed")
            return False

async def main():
    """Main test execution"""
    tester = YooCreatAPITester()
    
    try:
        success = await tester.run_all_tests()
        return 0 if success else 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)