document.addEventListener('DOMContentLoaded', () => {
    const promptInput = document.getElementById('prompt-input');
    const generateBtn = document.getElementById('generate-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const videoContainer = document.getElementById('video-container');

    generateBtn.addEventListener('click', async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert('Please enter a prompt!');
            return;
        }

        // --- UI Changes for Loading State ---
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
        loadingSpinner.classList.remove('hidden');
        videoContainer.innerHTML = ''; // Clear previous video

        try {
            // --- API Call to our Flask Backend ---
            // Change the absolute URL to a relative one
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: prompt }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // --- Display the Generated Video ---
            if (data.video_url) {
                const videoElement = document.createElement('video');
                videoElement.src = data.video_url;
                videoElement.controls = true;
                videoElement.autoplay = true;
                videoElement.muted = true; // Autoplay often requires video to be muted
                videoContainer.appendChild(videoElement);
            } else {
                throw new Error(data.error || 'Failed to get video URL.');
            }

        } catch (error) {
            // --- Error Handling ---
            console.error('Error:', error);
            videoContainer.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
        } finally {
            // --- Reset UI after completion or error ---
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Video';
            loadingSpinner.classList.add('hidden');
        }
    });
});
