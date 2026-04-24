.PHONY: release release-dry-run

PYTHON ?= python

release:
	$(PYTHON) scripts/release.py $(if $(VERSION),--version $(VERSION),) $(if $(REPOSITORY),--repository $(REPOSITORY),) $(if $(YES),--yes,) $(if $(SKIP_CHECKS),--skip-checks,) $(if $(SKIP_PUSH),--skip-push,)

release-dry-run:
	$(PYTHON) scripts/release.py --dry-run $(if $(VERSION),--version $(VERSION),) $(if $(REPOSITORY),--repository $(REPOSITORY),) $(if $(YES),--yes,) $(if $(SKIP_CHECKS),--skip-checks,)
