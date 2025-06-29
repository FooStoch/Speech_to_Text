// audio_handler.js
let socket;
let mediaRecorder;
let audioContext;
let processor;

async function startRecording(apiKey) {
    try {
        // Initialize WebSocket connection
        socket = new WebSocket('wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000');
        
        socket.onmessage = (message) => {
            const response = JSON.parse(message.data);
            if (response.message_type === 'PartialTranscript') {
                sendToStreamlit({
                    type: "transcript",
                    text: response.text
                });
            }
        };

        socket.onopen = () => {
            sendToStreamlit({
                type: "status",
                message: "Connected - Speak now!"
            });
            
            // Start microphone access
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    audioContext = new AudioContext({ sampleRate: 16000 });
                    const source = audioContext.createMediaStreamSource(stream);
                    processor = audioContext.createScriptProcessor(4096, 1, 1);
                    
                    source.connect(processor);
                    processor.connect(audioContext.destination);
                    
                    processor.onaudioprocess = (e) => {
                        const audioData = e.inputBuffer.getChannelData(0);
                        const int16Array = floatTo16BitPCM(audioData);
                        const binaryString = arrayBufferToString(int16Array.buffer);
                        
                        if (socket.readyState === WebSocket.OPEN) {
                            socket.send(JSON.stringify({
                                audio_data: binaryString
                            }));
                        }
                    };
                    
                    // Send auth message
                    socket.send(JSON.stringify({
                        authorization: apiKey
                    }));
                });
        };

        socket.onerror = (error) => {
            sendToStreamlit({
                type: "error",
                message: `WebSocket error: ${error.message}`
            });
        };

        socket.onclose = () => {
            sendToStreamlit({
                type: "status",
                message: "Connection closed"
            });
        };

    } catch (error) {
        sendToStreamlit({
            type: "error",
            message: `Recording error: ${error.message}`
        });
    }
}

// Helper functions
function floatTo16BitPCM(input) {
    const output = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
        output[i] = Math.max(-32768, Math.min(32767, input[i] * 32767));
    }
    return output;
}

function arrayBufferToString(buffer) {
    return btoa(String.fromCharCode.apply(null, new Uint8Array(buffer)));
}

function sendToStreamlit(message) {
    window.parent.postMessage(message, '*');
}
