from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='sellgo_core',
      version='0.2.1',
      description='Core library for sellgo',
      long_description=readme(),
      url='https://github.com/Sellgo/core',
      dependency_links=['https://github.com/Sellgo/core.git'],
      author='Marcus Ong',
      author_email='marcus@sellgo.com',
      license='unlicensed',
      packages=['sellgo_core', 'sellgo_core.utils', 'sellgo_core.webcrawl', 'sellgo_core.webcrawl.scrapy'],
      include_package_data=True,
      package_data={'': ['data/*.csv']},
      test_suite='nose.collector',
      tests_require=['nose'],
      install_requires=[
          'mws',
          'boto3',
          'pytest',
          'lxml',
          'requests',
          'Scrapy',
          'scrapy-proxycrawl-middleware'
      ],
      zip_safe=False)
