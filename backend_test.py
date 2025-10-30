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
BACKEND_URL = "https://smartwriter-2.preview.emergentagent.com/api"

class YooCreatAPITester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=180.0)  # 3 minutes for AI generation
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
                "author": "Dr. Sophie Martin",
                "title": "Guide Santé Mentale",
                "tone": "Bienveillant",
                "target_audience": ["Adultes", "Professionnels de santé"],
                "description": "Un guide complet pour comprendre et améliorer sa santé mentale au quotidien",
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
                "author": "Dr. Sophie Martin",
                "title": "Guide Santé Mentale",
                "tone": "Bienveillant",
                "target_audience": ["Adultes", "Professionnels de santé"],
                "description": "Un guide complet pour comprendre et améliorer sa santé mentale au quotidien",
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
            # Try to get more details about the error
            import traceback
            self.log(f"Full traceback: {traceback.format_exc()}", "ERROR")
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
    
    async def test_visual_theme_generation(self):
        """Test NEW visual theme generation endpoint"""
        self.log("Testing visual theme generation (NEW FEATURE)...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            theme_data = {
                "ebook_id": self.test_ebook_id
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-visual-theme", json=theme_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                visual_theme = data.get("visual_theme", {})
                
                issues = []
                
                # Check required structure
                required_sections = ["palette", "fonts", "quote_style", "chapter_separator", "overall_mood"]
                for section in required_sections:
                    if section not in visual_theme:
                        issues.append(f"Missing '{section}' section in visual theme")
                
                # Validate palette
                if "palette" in visual_theme:
                    palette = visual_theme["palette"]
                    required_colors = ["primary", "secondary", "background"]
                    for color in required_colors:
                        if color not in palette:
                            issues.append(f"Missing '{color}' color in palette")
                        elif not isinstance(palette[color], str) or not palette[color].startswith("#"):
                            issues.append(f"Invalid HEX color format for '{color}': {palette.get(color)}")
                
                # Validate fonts
                if "fonts" in visual_theme:
                    fonts = visual_theme["fonts"]
                    allowed_fonts = ["Helvetica", "Georgia", "Arial", "Times New Roman", "Palatino", "Times"]
                    if "body" in fonts:
                        body_font = fonts["body"]
                        if not any(allowed in body_font for allowed in allowed_fonts):
                            issues.append(f"Body font '{body_font}' not in allowed list")
                    if "titles" in fonts:
                        title_font = fonts["titles"]
                        if not any(allowed in title_font for allowed in allowed_fonts):
                            issues.append(f"Title font '{title_font}' not in allowed list")
                
                # Check French language
                mood = visual_theme.get("overall_mood", "")
                if mood and not any(french_word in mood.lower() for french_word in ["le", "la", "les", "de", "du", "des", "et", "avec", "pour", "dans"]):
                    issues.append("Overall mood may not be in French")
                
                if issues:
                    self.log("❌ Visual theme generation issues found:", "ERROR")
                    for issue in issues:
                        self.log(f"  - {issue}", "ERROR")
                    return False
                else:
                    self.log("✅ Visual theme generation successful with valid structure")
                    # Log sample theme for verification
                    if "palette" in visual_theme:
                        colors = visual_theme["palette"]
                        self.log(f"  Sample colors: Primary={colors.get('primary')}, Secondary={colors.get('secondary')}")
                    if "fonts" in visual_theme:
                        fonts = visual_theme["fonts"]
                        self.log(f"  Sample fonts: Body={fonts.get('body')}, Titles={fonts.get('titles')}")
                    return True
                    
            else:
                self.log(f"❌ Visual theme generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Visual theme generation error: {str(e)}", "ERROR")
            return False
    
    async def test_illustrations_generation(self):
        """Test NEW illustrations generation endpoint"""
        self.log("Testing illustrations generation (NEW FEATURE)...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            illustrations_data = {
                "ebook_id": self.test_ebook_id
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-illustrations", json=illustrations_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                illustrations = data.get("illustrations", [])
                
                issues = []
                
                if not illustrations:
                    issues.append("No illustrations generated")
                else:
                    for chapter_illust in illustrations:
                        chapter_num = chapter_illust.get("chapter_number", "?")
                        queries = chapter_illust.get("queries", [])
                        
                        if not queries:
                            issues.append(f"Chapter {chapter_num} has no illustration queries")
                            continue
                        
                        for i, query in enumerate(queries):
                            # Check required fields
                            required_fields = ["search_query", "alt_text", "placement", "image_url", "image_credit"]
                            for field in required_fields:
                                if field not in query:
                                    issues.append(f"Chapter {chapter_num}, query {i+1} missing '{field}' field")
                            
                            # Validate search_query (should be English)
                            search_query = query.get("search_query", "")
                            if search_query:
                                # Check if it's likely English (no French accents)
                                french_chars = ["é", "è", "à", "ç", "ù", "ê", "â", "î", "ô", "û"]
                                if any(char in search_query.lower() for char in french_chars):
                                    issues.append(f"Chapter {chapter_num}, query {i+1} search_query may not be in English: '{search_query}'")
                            
                            # Validate alt_text (should be French)
                            alt_text = query.get("alt_text", "")
                            if alt_text:
                                french_indicators = ["une", "un", "le", "la", "les", "de", "du", "des", "avec", "dans", "pour"]
                                if not any(indicator in alt_text.lower() for indicator in french_indicators):
                                    issues.append(f"Chapter {chapter_num}, query {i+1} alt_text may not be in French: '{alt_text}'")
                            
                            # Validate image_url
                            image_url = query.get("image_url", "")
                            if image_url and not image_url.startswith("https://"):
                                issues.append(f"Chapter {chapter_num}, query {i+1} invalid image_url format: '{image_url}'")
                
                if issues:
                    self.log("❌ Illustrations generation issues found:", "ERROR")
                    for issue in issues:
                        self.log(f"  - {issue}", "ERROR")
                    return False
                else:
                    self.log(f"✅ Illustrations generation successful - {len(illustrations)} chapters with illustrations")
                    # Log sample for verification
                    if illustrations:
                        sample = illustrations[0]
                        queries = sample.get("queries", [])
                        if queries:
                            sample_query = queries[0]
                            self.log(f"  Sample: Query='{sample_query.get('search_query')}', Alt='{sample_query.get('alt_text')[:50]}...'")
                    return True
                    
            else:
                self.log(f"❌ Illustrations generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Illustrations generation error: {str(e)}", "ERROR")
            return False
    
    async def test_ebook_data_storage(self):
        """Test that visual theme and illustrations are stored in ebook data"""
        self.log("Testing ebook data storage for new features...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            response = await self.client.get(f"{BACKEND_URL}/ebooks/{self.test_ebook_id}", headers=headers)
            
            if response.status_code == 200:
                ebook_data = response.json()
                
                issues = []
                
                # Check if visual_theme is stored
                if "visual_theme" not in ebook_data:
                    issues.append("visual_theme field not found in ebook data")
                elif not ebook_data["visual_theme"]:
                    issues.append("visual_theme field is empty")
                
                # Check if illustrations are stored
                if "illustrations" not in ebook_data:
                    issues.append("illustrations field not found in ebook data")
                elif not ebook_data["illustrations"]:
                    issues.append("illustrations field is empty")
                
                if issues:
                    self.log("❌ Ebook data storage issues found:", "ERROR")
                    for issue in issues:
                        self.log(f"  - {issue}", "ERROR")
                    return False
                else:
                    self.log("✅ Ebook data storage successful - visual_theme and illustrations fields present")
                    return True
                    
            else:
                self.log(f"❌ Ebook data retrieval failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Ebook data storage test error: {str(e)}", "ERROR")
            return False
    
    async def test_legal_mentions_update_fix(self):
        """Test URGENT FIX: Legal mentions save button with JSON body parsing"""
        self.log("Testing URGENT FIX: Legal mentions update with JSON body...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # First, generate legal pages to have something to update
            legal_gen_data = {
                "ebook_id": self.test_ebook_id,
                "year": 2025,
                "edition": "Première édition"
            }
            
            gen_response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-legal-pages", json=legal_gen_data, headers=headers)
            
            if gen_response.status_code != 200:
                self.log(f"❌ Failed to generate legal pages first: {gen_response.status_code} - {gen_response.text}", "ERROR")
                return False
            
            # Now test the update functionality with JSON body (the fix)
            update_data = {
                "ebook_id": self.test_ebook_id,
                "copyright_page": "© 2025 Test Author\nDroits réservés.",
                "legal_mentions": "Protection de la propriété intellectuelle : Ce livre est protégé."
            }
            
            self.log("Testing POST /api/ebooks/update-legal-pages with JSON body...")
            update_response = await self.client.post(f"{BACKEND_URL}/ebooks/update-legal-pages", json=update_data, headers=headers)
            
            if update_response.status_code == 200:
                response_data = update_response.json()
                
                # Check for expected response format
                if response_data.get("success") != True:
                    self.log(f"❌ Update response missing success=true: {response_data}", "ERROR")
                    return False
                
                if "message" not in response_data:
                    self.log(f"❌ Update response missing message field: {response_data}", "ERROR")
                    return False
                
                expected_message = "Legal pages updated successfully"
                if expected_message not in response_data.get("message", ""):
                    self.log(f"❌ Unexpected message: {response_data.get('message')}", "ERROR")
                    return False
                
                self.log("✅ Legal pages update API returned correct success response")
                
                # Verify data persistence - get the ebook and check if changes were saved
                get_response = await self.client.get(f"{BACKEND_URL}/ebooks/{self.test_ebook_id}", headers=headers)
                
                if get_response.status_code == 200:
                    ebook_data = get_response.json()
                    legal_pages = ebook_data.get("legal_pages", {})
                    
                    # Check if our updates were saved
                    saved_copyright = legal_pages.get("copyright_page", "")
                    saved_legal_mentions = legal_pages.get("legal_mentions", "")
                    
                    if update_data["copyright_page"] not in saved_copyright:
                        self.log(f"❌ Copyright page not properly saved. Expected: '{update_data['copyright_page']}', Got: '{saved_copyright}'", "ERROR")
                        return False
                    
                    if update_data["legal_mentions"] not in saved_legal_mentions:
                        self.log(f"❌ Legal mentions not properly saved. Expected: '{update_data['legal_mentions']}', Got: '{saved_legal_mentions}'", "ERROR")
                        return False
                    
                    self.log("✅ Legal pages data properly persisted in MongoDB")
                    self.log("✅ URGENT FIX VERIFIED: No [object Object] errors, JSON body properly parsed")
                    return True
                else:
                    self.log(f"❌ Failed to retrieve ebook for verification: {get_response.status_code}", "ERROR")
                    return False
                    
            else:
                self.log(f"❌ Legal pages update failed: {update_response.status_code} - {update_response.text}", "ERROR")
                
                # Check if this is the old [object Object] error
                response_text = update_response.text
                if "[object Object]" in response_text:
                    self.log("❌ CRITICAL: [object Object] error still present - fix not working!", "ERROR")
                
                return False
                
        except Exception as e:
            self.log(f"❌ Legal mentions update test error: {str(e)}", "ERROR")
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
            ("URGENT: Legal Mentions Update Fix", self.test_legal_mentions_update_fix),
            ("Visual Theme Generation", self.test_visual_theme_generation),
            ("Illustrations Generation", self.test_illustrations_generation),
            ("Ebook Data Storage", self.test_ebook_data_storage),
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