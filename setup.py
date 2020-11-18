import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sshcontroller",
    version="1.0",
    author="Olivier Roques",
    author_email="olivier@oroques.dev",
    description="A package to easily run SSH commands",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ojroques/python-sshcontroller",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)",
        "Operating System :: OS Independent",
        "Topic :: Internet",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development",
    ],
    python_requires='>=3.6',
)
