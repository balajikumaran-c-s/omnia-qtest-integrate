# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Setup script for qtest-cli package."""

from setuptools import setup, find_packages  # pylint: disable=import-error

with open("requirements.txt", encoding="utf-8") as req_file:
    REQUIREMENTS = [
        line.strip() for line in req_file
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="qtest-cli",
    version="1.0.0",
    description="CLI tool for qTest Manager - list folders and add test cases",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=REQUIREMENTS,
    entry_points={
        "console_scripts": [
            "qtest=qtest_cli.main:main",
        ],
    },
)
