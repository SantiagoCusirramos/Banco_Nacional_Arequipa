# Atajos de ./bna. Sin make (Windows con Git Bash): ./bna <orden>.
ORDENES := up down reset test smoke logs ps

.PHONY: $(ORDENES) help
help:
	@./bna help

$(ORDENES):
	@./bna $@
