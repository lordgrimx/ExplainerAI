import os
import json
import shutil
import markdown
import fnmatch
from pathlib import Path
from flask import Flask, request, render_template, redirect, url_for, jsonify, session, send_from_directory
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.config['UPLOAD_FOLDER'] = 'app/uploads'
app.config['OUTPUT_FOLDER'] = 'app/output'
app.secret_key = 'explainer_secret_key'

# Make sure the upload and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Configure Google AI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_AI_MODEL = os.getenv('GOOGLE_AI_MODEL', 'gemini-2.0-flash-thinking-exp-01-21')  # Default to experimental model if not specified
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(GOOGLE_AI_MODEL)

# Get API settings from .env
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_folder():
    if 'folder' not in request.files:
        return redirect(request.url)
    
    # First, create a temporary list of files to be uploaded
    files = request.files.getlist('folder')
    files_to_upload = []
    
    # Filter out self-references to the explainer project itself
    for file in files:
        if file.filename:
            # Check if this is a recursion of the explainer project itself
            if 'explainer/app.py' in file.filename or 'explainer\\app.py' in file.filename:
                continue  # Skip files that appear to be from the explainer project itself
            files_to_upload.append(file)
    
    if not files_to_upload:
        return jsonify({'error': 'No valid files to upload or trying to upload the explainer project itself'}), 400
    
    # Completely clear the uploads and output directories
    completely_clear_directory(app.config['UPLOAD_FOLDER'])
    completely_clear_directory(app.config['OUTPUT_FOLDER'])
    
    # Look for .gitignore files in the uploaded files
    gitignore_patterns = []
    for file in files_to_upload:
        if file.filename.endswith('.gitignore') or file.filename.split('/')[-1] == '.gitignore' or file.filename.split('\\')[-1] == '.gitignore':
            content = file.read().decode('utf-8', errors='ignore')
            file.seek(0)  # Reset file position after reading
            gitignore_patterns.extend([p.strip() for p in content.splitlines() if p.strip() and not p.startswith('#')])
    
    uploaded_files = []
    
    # Now save the filtered files, excluding .gitignore patterns
    for file in files_to_upload:
        filename = file.filename.replace('\\', '/')  # Normalize path separators
        
        # Check if file matches any gitignore pattern
        if should_ignore_file(filename, gitignore_patterns):
            continue
            
        # Extract directory path and create it if it doesn't exist
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            file.save(file_path)
            uploaded_files.append(file_path)
        except PermissionError as e:
            print(f"Warning: Could not save {file_path}. File may be in use: {e}")
        except Exception as e:
            print(f"Error saving {file_path}: {e}")
    
    # Store the file structure in the session
    session['file_structure'] = get_folder_structure(app.config['UPLOAD_FOLDER'])
    
    return redirect(url_for('show_structure'))

def completely_clear_directory(directory_path):
    """Completely clear a directory by recreating it"""
    try:
        if os.path.exists(directory_path):
            shutil.rmtree(directory_path)
        os.makedirs(directory_path, exist_ok=True)
    except Exception as e:
        print(f"Error clearing directory {directory_path}: {e}")

def should_ignore_file(file_path, gitignore_patterns):
    """Check if a file should be ignored based on gitignore patterns"""
    file_path = file_path.replace('\\', '/')  # Normalize path separators
    
    for pattern in gitignore_patterns:
        # Basic gitignore pattern matching
        if pattern.startswith('/'):  # Patterns starting with / match from the root of the repo
            pattern = pattern[1:]
            if fnmatch.fnmatch(file_path, pattern):
                return True
        else:  # Patterns without / match anywhere in the path
            if fnmatch.fnmatch(file_path, pattern) or any(fnmatch.fnmatch(part, pattern) for part in file_path.split('/')):
                return True
                
        # Handle directory pattern (ending with /)
        if pattern.endswith('/'):
            dir_pattern = pattern[:-1]
            for part in file_path.split('/')[:-1]:  # Check each directory part
                if fnmatch.fnmatch(part, dir_pattern):
                    return True
    
    return False

@app.route('/structure')
def show_structure():
    if 'file_structure' not in session:
        return redirect(url_for('index'))
    
    file_structure = session['file_structure']
    return render_template('structure.html', structure=file_structure)

@app.route('/generate_explanation', methods=['POST'])
def generate_explanation():
    if 'file_structure' not in session:
        return jsonify({'error': 'No file structure found'}), 400
    
    file_structure = session['file_structure']
    
    # Create a base prompt with the project structure
    base_prompt = "# Project Structure\n\n```\n"
    base_prompt += format_structure_for_prompt(file_structure)
    base_prompt += "```\n\n# File Contents\n\n"
    
    # Create project overview markdown
    project_md = "# Project Overview\n\n## Structure\n\n```\n"
    project_md += format_structure_for_prompt(file_structure)
    project_md += "```\n\n## Files\n\n"
    
    # Process each file and generate explanation
    for file_info in get_all_files(file_structure):
        file_path = file_info['path']
        relative_path = os.path.relpath(file_path, app.config['UPLOAD_FOLDER'])
        
        # Skip files that are too large or binary
        if is_binary_file(file_path) or os.path.getsize(file_path) > 1000000:  # 1MB limit
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            continue
        
        # Add file content to the base prompt
        file_prompt = base_prompt + f"## {relative_path}\n\n```\n{content}\n```\n\n"
        file_prompt += f"Please explain the file {relative_path} line by line, detailing its purpose and functionality."
        
        # Call OpenRouter API to explain the file
        explanation = get_explanation_from_openrouter(file_prompt, relative_path)
        
        # Create markdown file for this file's explanation
        output_md_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{os.path.basename(file_path)}.md")
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Explanation for {relative_path}\n\n{explanation}")
        
        # Add summary to project markdown
        project_md += f"### [{relative_path}]({os.path.basename(file_path)}.md)\n\n"
        project_md += f"{get_summary_from_explanation(explanation)}\n\n"
    
    # Save project overview markdown
    with open(os.path.join(app.config['OUTPUT_FOLDER'], 'project_overview.md'), 'w', encoding='utf-8') as f:
        f.write(project_md)
    
    return jsonify({
        'success': True, 
        'message': 'Explanations generated successfully',
        'overview_path': 'output/project_overview.md'
    })

@app.route('/output/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

def get_folder_structure(folder_path):
    result = []
    
    for root, dirs, files in os.walk(folder_path):
        rel_path = os.path.relpath(root, folder_path)
        if rel_path == '.':
            # Add files from the root directory
            for file in files:
                file_path = os.path.join(root, file)
                result.append({
                    'name': file,
                    'path': file_path,
                    'type': 'file',
                    'size': os.path.getsize(file_path)
                })
                
            # Add directories from the root level
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                result.append({
                    'name': dir_name,
                    'path': dir_path,
                    'type': 'folder',
                    'children': get_folder_structure(dir_path)
                })
            
            break  # Only process the top level
    
    return result

def get_all_files(structure, path_prefix=''):
    files = []
    
    for item in structure:
        if item['type'] == 'file':
            files.append(item)
        elif item['type'] == 'folder':
            files.extend(get_all_files(item.get('children', []), 
                                      os.path.join(path_prefix, item['name'])))
    
    return files

def format_structure_for_prompt(structure, level=0):
    result = ""
    indent = "  " * level
    
    for item in structure:
        if item['type'] == 'folder':
            result += f"{indent}📁 {item['name']}/\n"
            if 'children' in item:
                result += format_structure_for_prompt(item['children'], level + 1)
        else:
            result += f"{indent}📄 {item['name']}\n"
            
    return result

def get_explanation_from_openrouter(prompt, file_path):
    """Generate explanation using Google's Gemini API"""
    try:
        # Generate content using Gemini
        response = model.generate_content(prompt)
        
        if response.text:
            return response.text
        else:
            error_message = "No content in API response"
            print(error_message)
            return f"Failed to generate explanation: {error_message}"
            
    except Exception as e:
        print(f"Error generating explanation for {file_path}: {e}")
        return f"Failed to generate explanation: {str(e)}"

def get_summary_from_explanation(explanation):
    # Extract a brief summary from the full explanation
    # Just taking the first paragraph as a simple approach
    lines = explanation.split('\n')
    summary = ""
    for line in lines:
        if line.strip() and not line.startswith('#'):
            summary = line
            break
    
    if not summary and lines:
        summary = lines[0]
    
    return summary

def is_binary_file(file_path):
    """Check if a file is binary (non-text)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1024)
        return False
    except UnicodeDecodeError:
        return True

if __name__ == '__main__':
    app.run(debug=True)