from setuptools import setup

setup(name='CSC',
      version='0.8',
      description='Charger Status Checker',
      url='https://www.python.org/community/sigs/current/distutils-sig',
      install_requires=['Flask>=0.7.2', 'MarkupSafe', 'flask-wtf', 'flask-babel', 'markdown', 'flup', 'requests', 'pytz', 'humanize'],
     )
