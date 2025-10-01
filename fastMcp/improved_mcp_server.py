import os
import tempfile
import uuid
import base64
from pathlib import Path
from typing import Optional
import logging
import shutil
from fastmcp import FastMCP
from markitdown import MarkItDown

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.html', '.xlsx', '.pptx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Create secure temporary directories
TEMP_BASE = tempfile.mkdtemp(prefix="mcp_converter_")
UPLOAD_DIR = os.path.join(TEMP_BASE, "uploads")
OUTPUT_DIR = os.path.join(TEMP_BASE, "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

mcp = FastMCP("File Converter MCP Server", host="0.0.0.0", port=8001)

def validate_file_content(filename: str, content_size: int) -> tuple[bool, str]:
    """Validate file before processing."""
    try:
        path = Path(filename)
        
        # Check file extension
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return False, f"File type not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        
        # Check file size
        if content_size > MAX_FILE_SIZE:
            return False, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            
        return True, "Valid"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def save_uploaded_file(filename: str, content: bytes) -> str:
    """Save uploaded file content to temporary location."""
    # Generate unique filename to avoid conflicts
    file_id = uuid.uuid4().hex[:8]
    safe_filename = f"{file_id}_{Path(filename).name}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    return file_path

@mcp.tool
def convert_file_from_base64(filename: str, file_content_base64: str, output_name: Optional[str] = None) -> str:
    """
    Converts a file to markdown format using base64 encoded content.
    
    Args:
        filename: Original filename (used for extension validation)
        file_content_base64: Base64 encoded file content
        output_name: Optional custom name for output file (without extension)
    
    Returns:
        Status message with converted markdown content
    """
    temp_file = None
    try:
        # Decode base64 content
        try:
            file_content = base64.b64decode(file_content_base64)
        except Exception as e:
            return f"❌ Invalid base64 content: {str(e)}"
        
        # Validate file
        is_valid, message = validate_file_content(filename, len(file_content))
        if not is_valid:
            logger.warning(f"File validation failed: {message}")
            return f"❌ Error: {message}"
        
        # Save temporary file
        temp_file = save_uploaded_file(filename, file_content)
        
        # Convert file
        md = MarkItDown(enable_plugins=False)
        result = md.convert(temp_file)
        
        logger.info(f"Successfully converted {filename}")
        return f"✅ Conversion successful!\n\n--- MARKDOWN CONTENT ---\n{result.text_content}"
        
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        return f"❌ Conversion failed: {str(e)}"
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")

@mcp.tool
def convert_file_from_path(file_path: str, output_name: Optional[str] = None) -> str:
    """
    Converts a file to markdown format from a server-accessible path.
    ⚠️  Only use this for files you know are accessible on the server.
    
    Args:
        file_path: Server path to the input file
        output_name: Optional custom name for output file (without extension)
    
    Returns:
        Status message with output file path
    """
    try:
        # Security check - ensure path is within allowed directories
        abs_path = os.path.abspath(file_path)
        if not (abs_path.startswith('/tmp/') or abs_path.startswith('/shared/')):
            return "❌ Access denied: File must be in /tmp/ or /shared/ directory"
        
        # Check if file exists and is readable
        if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
            return f"❌ File not accessible: {file_path}"
        
        # Validate file
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        is_valid, message = validate_file_content(filename, file_size)
        if not is_valid:
            logger.warning(f"File validation failed: {message}")
            return f"❌ Error: {message}"
        
        # Convert file
        md = MarkItDown(enable_plugins=False)
        result = md.convert(file_path)
        
        # Generate unique output filename
        if output_name:
            output_filename = f"{output_name}_{uuid.uuid4().hex[:8]}.md"
        else:
            input_name = Path(file_path).stem
            output_filename = f"{input_name}_{uuid.uuid4().hex[:8]}.md"
        
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Save output
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.text_content)
        
        logger.info(f"Successfully converted {file_path} to {output_path}")
        return f"✅ Conversion successful! Output saved to: {output_path}"
        
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        return f"❌ Conversion failed: {str(e)}"

@mcp.tool
def list_supported_formats() -> str:
    """Returns list of supported file formats."""
    return f"Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

@mcp.tool
def get_server_info() -> str:
    """Returns server information and usage guidelines."""
    return f"""
📋 MCP File Converter Server Info:
- Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}
- Maximum file size: {MAX_FILE_SIZE // (1024*1024)}MB
- Output directory: {OUTPUT_DIR}
- Server version: 1.0.0

📖 Usage:
1. Use convert_file(file_path) to convert files
2. Files must be accessible by the server
3. Converted files are saved with unique names to prevent conflicts
"""

def cleanup_temp_files():
    """Clean up temporary files on server shutdown."""
    try:
        if os.path.exists(TEMP_BASE):
            shutil.rmtree(TEMP_BASE)
            logger.info("Cleaned up temporary files")
    except Exception as e:
        logger.error(f"Failed to cleanup temp files: {e}")

@mcp.tool
def cleanup_old_files() -> str:
    """Manual cleanup of old temporary files (admin function)."""
    try:
        count = 0
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                # Remove files older than 1 hour
                if os.path.getctime(file_path) < (os.time.time() - 3600):
                    os.remove(file_path)
                    count += 1
        return f"✅ Cleaned up {count} old files"
    except Exception as e:
        return f"❌ Cleanup failed: {str(e)}"

if __name__ == "__main__":
    import atexit
    atexit.register(cleanup_temp_files)
    
    logger.info("Starting MCP File Converter Server...")
    logger.info(f"Temporary base directory: {TEMP_BASE}")
    logger.info(f"Upload directory: {UPLOAD_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("Use convert_file_from_base64() for uploaded files")
    logger.info("Use convert_file_from_path() for server-accessible files")
    
    try:
        mcp.run(transport="streamable-http")
    finally:
        cleanup_temp_files()