from pathlib import Path

EXCLUDE_DIRS = {"venv", ".venv", "env", "__pycache__", ".git", ".ipynb_checkpoints"}

def print_tree(path, prefix=""):
    items = sorted(
        [p for p in path.iterdir() if p.name not in EXCLUDE_DIRS],
        key=lambda p: (p.is_file(), p.name.lower())
    )
    for i, item in enumerate(items):
        connector = "└── " if i == len(items) - 1 else "├── "
        print(prefix + connector + item.name)
        if item.is_dir():
            extension = "    " if i == len(items) - 1 else "│   "
            print_tree(item, prefix + extension)

root = Path(".").resolve()
print(root.name)
print_tree(root)
