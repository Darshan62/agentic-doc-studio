"""
Packages the project source into a zip for the "Download Project ZIP" button.
Secrets (.env), generated files and user uploads are left out.
"""
import os
import zipfile

OUTPUT_ZIP = "public/downloads/multi_agent_doc_ppt_system.zip"
EXCLUDED_DIRS = {"node_modules", "dist", "__pycache__", "output", "versions", "uploads", "downloads"}
EXCLUDED_EXTENSIONS = (".pyc", ".db")  # .db = the knowledge base with indexed user files
ALLOWED_DOTFILES = {".env.example", ".gitignore"}


def should_skip(filename: str) -> bool:
    if filename.endswith(EXCLUDED_EXTENSIONS):
        return True
    # Dotfiles such as .env hold secrets
    return filename.startswith(".") and filename not in ALLOWED_DOTFILES


def package_project(output_zip: str = OUTPUT_ZIP) -> str:
    os.makedirs(os.path.dirname(output_zip), exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("."):
            # Editing dirs in place stops os.walk from descending into them
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            for filename in files:
                if not should_skip(filename):
                    path = os.path.join(root, filename)
                    zf.write(path, os.path.relpath(path, "."))
    return output_zip
