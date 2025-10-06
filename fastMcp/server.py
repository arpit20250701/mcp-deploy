import os
from pathlib import Path
from fastmcp import FastMCP
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from markitdown import MarkItDown
import tempfile
import shutil

mcp = FastMCP("docling-mcp")


@mcp.tool
def convert_file_to_markdown(file_path: str) -> str:
    """
    Convert a file to Markdown format.
    
    Args:
        file_path: Path to the file to convert
        
    Returns:
        The Markdown content of the converted file
    """
    input_path = Path(file_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Convert based on file type
    md_text = ""
    if input_path.suffix.lower() == ".pdf":
        # Use docling for PDF files
        conv = DocumentConverter(pipeline_options=PdfPipelineOptions(do_ocr=True))
        result = conv.convert(str(input_path))
        md_text = result.document.export_to_markdown()
    else:
        # Use MarkItDown for other file types
        md = MarkItDown(enable_plugins=False)
        result = md.convert(str(input_path))
        md_text = result.text_content

    # Save Markdown file next to original
    output_path = input_path.with_suffix(".md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    return f"File converted successfully. Markdown saved to: {output_path}\n\nContent:\n{md_text}"


@mcp.tool
def convert_file_content_to_markdown(content: str, filename: str, output_dir: str = "/tmp") -> str:
    """
    Convert file content to Markdown format by first saving it to a temporary file.
    
    Args:
        content: The file content as a string (base64 encoded for binary files)
        filename: Name of the file (used to determine file type)
        output_dir: Directory to save the temporary and output files
        
    Returns:
        The Markdown content of the converted file
    """
    import base64
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save content to temporary file
    input_path = output_path / filename
    
    try:
        # Try to decode as base64 first (for binary files)
        decoded_content = base64.b64decode(content)
        with open(input_path, "wb") as f:
            f.write(decoded_content)
    except:
        # If base64 decoding fails, treat as text
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    # Convert using the existing function
    result = convert_file_to_markdown(str(input_path))
    
    # Clean up temporary file
    try:
        input_path.unlink()
    except:
        pass  # Ignore cleanup errors
    
    return result


if __name__ == "__main__":
    mcp.run()
