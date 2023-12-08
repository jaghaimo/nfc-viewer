SOURCES = $(shell find data/ -iname '*.fleet' -o -iname '*.missile' -o -iname '*.ship' | sed 's/ /\\ /g')

.PHONY: $(SOURCES) all clean check format cache steam wiki

all: $(SOURCES)

clean:
	rm -f *.png
	rm -f *.log
	rm -f *.log.*

check:
	poetry run ruff check nfcli/

format:
	poetry run ruff check --fix nfcli/
	poetry run ruff format nfcli/

cache: steam wiki

steam:
	poetry run steam

wiki:
	poetry run wiki

$(SOURCES):
	poetry run nfcli -i "$@" -w
