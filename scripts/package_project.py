"""
Packages the entire project into a clean, standalone zip file excluding node_modules, dist, and cache artifacts.
"""
import os
import zipfile

def package_project(output_zip: str = "public/downloads/multi_agent_doc_ppt_system.zip"):
    os.makedirs(os.path.dirname(output_zip), exist_ok=True)
    root_dir = "."
    excluded_dirs = {
        "node_modules", ".git", "dist", "__pycache__", ".next", ".cache",
        "public/downloads", "versions"
    }
    excluded_extensions = {".pyc", ".pyo", ".pyd", ".DS_Store"}

    print(f"Creating project zip archive: {output_zip}")
    file_count = 0
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(root_dir):
            # Prune excluded directories
            rel_dir = os.path.relpath(root, root_dir)
            parts = rel_dir.split(os.sep)
            if any(p in excluded_dirs or p.startswith(".") for p in parts if p != "."):
                continue

            for f in files:
                if any(f.endswith(ext) for ext in excluded_extensions):
                    continue
                full_path = os.path.join(root, f)
                arc_name = os.path.relpath(full_path, root_dir)
                # Don't include the output zip itself
                if os.path.abspath(full_path) == os.path.abspath(output_zip):
                    continue
                zf.write(full_path, arc_name)
                file_count += 1

    size_mb = os.path.getsize(output_zip) / (1024 * 1024)
    print(f"Archive created with {file_count} files ({size_mb:.2f} MB) at {output_zip}")
    return output_zip

if __name__ == "__main__":
    package_project()
