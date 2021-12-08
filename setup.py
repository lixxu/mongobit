"""
MongoBit
--------

Simple pymongo orm
"""
import io
import os.path

from setuptools import setup

work_dir = os.path.dirname(os.path.abspath(__file__))
fp = os.path.join(work_dir, "mongobit/__init__.py")

version = ""
with io.open(fp, encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__ = "):
            version = line.split("=")[-1].strip().replace("'", "")
            break

setup(
    name="MongoBit",
    version=version.replace('"', ""),
    url="https://github.com/lixxu/mongobit",
    license="BSD",
    author="Lix Xu",
    author_email="xuzenglin@gmail.com",
    description="Simple pymongo orm",
    long_description=__doc__,
    packages=["mongobit"],
    zip_safe=False,
    platforms="any",
    install_requires=["pymongo<4.0", "six"],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
