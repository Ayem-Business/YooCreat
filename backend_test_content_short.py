#!/usr/bin/env python3
"""
YooCreat Backend API Testing Script - Short Content Test
Tests content generation with a minimal TOC to check format
"""

import httpx
import json
import asyncio
import sys
from datetime import datetime
import re

# Backend URL from frontend/.env
BACKEND_URL = "https://smartwriter-2.preview.emergentagent.com/api"

class YooCreatContentTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minutes
        self.auth_token = None
        self.user_id = None
        self.test_ebook_id = None
        
    async def cleanup(self):
        await self.client.aclose()
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def setup_test_user_and_ebook(self):
        """Setup test user and ebook"""
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
                "title": "Guide Test Productivité",
                "tone": "Professionnel",
                "target_audience": ["Adultes"],
                "description": "Un guide test pour la productivité",
                "chapters_count": 1,  # Only 1 chapter for faster testing
                "length": "Court"
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
    
    async def generate_minimal_toc(self):
        """Generate a minimal TOC for testing"""
        self.log("Generating minimal TOC...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            toc_data = {
                "author": "Marie Dubois",
                "title": "Guide Test Productivité",
                "tone": "Professionnel",
                "target_audience": ["Adultes"],
                "description": "Un guide test pour la productivité",
                "chapters_count": 1,
                "length": "Court"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-toc", json=toc_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.test_toc = data.get("toc", [])
                self.log(f"✅ TOC generated with {len(self.test_toc)} chapters")
                return True
            else:
                self.log(f"❌ TOC generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ TOC generation error: {str(e)}", "ERROR")
            return False
    
    async def test_content_generation_format(self):
        """Test content generation with format analysis"""
        self.log("Testing content generation format (this may take a few minutes)...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            content_data = {
                "ebook_id": self.test_ebook_id,
                "toc": self.test_toc
            }
            
            self.log("Sending content generation request...")
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-content", json=content_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                chapters = data.get("chapters", [])
                
                self.log(f"Content generated for {len(chapters)} chapters. Analyzing format...")
                
                issues = []
                
                for chapter in chapters:
                    content = chapter.get("content", "")
                    chapter_num = chapter.get("number", "?")
                    chapter_type = chapter.get("type", "chapter")
                    chapter_title = chapter.get("title", "")
                    
                    self.log(f"Analyzing Chapter {chapter_num}: {chapter_title} (type: {chapter_type})")
                    self.log(f"Content length: {len(content)} characters")
                    
                    # Check for markdown symbols in content
                    markdown_matches = re.findall(r'[#]{1,6}\s', content)
                    if markdown_matches:
                        issues.append(f"Chapter {chapter_num} contains {len(markdown_matches)} markdown symbols (# ## ###)")
                        self.log(f"  ❌ Found markdown symbols: {markdown_matches[:3]}...", "ERROR")
                    else:
                        self.log(f"  ✅ No markdown symbols found")
                    
                    # Check for 🔹 markers (should be present in chapters)
                    diamond_count = content.count("🔹")
                    if chapter_type == "chapter" and diamond_count == 0:
                        issues.append(f"Chapter {chapter_num} missing 🔹 section markers")
                        self.log(f"  ❌ No 🔹 markers found", "ERROR")
                    else:
                        self.log(f"  ✅ Found {diamond_count} 🔹 markers")
                    
                    # Check for mandatory sections in regular chapters
                    if chapter_type == "chapter":
                        has_synthese = "🔹 En synthèse" in content or "En synthèse" in content
                        has_reflexion = "🔹 Question de réflexion" in content or "Réflexion personnelle" in content or "🔹 Réflexion personnelle" in content
                        
                        if not has_synthese:
                            issues.append(f"Chapter {chapter_num} missing mandatory 'En synthèse' section")
                            self.log(f"  ❌ Missing 'En synthèse' section", "ERROR")
                        else:
                            self.log(f"  ✅ Found 'En synthèse' section")
                        
                        if not has_reflexion:
                            issues.append(f"Chapter {chapter_num} missing mandatory 'Question de réflexion' section")
                            self.log(f"  ❌ Missing 'Question de réflexion' section", "ERROR")
                        else:
                            self.log(f"  ✅ Found 'Question de réflexion' section")
                    
                    # Show sample content
                    self.log(f"  Sample content (first 200 chars): {content[:200]}...")
                
                if issues:
                    self.log("❌ Content generation format issues found:", "ERROR")
                    for issue in issues:
                        self.log(f"  - {issue}", "ERROR")
                    return False
                else:
                    self.log(f"✅ Content generation successful - All {len(chapters)} chapters have proper format")
                    return True
                    
            else:
                self.log(f"❌ Content generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Content generation error: {str(e)}", "ERROR")
            import traceback
            self.log(f"Full traceback: {traceback.format_exc()}", "ERROR")
            return False
    
    async def run_content_tests(self):
        """Run content generation tests"""
        self.log("=== YooCreat Content Format Testing Started ===")
        self.log(f"Backend URL: {BACKEND_URL}")
        
        test_results = {}
        
        # Test sequence
        tests = [
            ("Setup User and Ebook", self.setup_test_user_and_ebook),
            ("Generate Minimal TOC", self.generate_minimal_toc),
            ("Content Generation Format", self.test_content_generation_format),
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
        self.log("\n=== CONTENT FORMAT TEST RESULTS ===")
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status}: {test_name}")
        
        self.log(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL CONTENT FORMAT TESTS PASSED!")
            return True
        else:
            self.log("⚠️  SOME CONTENT FORMAT TESTS FAILED")
            return False

async def main():
    """Main test execution"""
    tester = YooCreatContentTester()
    
    try:
        success = await tester.run_content_tests()
        return 0 if success else 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)