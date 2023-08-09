self.addEventListener('message', function(event) {
    const { presignedUrl, chunk } = event.data;
    if (presignedUrl == null || chunk==null){
        return;
    }

    fetch(presignedUrl, {
        method: "PUT",
        body: chunk,
    })
    .then((response) => {
        if (!response.ok) {
            throw new Error("Chunk upload failed");
        }
        const etag = response.headers.get('ETag');
        self.postMessage({ etag });
    })
    .catch((error) => {
        console.error(`Error uploading chunk:`, error);
        self.postMessage({ error: error.message });
    });
});
