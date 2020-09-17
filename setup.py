# Copyright 2019-2020, Ryan P. Kelly.

from setuptools import setup


setup(
    name="enctempfile",
    version="0.3",
    description="Transparently encrypted temporary files",
    author="Ryan P. Kelly",
    author_email="ryan@ryankelly.us",
    url="https://github.com/f0rk/enctempfile",
    install_requires=[
        "cryptography",
    ],
    tests_require=[
        "pytest",
    ],
    package_dir={"": "lib"},
    packages=["enctempfile"],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
    ],
)
