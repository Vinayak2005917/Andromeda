const http = require("http");
const fs = require("fs");
const path = require("path");

const root = __dirname;
const port = 5500;
const contentTypes = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".jpg": "image/jpeg",
    ".png": "image/png",
};

http.createServer((request, response) => {
    const requestedPath = decodeURIComponent(request.url.split("?")[0]);
    const relativePath = requestedPath === "/" ? "/index.html" : requestedPath;
    const filePath = path.resolve(root, `.${relativePath}`);

    if (!filePath.startsWith(root + path.sep)) {
        response.writeHead(400);
        response.end("Invalid path");
        return;
    }

    fs.readFile(filePath, (error, data) => {
        if (error) {
            response.writeHead(error.code === "ENOENT" ? 404 : 500);
            response.end("Not found");
            return;
        }
        response.writeHead(200, {
            "Content-Type": contentTypes[path.extname(filePath)] || "application/octet-stream",
        });
        response.end(data);
    });
}).listen(port, "127.0.0.1", () => {
    console.log(`Andromeda frontend running at http://127.0.0.1:${port}`);
});
