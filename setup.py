"""Setup script for the PDFMaster package."""

from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
REQUIREMENTS = [
    line.strip()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.strip().startswith("#")
]

setup(
    name="pdfmaster",
    version="0.6.0",
    description="A professional PDF viewer and editor for Windows",
    long_description=README,
    long_description_content_type="text/markdown",
    author="PDFMaster Contributors",
    license="MIT",
    python_requires=">=3.10",
    packages=find_packages(include=["src", "src.*"]),
    include_package_data=True,
    install_requires=REQUIREMENTS,
    extras_require={
        "ocr": ["pytesseract>=0.3.10"],
        "ocr-easyocr": ["easyocr>=1.7.0"],
        "installer": ["pyinstaller>=6.0.0"],
        "all": ["pytesseract>=0.3.10", "pyinstaller>=6.0.0"],
    },
    entry_points={
        "console_scripts": [
            "pdfmaster=src.main:main",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business",
        "Environment :: X11 Applications :: Qt",
    ],
    project_urls={
        "Documentation": "https://github.com/pdfmaster/pdfmaster",
        "Source": "https://github.com/pdfmaster/pdfmaster",
    },
)
