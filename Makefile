PHONY: plone4.3 plone5.0

ifneq ($(strip $(TRAVIS)),)
IS_TRAVIS = yes
endif

ifdef IS_TRAVIS

PIP = pip
PYTHON27 = python2.7

else

PIP = bin/pip
PYTHON27 = bin/python2.7

endif

plone4.3:
	$(PIP) install setuptools==0.6c11
	$(PYTHON27) bootstrap.py --version
	$(PYTHON27) bootstrap.py --setuptools-version=0.6c11 --buildout-version=1.7.1 -c buildout.cfg
	bin/buildout -vc buildout.cfg

plone5.0:
	$(PYTHON27) bootstrap.py --version
	$(PYTHON27) bootstrap.py --setuptools-version=18.3.1 --buildout-version=2.4.3 -c buildout.cfg
	bin/buildout -vc buildout.cfg
