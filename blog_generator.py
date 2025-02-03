import os
import google.generativeai as genai
from pathlib import Path
import asyncio
import aiofiles
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Model configuration
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 65536,
    "response_mime_type": "text/plain",
}

async def read_file(filepath):
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as file:
        return await file.read()

async def save_blog(title, content):
    # Create Generated Blogs directory if it doesn't exist
    output_dir = Path("Generated Blogs")
    output_dir.mkdir(exist_ok=True)
    
    # Create safe filename from title
    safe_title = re.sub(r'[^\w\s-]', '', title)
    safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-')
    
    filepath = output_dir / f"{safe_title}.html"
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as file:
        await file.write(content)
        print(f"Generated blog saved: {filepath}")

def preprocess_content(content):
    """Clean up and format the AI-generated content."""
    
    # Remove code block markers
    content = re.sub(r'```html\s*', '', content)
    content = re.sub(r'```\s*$', '', content)
    
    # Remove any markdown formatting
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
    
    # Fix HTML entities
    content = content.replace('&amp;', '&')
    content = content.replace('&lt;', '<')
    content = content.replace('&gt;', '>')
    
    # Remove extra newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Remove any remaining markdown or special characters
    content = re.sub(r'^\s*[-*]\s', '', content, flags=re.MULTILINE)
    
    # Fix any broken HTML tags
    content = re.sub(r'<br\s*/>', '<br>', content)
    content = re.sub(r'<hr\s*/>', '<hr>', content)
    
    # Ensure proper spacing around HTML tags
    content = re.sub(r'>\s+<', '>\n<', content)
    
    return content.strip()

async def generate_blog(title, prompt_template):
    try:
        # Create the model with exact GUI configuration
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-thinking-exp-01-21",
            generation_config=generation_config
        )
        
        # Start chat session with history
        chat_session = model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [prompt_template]
                }
            ]
        )
        
        # Generate content
        response = chat_session.send_message(f"Write a blog post about: {title}")
        
        content = response.text
        
        # Preprocess the content
        content = preprocess_content(content)
        
        # Add style template if missing
        if "<style>" not in content:
            style_template = '''
<style>
    body { font-family: Arial, sans-serif; line-height: 1.8; margin: 0; background-color: #ffffff; color: #000000; }
    h1 { font-size: 2.5rem; margin-top: 20px; border-bottom: 2px solid #000000; padding-bottom: 10px; }
    h2 { font-size: 2rem; margin-top: 30px; border-bottom: 1px solid #000000; padding-bottom: 5px; color: #000000; }
    p { margin: 15px 0; }
    ul { margin: 10px 0; padding-left: 20px; }
    ul li { margin-bottom: 10px; list-style-type: disc; }
    a { color: #000000; text-decoration: underline; }
    .callout { margin: 30px 0; padding: 20px; background-color: #f1f1f1; border: 1px solid #000000; text-align: center; }
</style>
'''
            content = style_template + content
        
        # Verify minimum backlinks after preprocessing
        if content.count('href="https://shrigbrothersglobal.com') < 20:
            print("Warning: Generated content has insufficient backlinks, regenerating...")
            return await generate_blog(title, prompt_template)
        
        return content
    
    except Exception as e:
        print(f"Error generating blog for '{title}': {str(e)}")
        return None

async def main():
    try:
        # Read titles and prompt template
        titles = (await read_file('titles.txt')).strip().split('\n')
        prompt_template = await read_file('prompt.txt')
        
        # Generate blogs for each title
        for title in titles:
            title = title.strip()
            if not title:
                continue
                
            print(f"Generating blog for: {title}")
            content = await generate_blog(title, prompt_template)
            
            if content:
                await save_blog(title, content)
                # Add delay to avoid rate limiting
                await asyncio.sleep(2)
            
    except Exception as e:
        print(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
