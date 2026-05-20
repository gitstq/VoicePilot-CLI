"""
VoicePilot-CLI setup script.

Provides setuptools configuration with console_scripts entry point
for the 'voicepilot' command.
"""

from setuptools import setup, find_packages

setup(
    name="voicepilot-cli",
    version="0.1.0",
    description="A lightweight local voice AI agent CLI engine",
    long_description=open("README.md", encoding="utf-8").read() if True else "",
    long_description_content_type="text/markdown",
    author="VoicePilot-CLI Contributors",
    license="MIT",
    python_requires=">=3.8",
    packages=find_packages(include=["voicepilot_cli*"]),
    package_data={
        "voicepilot_cli": ["py.typed"],
    },
    entry_points={
        "console_scripts": [
            "voicepilot=voicepilot_cli.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
