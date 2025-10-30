#!/usr/bin/env python3
"""
Quick Backend Test - Essential APIs
"""

import httpx
import json
import asyncio
import sys
from datetime import datetime

BACKEND_URL = "https://smartwriter-2.preview.emergentagent.com/api"

class QuickTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.auth_token = None
        self.test_ebook_id = None
        
    async def cleanup(self):
        await self.client.aclose()
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def test_auth_and_ebook_creation(self):
        """Test authentication and ebook creation"""
        self.log("Testing authentication and ebook creation...")
        
        timestamp = str(int(datetime.now().timestamp()))
        test_email = f"quicktest_{timestamp}@example.com"
        test_username = f"quicktest_{timestamp}"
        
        try:
            # Register
            register_data = {
                "username": test_username,
                "email": test_email,
                "password": "TestPassword123!"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/auth/register", json=register_data)
            if response.status_code != 200:
                self.log(f"❌ Registration failed: {response.status_code}", "ERROR")
                return False
            
            data = response.json()
            self.auth_token = data.get("token")
            self.log("✅ User registration successful")
            
            # Create ebook
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            ebook_data = {
                "author": "Marie Dubois",
                "title": "Guide de Productivité Personnel",
                "tone": "Professionnel",
                "target_audience": ["Adultes"],
                "description": "Un guide complet pour améliorer sa productivité au quotidien",
                "chapters_count": 3,
                "length": "Moyen"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/create", json=ebook_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Ebook creation failed: {response.status_code}", "ERROR")
                return False
            
            data = response.json()
            self.test_ebook_id = data.get("ebook_id")
            self.log("✅ Ebook creation successful")
            return True
            
        except Exception as e:
            self.log(f"❌ Auth/Ebook error: {str(e)}", "ERROR")
            return False
    
    async def test_legal_pages_workflow(self):
        """Test complete legal pages workflow"""
        self.log("Testing legal pages workflow...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Generate legal pages
            legal_data = {
                "ebook_id": self.test_ebook_id,
                "year": 2025,
                "edition": "Première édition"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-legal-pages", json=legal_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Legal pages generation failed: {response.status_code}", "ERROR")
                return False
            
            self.log("✅ Legal pages generation successful")
            
            # Update legal pages (the fix we're testing)
            update_data = {
                "ebook_id": self.test_ebook_id,
                "copyright_page": "© 2025 Marie Dubois\nTous droits réservés.",
                "legal_mentions": "Protection de la propriété intellectuelle : Ce livre est protégé par le droit d'auteur."
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/update-legal-pages", json=update_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Legal pages update failed: {response.status_code}", "ERROR")
                return False
            
            data = response.json()
            if not data.get("success"):
                self.log(f"❌ Legal pages update response invalid: {data}", "ERROR")
                return False
            
            self.log("✅ Legal pages update successful")
            return True
            
        except Exception as e:
            self.log(f"❌ Legal pages workflow error: {str(e)}", "ERROR")
            return False
    
    async def test_toc_and_content(self):
        """Test TOC and content generation"""
        self.log("Testing TOC and content generation...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Generate TOC
            toc_data = {
                "author": "Marie Dubois",
                "title": "Guide de Productivité Personnel",
                "tone": "Professionnel",
                "target_audience": ["Adultes"],
                "description": "Un guide complet pour améliorer sa productivité au quotidien",
                "chapters_count": 3,
                "length": "Moyen"
            }
            
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-toc", json=toc_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ TOC generation failed: {response.status_code}", "ERROR")
                return False
            
            data = response.json()
            toc = data.get("toc", [])
            if not toc:
                self.log("❌ TOC is empty", "ERROR")
                return False
            
            self.log(f"✅ TOC generation successful - {len(toc)} chapters")
            
            # Generate content (this takes longer)
            content_data = {
                "ebook_id": self.test_ebook_id,
                "toc": toc
            }
            
            self.log("Generating content (this may take 1-2 minutes)...")
            response = await self.client.post(f"{BACKEND_URL}/ebooks/generate-content", json=content_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Content generation failed: {response.status_code}", "ERROR")
                return False
            
            data = response.json()
            chapters = data.get("chapters", [])
            if not chapters:
                self.log("❌ No chapters generated", "ERROR")
                return False
            
            self.log(f"✅ Content generation successful - {len(chapters)} chapters")
            return True
            
        except Exception as e:
            self.log(f"❌ TOC/Content error: {str(e)}", "ERROR")
            return False
    
    async def run_quick_tests(self):
        """Run essential backend tests"""
        self.log("=== QUICK BACKEND TESTS ===")
        
        tests = [
            ("Authentication & Ebook Creation", self.test_auth_and_ebook_creation),
            ("Legal Pages Workflow", self.test_legal_pages_workflow),
            ("TOC & Content Generation", self.test_toc_and_content),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            self.log(f"\n--- {test_name} ---")
            try:
                result = await test_func()
                results[test_name] = result
                if not result:
                    self.log(f"❌ {test_name} FAILED", "ERROR")
                    break
            except Exception as e:
                self.log(f"❌ {test_name} ERROR: {str(e)}", "ERROR")
                results[test_name] = False
                break
        
        # Summary
        self.log("\n=== RESULTS ===")
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status}: {test_name}")
        
        self.log(f"\nOverall: {passed}/{total} tests passed")
        return passed == total

async def main():
    tester = QuickTester()
    try:
        success = await tester.run_quick_tests()
        return 0 if success else 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)