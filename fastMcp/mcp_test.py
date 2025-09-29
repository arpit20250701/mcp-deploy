import os
import tempfile
import base64
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from markitdown import MarkItDown
import uvicorn

# Initialize FastAPI
app = FastAPI(title="File-to-Markdown Converter", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize FastMCP with dependencies for remote access
mcp = FastMCP(
    "file-to-markdown-converter",
    dependencies=[]  # Add any FastAPI dependencies here if needed
)

# Initialize MarkItDown converter
md_converter = MarkItDown(enable_plugins=True)


def convert_file_to_md(file_path: str, filename: str) -> str:
    """Convert a file to markdown using MarkItDown."""
    try:
        result = md_converter.convert(file_path)
        return result.text_content
    except Exception as e:
        raise Exception(f"Conversion error for {filename}: {str(e)}")


# ===== MCP Tools =====

@mcp.tool()
def convert_file_from_path(file_path: str) -> str:
    """
    Convert a file to markdown format using its local file path.
    
    Args:
        file_path: Absolute path to the file to convert
        
    Returns:
        Markdown content of the converted file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    filename = os.path.basename(file_path)
    markdown = convert_file_to_md(file_path, filename)
    
    return f"# Converted: {filename}\n\n{markdown}"


@mcp.tool()
def convert_file_from_base64(content: str, filename: str) -> str:
    """
    Convert a file to markdown format using base64-encoded content.
    
    Args:
        content: Base64-encoded file content
        filename: Original filename with extension (e.g., 'document.pdf')
        
    Returns:
        Markdown content of the converted file
    """
    tmp_path = None
    try:
        # Decode base64 content
        file_bytes = base64.b64decode(content)
        
        # Create temp file with proper extension
        suffix = os.path.splitext(filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        # Convert to markdown
        markdown = convert_file_to_md(tmp_path, filename)
        
        return f"# Converted: {filename}\n\n{markdown}"
        
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@mcp.tool()
def list_supported_formats() -> dict:
    """
    Get a list of all supported file formats for conversion.
    
    Returns:
        Dictionary of format categories and their supported types
    """
    return {
        "documents": ["PDF", "DOCX", "DOC", "PPTX", "PPT", "RTF"],
        "spreadsheets": ["XLSX", "XLS", "CSV", "TSV"],
        "images": ["PNG", "JPG", "JPEG", "GIF", "BMP", "TIFF", "WEBP"],
        "web": ["HTML", "HTM", "XML"],
        "code": ["PY", "JS", "JAVA", "CPP", "C", "GO", "RS", "TS", "JSX", "TSX"],
        "data": ["JSON", "YAML", "YML", "TOML", "INI"],
        "text": ["TXT", "MD", "MARKDOWN", "RST"],
        "archives": ["ZIP"],
        "audio": ["MP3", "WAV", "M4A", "FLAC"],
        "other": ["EML", "MSG"]
    }


# ===== FastAPI Endpoints =====

@app.get("/")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "file-to-markdown-converter",
        "version": "1.0.0"
    }


@app.post("/convert")
async def convert_uploaded_file(file: UploadFile = File(...)):
    """
    Convert an uploaded file to markdown format.
    
    Upload a file and receive its markdown representation.
    """
    tmp_path = None
    try:
        # Save uploaded file to temp location
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Convert to markdown
        markdown = convert_file_to_md(tmp_path, file.filename)
        
        return {
            "filename": file.filename,
            "markdown": markdown,
            "size": len(content)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Conversion failed: {str(e)}"
        )
        
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@app.post("/convert/base64")
async def convert_base64_file(content: str, filename: str):
    """
    Convert a base64-encoded file to markdown format.
    
    Send base64-encoded file content and filename.
    """
    tmp_path = None
    try:
        # Decode base64 content
        file_bytes = base64.b64decode(content)
        
        # Save to temp file
        suffix = os.path.splitext(filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        # Convert to markdown
        markdown = convert_file_to_md(tmp_path, filename)
        
        return {
            "filename": filename,
            "markdown": markdown,
            "size": len(file_bytes)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Conversion failed: {str(e)}"
        )
        
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@app.get("/formats")
def get_supported_formats():
    """Get list of supported file formats."""
    return list_supported_formats()


# Mount MCP server to FastAPI
# app.mount("/mcp", mcp.get_asgi_app())


if __name__ == "__main__":
    # mcp.run(transport="streamable-http", host="0.0.1.1", port=8003)
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8003,
        log_level="info"
    )
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )