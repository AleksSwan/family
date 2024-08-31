# Targets
.PHONY: lint
lint:
	isort .
	black .
	ruff check --fix .
	mypy .

.PHONY: clean
clean:
	rm -rf __pycache__
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache

.PHONY: paths
paths:
	@echo $(PYTHONPATH)

.PHONY: test
test:
	python -m pytest tests/ -xvv

.PHONY: up
up:
	@$(MAKE) -s down
	@$(MAKE) -s lint
	@$(MAKE) -s test
	@sudo docker-compose up --remove-orphans --build

.PHONY: down
down:
	@sudo docker-compose down

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  up      - Start the services"
	@echo "  down    - Stop the services"
	@echo "  lint    - Run code linters and checkers"
	@echo "  test    - Run all tests"
	@echo "  clean   - Remove build artifacts and temporary files"
	@echo "  paths   - Display python paths"
	@echo "  help    - Show this help message"
