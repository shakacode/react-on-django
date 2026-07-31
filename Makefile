.PHONY: release release-dry-run

PYTHON ?= python
_truthy = $(filter 1 true yes y on TRUE YES Y ON,$(strip $(1)))

release:
	$(PYTHON) scripts/release.py $(if $(VERSION),--version $(VERSION),) $(if $(REPOSITORY),--repository $(REPOSITORY),) $(if $(call _truthy,$(YES)),--yes,) $(if $(call _truthy,$(SKIP_CHECKS)),--skip-checks,) $(if $(call _truthy,$(SKIP_PUSH)),--skip-push,)

release-dry-run:
	$(PYTHON) scripts/release.py --dry-run $(if $(VERSION),--version $(VERSION),) $(if $(REPOSITORY),--repository $(REPOSITORY),) $(if $(call _truthy,$(YES)),--yes,) $(if $(call _truthy,$(SKIP_CHECKS)),--skip-checks,)
