import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pylib",
    version="0.0.1",
    author="Tai Lucas",
    author_email="tglucas@gmail.com",
    description="Common Python utility modules",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tglucas/pylib",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "pylib"},
    packages=setuptools.find_packages(where="pylib"),
    python_requires=">=3.6",
)
