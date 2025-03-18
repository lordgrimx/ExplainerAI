document.addEventListener('DOMContentLoaded', function() {
    const folderInput = document.getElementById('folder-input');
    const fileListContainer = document.getElementById('file-list-container');
    
    folderInput.addEventListener('change', function(e) {
        const files = e.target.files;
        
        if (files.length === 0) {
            fileListContainer.innerHTML = '<p>No files selected</p>';
            return;
        }
        
        // Clear previous content
        fileListContainer.innerHTML = '';
        
        // Create a file list element
        const fileList = document.createElement('ul');
        fileList.className = 'file-list';
        
        // Keep track of displayed paths to avoid duplicates
        const displayedPaths = new Set();
        
        // Create a map to organize files by directory
        const fileTree = {};
        
        // Process each file
        Array.from(files).forEach(file => {
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
        totalFiles.textContent = `Total: ${files.length} files selected`;
        fileListContainer.appendChild(totalFiles);
        
        // Add the file list
        fileListContainer.appendChild(fileList);
    });
});