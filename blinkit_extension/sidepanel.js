document.getElementById('upload-btn').addEventListener('click', async () => {
    const fileInput = document.getElementById('pdf-upload');
    const statusDiv = document.getElementById('status');
    const resultsDiv = document.getElementById('results');

    if (!fileInput.files.length) {
        statusDiv.innerText = "Please select a vendor PDF first.";
        statusDiv.style.color = "#dc2626";
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    statusDiv.innerText = "Processing via Qwen AI... (Takes ~3 seconds)";
    statusDiv.style.color = "#0052cc";
    resultsDiv.innerHTML = "";

    try {
        const response = await fetch('http://127.0.0.1:5000/extract-catalog', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("API Request Failed. Is the Flask server running?");

        const data = await response.json();
        
        // Setup Indian Rupee Formatter
        const rupeeFormatter = new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0 // Removes the .00 at the end
        });
        
        let tableHTML = `<table>
            <tr><th>Item</th><th>Category</th><th>MRP</th><th>SEO Description</th></tr>`;
        
        data.products.forEach(p => {
            // Apply the rupee format
            const formattedPrice = rupeeFormatter.format(p.mrp);
            
            tableHTML += `<tr>
                <td><strong>${p.item_name}</strong></td>
                <td><span class="category-badge">${p.category}</span></td>
                <td class="mrp-text">${formattedPrice}</td>
                <td>${p.seo_description}</td>
            </tr>`;
        });
        tableHTML += `</table>`;
        
        resultsDiv.innerHTML = tableHTML;
        statusDiv.innerText = `Successfully extracted ${data.products.length} catalog items.`;
        statusDiv.style.color = "#059669"; // Success green
        
    } catch (error) {
        statusDiv.innerText = "Error: " + error.message;
        statusDiv.style.color = "#dc2626"; // Error red
    }
});