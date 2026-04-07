from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="qtest-cli",
    version="1.0.0",
    description="CLI tool for qTest Manager - list folders and add test cases",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "qtest=qtest_cli.main:main",
        ],
    },
)
