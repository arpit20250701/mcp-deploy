from fastmcp import FastMCP
from markitdown import MarkItDown
import os

# Initialize FastMCP
mcp = FastMCP("repo-folder-markdown-converter", host="0.0.0.0", port=8080)

@mcp.tool
def convert_folder(folder_path: str) -> str:
    """
    Converts all supported files in a given folder to Markdown using MarkItDown.
    Stores results in a 'markdown_output' subfolder inside the same directory.
    """
    # Resolve absolute path (assuming workspace-relative input)
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return f"❌ Path not found or not a folder: {folder_path}"

    md = MarkItDown(enable_plugins=False)
    output_dir = os.path.join(folder_path, "markdown_output")
    os.makedirs(output_dir, exist_ok=True)

    processed = []
    skipped = []

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            try:
                result = md.convert(file_path)
                output_file = os.path.join(
                    output_dir, f"{os.path.splitext(filename)[0]}.md"
                )
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result.text_content)
                processed.append(filename)
            except Exception as e:
                skipped.append(f"{filename} ({e})")

    summary = f"✅ Converted {len(processed)} files. Markdown saved to: {output_dir}\n"
    if skipped:
        summary += f"⚠️ Skipped {len(skipped)} files: {', '.join(skipped)}"
    return summary

if __name__ == "__main__":
    mcp.run()
