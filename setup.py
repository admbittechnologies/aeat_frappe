# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="erpnext_es_aeat",
    version="1.0.0",
    description="Modelos tributarios españoles (AEAT) para ERPNext",
    author="BIT Technologies GmbH",
    author_email="info@bit-technologies.eu",
    license="AGPL-3.0-or-later",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
)
