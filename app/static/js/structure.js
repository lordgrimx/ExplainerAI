document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generate-btn');
    const loadingSection = document.getElementById('loading');
    const resultsSection = document.getElementById('results');
    const overviewLink = document.getElementById('overview-link');
    
    // Toggle folder visibility
    const folderNames = document.querySelectorAll('.folder-name');
    folderNames.forEach(folder => {
        folder.addEventListener('click', function() {
            const parentLi = this.parentElement;
            const childUl = parentLi.querySelector('ul');
            if (childUl) {
                childUl.classList.toggle('hidden');
                
                // Update folder icon
                if (childUl.classList.contains('hidden')) {
                    this.textContent = this.textContent.replace('📂', '📁');
                } else {
                    this.textContent = this.textContent.replace('📁', '📂');
                }
            }
        });
    });
    
    // Generate explanations when button is clicked
    generateBtn.addEventListener('click', function() {
        // Show loading indicator
        loadingSection.classList.remove('hidden');
        generateBtn.disabled = true;
        
        // Make AJAX request to generate explanations
        fetch('/generate_explanation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            loadingSection.classList.add('hidden');
            
            // Show results section
            resultsSection.classList.remove('hidden');
            
            // Update download link
            if (data.overview_path) {
                overviewLink.href = data.overview_path;
            }
            
            // Enable generate button again
            generateBtn.disabled = false;
        })
        .catch(error => {
            console.error('Error generating explanations:', error);
            
            // Hide loading indicator
            loadingSection.classList.add('hidden');
            
            // Show error message
            alert('An error occurred while generating explanations. Please try again.');
            
            // Enable generate button again
            generateBtn.disabled = false;
        });
    });
});