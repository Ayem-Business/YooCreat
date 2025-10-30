#!/usr/bin/env python3
"""
Detailed verification of YooCreat visual themes and illustrations features
"""

import httpx
import json
import asyncio
from datetime import datetime

BACKEND_URL = "https://smartwriter-2.preview.emergentagent.com/api"

async def detailed_verification():
    """Perform detailed verification of the new features"""
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        print("=== DETAILED VERIFICATION OF VISUAL THEMES & ILLUSTRATIONS ===\n")
        
        # Register a test user
        timestamp = str(int(datetime.now().timestamp()))
        test_email = f"verify_{timestamp}@example.com"
        test_username = f"verify_{timestamp}"
        
        register_data = {
            "username": test_username,
            "email": test_email,
            "password": "VerifyPass123!"
        }
        
        response = await client.post(f"{BACKEND_URL}/auth/register", json=register_data)
        if response.status_code != 200:
            print(f"❌ Registration failed: {response.text}")
            return
        
        auth_token = response.json()["token"]
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create test ebook
        ebook_data = {
            "author": "Dr. Sophie Martin",
            "title": "Guide Santé Mentale",
            "tone": "Bienveillant",
            "target_audience": ["Adultes", "Professionnels de santé"],
            "description": "Un guide complet pour comprendre et améliorer sa santé mentale au quotidien",
            "chapters_count": 3,
            "length": "Moyen"
        }
        
        response = await client.post(f"{BACKEND_URL}/ebooks/create", json=ebook_data, headers=headers)
        ebook_id = response.json()["ebook_id"]
        
        # Generate TOC
        response = await client.post(f"{BACKEND_URL}/ebooks/generate-toc", json=ebook_data, headers=headers)
        toc = response.json()["toc"]
        
        # Generate content
        content_data = {"ebook_id": ebook_id, "toc": toc}
        response = await client.post(f"{BACKEND_URL}/ebooks/generate-content", json=content_data, headers=headers)
        
        print("1. TESTING VISUAL THEME GENERATION")
        print("=" * 50)
        
        # Generate visual theme
        theme_data = {"ebook_id": ebook_id}
        response = await client.post(f"{BACKEND_URL}/ebooks/generate-visual-theme", json=theme_data, headers=headers)
        
        if response.status_code == 200:
            visual_theme = response.json()["visual_theme"]
            
            print("✅ Visual Theme Generated Successfully")
            print(f"📋 Response Status: {response.status_code}")
            print("\n🎨 PALETTE:")
            palette = visual_theme.get("palette", {})
            print(f"  • Primary: {palette.get('primary')} (for titles, main elements)")
            print(f"  • Secondary: {palette.get('secondary')} (for quotes, accents)")
            print(f"  • Background: {palette.get('background')} (for special sections)")
            print(f"  • Justification: {palette.get('justification', 'N/A')}")
            
            print("\n🔤 FONTS:")
            fonts = visual_theme.get("fonts", {})
            print(f"  • Body: {fonts.get('body')}")
            print(f"  • Titles: {fonts.get('titles')}")
            print(f"  • Justification: {fonts.get('justification', 'N/A')}")
            
            print("\n💬 QUOTE STYLE:")
            quote_style = visual_theme.get("quote_style", {})
            print(f"  • Type: {quote_style.get('type')}")
            print(f"  • Description: {quote_style.get('description', 'N/A')}")
            print(f"  • Icon: {quote_style.get('icon', 'N/A')}")
            
            print("\n📖 CHAPTER SEPARATOR:")
            separator = visual_theme.get("chapter_separator", {})
            print(f"  • Type: {separator.get('type')}")
            print(f"  • Description: {separator.get('description', 'N/A')}")
            print(f"  • Symbol: {separator.get('symbol', 'N/A')}")
            
            print(f"\n🌟 OVERALL MOOD: {visual_theme.get('overall_mood', 'N/A')}")
            
            # Validate HEX colors
            print("\n🔍 VALIDATION:")
            valid_colors = True
            for color_name, color_value in palette.items():
                if color_name in ['primary', 'secondary', 'background']:
                    if not color_value.startswith('#') or len(color_value) != 7:
                        print(f"  ❌ Invalid HEX color {color_name}: {color_value}")
                        valid_colors = False
                    else:
                        print(f"  ✅ Valid HEX color {color_name}: {color_value}")
            
            # Validate fonts
            allowed_fonts = ["Helvetica", "Georgia", "Arial", "Times", "Palatino"]
            body_font = fonts.get('body', '')
            title_font = fonts.get('titles', '')
            
            if any(font in body_font for font in allowed_fonts):
                print(f"  ✅ Valid body font: {body_font}")
            else:
                print(f"  ❌ Invalid body font: {body_font}")
            
            if any(font in title_font for font in allowed_fonts):
                print(f"  ✅ Valid title font: {title_font}")
            else:
                print(f"  ❌ Invalid title font: {title_font}")
                
        else:
            print(f"❌ Visual Theme Generation Failed: {response.status_code}")
            print(f"Error: {response.text}")
        
        print("\n\n2. TESTING ILLUSTRATIONS GENERATION")
        print("=" * 50)
        
        # Generate illustrations
        illustrations_data = {"ebook_id": ebook_id}
        response = await client.post(f"{BACKEND_URL}/ebooks/generate-illustrations", json=illustrations_data, headers=headers)
        
        if response.status_code == 200:
            illustrations = response.json()["illustrations"]
            
            print("✅ Illustrations Generated Successfully")
            print(f"📋 Response Status: {response.status_code}")
            print(f"📊 Total Chapters with Illustrations: {len(illustrations)}")
            
            for i, chapter_illust in enumerate(illustrations):
                chapter_num = chapter_illust.get("chapter_number", "?")
                queries = chapter_illust.get("queries", [])
                
                print(f"\n📖 CHAPTER {chapter_num}:")
                print(f"  • Number of illustrations: {len(queries)}")
                
                for j, query in enumerate(queries, 1):
                    print(f"\n  🖼️  ILLUSTRATION {j}:")
                    print(f"    • Search Query (EN): '{query.get('search_query', 'N/A')}'")
                    print(f"    • Alt Text (FR): '{query.get('alt_text', 'N/A')}'")
                    print(f"    • Placement: '{query.get('placement', 'N/A')}'")
                    print(f"    • Image URL: {query.get('image_url', 'N/A')}")
                    print(f"    • Credit: {query.get('image_credit', 'N/A')}")
                    
                    # Validate URL format
                    image_url = query.get('image_url', '')
                    if image_url and image_url.startswith('https://'):
                        print(f"    ✅ Valid URL format")
                    else:
                        print(f"    ❌ Invalid URL format: {image_url}")
                    
                    # Check language consistency
                    search_query = query.get('search_query', '')
                    alt_text = query.get('alt_text', '')
                    
                    # English indicators for search query
                    french_chars = ['é', 'è', 'à', 'ç', 'ù', 'ê', 'â', 'î', 'ô', 'û']
                    has_french_chars = any(char in search_query.lower() for char in french_chars)
                    
                    if not has_french_chars:
                        print(f"    ✅ Search query appears to be in English")
                    else:
                        print(f"    ⚠️  Search query may contain French characters")
                    
                    # French indicators for alt text
                    french_words = ['une', 'un', 'le', 'la', 'les', 'de', 'du', 'des', 'avec', 'dans', 'pour']
                    has_french_words = any(word in alt_text.lower() for word in french_words)
                    
                    if has_french_words:
                        print(f"    ✅ Alt text appears to be in French")
                    else:
                        print(f"    ⚠️  Alt text may not be in French")
                        
        else:
            print(f"❌ Illustrations Generation Failed: {response.status_code}")
            print(f"Error: {response.text}")
        
        print("\n\n3. TESTING DATA STORAGE")
        print("=" * 50)
        
        # Verify data is stored in ebook
        response = await client.get(f"{BACKEND_URL}/ebooks/{ebook_id}", headers=headers)
        
        if response.status_code == 200:
            ebook = response.json()
            
            print("✅ Ebook Data Retrieved Successfully")
            
            # Check visual_theme field
            if "visual_theme" in ebook and ebook["visual_theme"]:
                print("✅ visual_theme field present and populated")
                theme = ebook["visual_theme"]
                print(f"  • Contains {len(theme)} theme sections")
            else:
                print("❌ visual_theme field missing or empty")
            
            # Check illustrations field
            if "illustrations" in ebook and ebook["illustrations"]:
                print("✅ illustrations field present and populated")
                illustrations = ebook["illustrations"]
                total_queries = sum(len(ch.get("queries", [])) for ch in illustrations)
                print(f"  • Contains {len(illustrations)} chapters with {total_queries} total illustration queries")
            else:
                print("❌ illustrations field missing or empty")
                
        else:
            print(f"❌ Ebook Data Retrieval Failed: {response.status_code}")
        
        print("\n\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(detailed_verification())