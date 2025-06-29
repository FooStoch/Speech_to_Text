let socket;

async function startRecording() {
    try {
        // Get microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        document.getElementById("status").innerText = "Listening... Speak now!";
        
        // Initialize WebSocket
        socket = new WebSocket('wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000');
        
        socket.onmessage = (message) => {
            const response = JSON.parse(message.data);
            if (response.message_type === 'PartialTranscript') {
                document.getElementById("transcript").innerText = response.text;
                window.parent.postMessage({
                    type: "transcript",
                    text: response.text
                }, '*');
            }
        };

        socket.onopen = () => {
            // Send auth header
            socket.send(JSON.stringify({
                authorization: "YOUR_API_KEY"
            }));
            
            // Process audio
            const audioContext = new AudioContext({ sampleRate: 16000 });
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            source.connect(processor);
            processor.connect(audioContext.destination);
            
            processor.onaudioprocess = (e) => {
                const audioData = e.inputBuffer.getChannelData(0);
                const int16Array = new Int16Array(audioData.length);
                for (let i = 0; i < audioData.length; i++) {
                    int16Array[i] = Math.min(32767, Math.max(-32768, audioData[i] * 32767));
                }
                socket.send(JSON.stringify({
                    audio_data: Array.from(int16Array)
                }));
            };
        };

        socket.onerror = (error) => {
            document.getElementById("status").innerText = "Error occurred";
            window.parent.postMessage({
                type: "error",
                message: `Error: ${error.message}`
            }, '*');
        };

    } catch (error) {
        window.parent.postMessage({
            type: "error",
            message: `Microphone error: ${error.message}`
        }, '*');
    }
}

// Start immediately
startRecording();
