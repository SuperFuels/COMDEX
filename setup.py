from setuptools import setup, Extension
from Cython.Build import cythonize

ext_modules = cythonize([
    "backend/photon_algebra/structural_key_cy.pyx",
    "backend/photon_algebra/normalize_cy.pyx",   # <-- add this
])

setup(
    name="photon_algebra",
    ext_modules=ext_modules,
)