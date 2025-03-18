document.addEventListener('DOMContentLoaded', function() {
    const folderInput = document.getElementById('folder-input');
    const fileListContainer = document.getElementById('file-list-container');
    const languageSelect = document.getElementById('explanation-language');
    
    folderInput.addEventListener('change', function(e) {
        const files = e.target.files;
        
        if (files.length === 0) {
            fileListContainer.innerHTML = '<p>No files selected</p>';
            return;
        }
        
        // Process .gitignore files first
        let gitignorePatterns = [];
        Array.from(files).forEach(file => {
            const path = file.webkitRelativePath;
            const fileName = path.split('/').pop();
            
            if (fileName === '.gitignore') {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const content = e.target.result;
                    const patterns = content.split('\n')
                        .map(line => line.trim())
                        .filter(line => line && !line.startsWith('#'));
                    gitignorePatterns = gitignorePatterns.concat(patterns);
                    
                    // After processing gitignore, filter and display files
                    displayFilteredFiles(files, gitignorePatterns);
                };
                reader.readAsText(file);
            }
        });
        
        // If no .gitignore files found, just display all files
        if (gitignorePatterns.length === 0) {
            displayFilteredFiles(files, []);
        }
    });
    
    function displayFilteredFiles(files, gitignorePatterns) {
        // Clear previous content
        fileListContainer.innerHTML = '';
        
        // Filter files based on gitignore patterns
        const filteredFiles = Array.from(files).filter(file => {
            const path = file.webkitRelativePath;
            return !shouldIgnoreFile(path, gitignorePatterns);
        });
        
        if (filteredFiles.length === 0) {
            fileListContainer.innerHTML = '<p>No files to display after applying .gitignore filters</p>';
            return;
        }
        
        // Create a file list element
        const fileList = document.createElement('ul');
        fileList.className = 'file-list';
        
        // Keep track of displayed paths to avoid duplicates
        const displayedPaths = new Set();
        
        // Process each file
        filteredFiles.forEach(file => {
            const path = file.webkitRelativePath;
            const parts = path.split('/');
            
            // Only display top-level directories and files
            if (parts.length > 0) {
                const topLevel = parts[0];
                if (!displayedPaths.has(topLevel)) {
                    displayedPaths.add(topLevel);
                    
                    const listItem = document.createElement('li');
                    if (parts.length === 1) {
                        // It's a top-level file
                        listItem.innerHTML = `<span class="file-icon">📄</span> ${topLevel}`;
                    } else {
                        // It's a directory
                        listItem.innerHTML = `<span class="folder-icon">📁</span> ${topLevel}/`;
                    }
                    
                    fileList.appendChild(listItem);
                }
            }
        });
        
        // Display the total number of files
        const totalFiles = document.createElement('p');
        totalFiles.textContent = `Total: ${filteredFiles.length} files selected (${files.length - filteredFiles.length} excluded by .gitignore)`;
        fileListContainer.appendChild(totalFiles);
        
        // Add the file list
        fileListContainer.appendChild(fileList);
        
        // Update the form to only include filtered files
        updateFormFiles(filteredFiles);
    }
    
    function shouldIgnoreFile(filePath, patterns) {
        if (patterns.length === 0) return false;
        
        const parts = filePath.split('/');
        const fileName = parts.pop();
        
        for (const pattern of patterns) {
            // Handle simple exact matches
            if (pattern === fileName) return true;
            
            // Handle directory patterns (ending with /)
            if (pattern.endsWith('/')) {
                const dirPattern = pattern.slice(0, -1);
                if (parts.some(part => part === dirPattern)) return true;
            }
            
            // Handle wildcard patterns
            if (pattern.includes('*')) {
                const regexPattern = pattern
                    .replace(/\./g, '\\.')
                    .replace(/\*/g, '.*')
                    .replace(/\?/g, '.');
                const regex = new RegExp(`^${regexPattern}$`);
                
                if (regex.test(fileName)) return true;
                
                // Check if any directory in the path matches the pattern
                if (parts.some(part => regex.test(part))) return true;
            }
            
            // Handle file path patterns
            if (filePath.includes(pattern) || filePath.startsWith(pattern)) return true;
        }
        
        return false;
    }
    
    function updateFormFiles(filteredFiles) {
        const form = document.querySelector('form');
        
        form.onsubmit = function(e) {
            e.preventDefault();
            
            // Create a new FormData with filtered files and language
            const newFormData = new FormData();
            
            // Add the selected language
            newFormData.append('explanation-language', languageSelect.value);
            
            // Add all the filtered files
            filteredFiles.forEach(file => {
                newFormData.append('folder', file);
            });
            
            // Get the form's action URL and submit
            const actionUrl = form.getAttribute('action');
            
            fetch(actionUrl, {
                method: 'POST',
                body: newFormData
            }).then(response => {
                if (response.redirected) {
                    window.location.href = response.url;
                } else {
                    return response.json();
                }
            }).then(data => {
                if (data && data.error) {
                    alert('Error: ' + data.error);
                }
            }).catch(error => {
                console.error('Error submitting form:', error);
            });
        };
    }
});