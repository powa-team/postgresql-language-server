from setuptools import setup, find_packages

setup(
    name='pgls',
    version='0.0.1',
    description='Language Server for PostgreSQL SQL development',
    packages=find_packages(),
    entry_points={
          'console_scripts': [
              'pgls = pgls.__main__:main'
          ]
    },
    install_requires=['psycopg2', 'pglast', 'sqlalchemy', 'pygls']
)
