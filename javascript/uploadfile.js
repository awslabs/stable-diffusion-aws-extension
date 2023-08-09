self.addEventListener('message', (event) => {
    const { file, presignedUrls, chunkSize } = event.data;
    const fileSize = file.size;
    const totalChunks = Math.ceil(fileSize / chunkSize);

    const parts = [];

    for (let currentChunk = 0; currentChunk < totalChunks; currentChunk++) {
        const chunk = file.slice(
            currentChunk * chunkSize,
            (currentChunk + 1) * chunkSize
        );

        fetch(presignedUrls[currentChunk], {
            method: "PUT",
            body: chunk,
        })
        .then((response) => {
            if (!response.ok) {
                throw new Error("Chunk upload failed");
            }
            const etag = response.headers.get('ETag');
            parts.push({
                ETag: etag,
                PartNumber: currentChunk + 1
            });
            const progress = (currentChunk / totalChunks) * 100;
            self.postMessage({ progress });
        })
        .catch((error) => {
            console.error(`Error uploading chunk ${currentChunk}:`, error);
            self.postMessage({ error: `Error uploading chunk ${currentChunk}` });
        });
    }

    self.postMessage({ parts });
});