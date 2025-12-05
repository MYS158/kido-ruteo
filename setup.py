from pathlib import Path
from setuptools import find_packages, setup

README = Path(__file__).parent / "README.md"

setup(
    name="kido-ruteo",
    version="0.1.0",
    description="Pipeline de ruteo y validación para flujos OD KIDO",
    long_description=README.read_text(encoding="utf-8") if README.exists() else "",
    long_description_content_type="text/markdown",
    author="Miguel Antonio Muñoz Beltrán",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "pandas",
        "geopandas",
        "shapely",
        "networkx",
        "numpy",
        "pyyaml",
        "click",
    ],
    entry_points={
        "console_scripts": [
            "kido-run=kido_ruteo.pipeline:run_pipeline",
            "kido-matrices=kido_ruteo.pipeline:generate_matrices",
        ],
    },
)
