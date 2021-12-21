
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='pycta',
    version='0.1.1',
    author='Joe Rechenmacher',
    author_email='joe.rechenmacher@gmail.com',
    description='Testing installation of Package',
    url='https://github.com/joerex1418/cta',
    project_urls = {
        "Issues": "https://github.com/joerex1418/cta/issues",
        "Projects": "https://github.com/joerex1418/cta/projects"
    },
    license='GPU',
    packages=[''],
    install_requires=[
      'requests',
      'pandas',
      'beautifulsoup4'],
)
