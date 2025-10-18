#!/usr/bin/env python3
"""
YooCreat Backend API Testing Script - TOC Only
Tests the enhanced TOC generation with subtitles
"""

import httpx
import json
import asyncio
import sys
from datetime import datetime
import re

# Backend URL from frontend/.env
BACKEND_URL = "https://smart-ebook-gen-1.preview.emergentagent.com/api"

class YooCreatTOCTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.auth_token = None
        self.user_id = None
        
    async def cleanup(self):
        await self.client.aclose()
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def setup_test_user(self):
        """Setup test user"""
        self.log("Setting up test user...")
        
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
            self.log(f"❌ Setup error: {str(e)}", "ERROR")
            return False
    
    async def test_toc_generation_detailed(self):
        """Test TOC generation with detailed analysis"""
        self.log("Testing enhanced TOC generation with detailed analysis...")
        
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
                
                self.log(f"TOC generated with {len(toc)} chapters. Analyzing structure...")
                
                # Detailed analysis
                issues = []
                
                for i, chapter in enumerate(toc):
                    chapter_num = chapter.get("number", "?")
                    chapter_title = chapter.get("title", "")
                    chapter_desc = chapter.get("description", "")
                    chapter_type = chapter.get("type", "")
                    subtitles = chapter.get("subtitles", [])
                    
                    self.log(f"Chapter {chapter_num}: {chapter_title}")
                    self.log(f"  Type: {chapter_type}")
                    self.log(f"  Description: {chapter_desc[:50]}...")
                    self.log(f"  Subtitles ({len(subtitles)}): {subtitles}")
                    
                    # Check for subtitles field
                    if "subtitles" not in chapter:
                        issues.append(f"Chapter {chapter_num} missing 'subtitles' field")
                    elif not isinstance(subtitles, list):
                        issues.append(f"Chapter {chapter_num} 'subtitles' is not a list")
                    elif len(subtitles) < 2 or len(subtitles) > 4:
                        issues.append(f"Chapter {chapter_num} has {len(subtitles)} subtitles (expected 2-4)")
                    
                    # Check for markdown symbols in titles/descriptions/subtitles
                    all_text = f"{chapter_title} {chapter_desc} {' '.join(subtitles)}"
                    if re.search(r'[#]{1,6}\s', all_text):
                        issues.append(f"Chapter {chapter_num} contains markdown symbols")
                    
                    # Check French content
                    french_indicators = ["le", "la", "les", "de", "du", "des", "et", "pour", "dans", "avec", "sur"]
                    if not any(indicator in all_text.lower() for indicator in french_indicators):
                        issues.append(f"Chapter {chapter_num} may not be in French")
                
                if issues:
                    self.log("❌ TOC generation issues found:", "ERROR")
                    for issue in issues:
                        self.log(f"  - {issue}", "ERROR")
                    return False
                else:
                    self.log(f"✅ TOC generation successful - All {len(toc)} chapters have proper structure")
                    return True
                    
            else:
                self.log(f"❌ TOC generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ TOC generation error: {str(e)}", "ERROR")
            return False
    
    async def test_toc_different_parameters(self):
        """Test TOC generation with different parameters"""
        self.log("Testing TOC generation with different parameters...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test with different tone and audience
            toc_data = {
                "author": "Jean Martin",
                "title": "L'Art de la Communication Digitale",
                "tone": "Décontracté",
                "target_audience": ["Jeunes adultes", "Étudiants"],
                "description": "Maîtriser les outils de communication moderne pour réussir dans le monde digital",
                "chapters_count": 5,
                "length": "Long"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-toc", json=toc_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                toc = data.get("toc", [])
                
                # Should have 5 chapters + intro + conclusion = 7 total
                expected_total = 5 + 2  # chapters + intro + conclusion
                if len(toc) != expected_total:
                    self.log(f"❌ Expected {expected_total} chapters, got {len(toc)}", "ERROR")
                    return False
                
                # Check all have subtitles
                for chapter in toc:
                    if "subtitles" not in chapter or not chapter["subtitles"]:
                        self.log(f"❌ Chapter {chapter.get('number')} missing subtitles", "ERROR")
                        return False
                
                self.log(f"✅ TOC with different parameters successful - {len(toc)} chapters")
                return True
                
            else:
                self.log(f"❌ TOC with different params failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ TOC different params error: {str(e)}", "ERROR")
            return False
    
    async def run_toc_tests(self):
        """Run TOC specific tests"""
        self.log("=== YooCreat TOC Enhancement Testing Started ===")
        self.log(f"Backend URL: {BACKEND_URL}")
        
        test_results = {}
        
        # Test sequence
        tests = [
            ("Setup User", self.setup_test_user),
            ("TOC Generation Detailed", self.test_toc_generation_detailed),
            ("TOC Different Parameters", self.test_toc_different_parameters),
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
        self.log("\n=== TOC ENHANCEMENT TEST RESULTS ===")
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status}: {test_name}")
        
        self.log(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL TOC ENHANCEMENT TESTS PASSED!")
            return True
        else:
            self.log("⚠️  SOME TOC ENHANCEMENT TESTS FAILED")
            return False

async def main():
    """Main test execution"""
    tester = YooCreatTOCTester()
    
    try:
        success = await tester.run_toc_tests()
        return 0 if success else 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)