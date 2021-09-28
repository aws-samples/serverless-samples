# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import setuptools


setuptools.setup(
    name="lib",
    version="0.0.1",

    description="Serverless API CDK Python app",
    long_description="Serverless API CDK Python app",
    long_description_content_type="text/markdown",

    author="AWS",

    package_dir={"": "lib"},
    packages=setuptools.find_packages(where="lib"),

    install_requires=[
        "aws-cdk.core>=1.107.0"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 5 - Production/Stable",

        "Intended Audience :: Developers",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
